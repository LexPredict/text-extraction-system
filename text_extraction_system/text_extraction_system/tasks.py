import json
import logging
import os
import pickle
import shutil
import tempfile
from contextlib import contextmanager
from typing import List, Dict, Optional

import pycountry
import requests
from camelot.core import Table as CamelotTable
from celery import Celery, chord
from celery.signals import after_setup_logger, worker_process_init, before_task_publish, task_success, task_failure, \
    task_revoked
from webdav3.exceptions import RemoteResourceNotFound

from text_extraction_system.celery_log import JSONFormatter, set_log_extra
from text_extraction_system.config import get_settings
from text_extraction_system.constants import pages_ocred, task_ids, pages_for_processing, pages_tables, \
    queue_celery_beat
from text_extraction_system.data_extract.data_extract import extract_text_and_structure, process_pdf_page, \
    PDFPageProcessingResults
from text_extraction_system.data_extract.tables import get_table_dtos_from_camelot_output
from text_extraction_system.file_storage import get_webdav_client, WebDavClient
from text_extraction_system.pdf.convert_to_pdf import convert_to_pdf
from text_extraction_system.pdf.pdf import merge_pdf_pages, split_pdf_to_page_blocks
from text_extraction_system.request_metadata import RequestCallbackInfo, RequestMetadata, \
    save_request_metadata, \
    load_request_metadata
from text_extraction_system.result_delivery.celery_client import send_task
from text_extraction_system.task_health.task_health import store_pending_task_info_in_webdav, \
    remove_pending_task_info_from_webdav, re_schedule_unknown_pending_tasks, init_task_tracking
from text_extraction_system_api.dto import RequestStatus, STATUS_FAILURE, STATUS_PENDING, STATUS_DONE

settings = get_settings()

celery_app = Celery(
    'celery_app',
    backend=settings.celery_backend,
    broker=settings.celery_broker,
    task_serializer='pickle',
    result_serializer='pickle',
    accept_content=['application/json', 'application/x-python-serialize']
)

celery_app.conf.update(task_track_started=True)
celery_app.conf.update(task_serializer='pickle')
celery_app.conf.update(accept_content=['pickle', 'json'])
celery_app.conf.update(task_acks_late=True)
celery_app.conf.update(task_reject_on_worker_lost=True)
celery_app.conf.update(worker_prefetch_multiplier=1)

init_task_tracking()

log = logging.getLogger(__name__)


@worker_process_init.connect
def setup_recursion_limit(*args, **kwargs):
    # This is a workaround for pdfminer.six to not crash on too deep
    # data structures in some PDF files. It has recursion internally which looks correct
    # but does not work for some documents.
    # Of course this is totally unsafe and a bad practice
    # but it works.
    # Without this we would have to fork and modify algorithms in pdfminer.six which
    # would require much more development and testing work.
    from text_extraction_system.commons.sysutils import increase_recursion_limit
    increase_recursion_limit()
    import os
    log.info(f'Recursion limit increased for a Celery worker process {os.getpid()}')


@after_setup_logger.connect
def setup_loggers(*args, **kwargs):
    conf = get_settings()

    logger = logging.getLogger()
    logger.handlers.clear()

    if conf.log_to_stdout:
        if conf.log_to_stdout_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    if conf.log_to_file:
        formatter = JSONFormatter()
        from logging.handlers import RotatingFileHandler
        sh = RotatingFileHandler(filename=conf.log_to_file, encoding='utf-8', maxBytes=10 * 1024 * 1024, backupCount=5)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    # make pdfminer a bit more silent
    from pdfminer.pdfinterp import log as pdfinterp_log
    from pdfminer.pdfpage import log as pdfpage_log
    from pdfminer.pdfdocument import log as pdfdocument_log
    from pdfminer.converter import log as converter_log
    pdfinterp_log.setLevel(logging.WARNING)
    pdfpage_log.setLevel(logging.WARNING)
    pdfdocument_log.setLevel(logging.WARNING)
    converter_log.setLevel(logging.WARNING)


@before_task_publish.connect
def on_before_task_publish(sender,
                           body,
                           exchange,
                           routing_key,
                           headers,
                           properties,
                           declare,
                           retry_policy, *args, **kwargs):
    log.info(f'Registering task: #{headers["id"]} - {headers["task"]}')
    store_pending_task_info_in_webdav(body=body,
                                      exchange=exchange,
                                      routing_key=routing_key,
                                      headers=headers,
                                      properties=properties,
                                      declare=declare,
                                      retry_policy=retry_policy)


@task_success.connect
def on_task_success(sender, *args, **kwargs):
    log.info(f'Unregistering on task_success: #{sender.request.id} - {sender.request.task}')
    remove_pending_task_info_from_webdav(sender.request.id, sender.request.task)


@task_failure.connect
def on_task_failure(sender, *args, **kwargs):
    log.info(f'Unregistering on task_failure: #{sender.request.id} - {sender.request.task}')
    remove_pending_task_info_from_webdav(sender.request.id, sender.request.task)


@task_revoked.connect
def task_post_run(task_id: str, task: str, *args, **kwargs):
    log.info(f'Unregistering on task_revoked: #{task_id} - {task}')
    remove_pending_task_info_from_webdav(task_id, task)


def register_task_id(webdav_client: WebDavClient, request_id: str, task_id: str):
    webdav_client.mkdir(f'{request_id}/{task_ids}/{task_id}')


def get_request_task_ids(webdav_client: WebDavClient, request_id: str) -> List[str]:
    try:
        return [s.strip('/') for s in webdav_client.list(f'{request_id}/{task_ids}')]
    except RemoteResourceNotFound:
        metadata = load_request_metadata(request_id)
        if metadata is None:
            # the upload task was purged. Don't complain on missing request data
            return []
        raise


def deliver_error(request_id: str,
                  request_callback_info: RequestCallbackInfo,
                  problem: Optional[str] = None,
                  exc: Optional[Exception] = None):
    try:
        req = load_request_metadata(request_id)
        if not req:
            log.warning(f'{request_callback_info.original_file_name} | Not delivering error '
                        f'because the request files do not exist in storage: '
                        f'(#{request_id})\n'
                        f'This usually means the request is canceled.')
            return
        req.status = STATUS_FAILURE

        if problem or exc:
            req.append_error(problem, exc)

        save_request_metadata(req)
    except Exception as req_upd_err:
        log.error(f'{request_callback_info.original_file_name} | Unable to store failed status into '
                  f'metadata of request #{request_id}', exc_info=req_upd_err)
    req_status = RequestStatus(request_id=request_id,
                               original_file_name=request_callback_info.original_file_name,
                               status=STATUS_FAILURE,
                               additional_info=request_callback_info.call_back_additional_info)
    deliver_results(request_callback_info, req_status)


@contextmanager
def handle_errors(request_id: str, request_callback_info: RequestCallbackInfo):
    try:
        set_log_extra(request_callback_info.log_extra)
        yield
    except Exception as e:
        log.error(f'{request_callback_info.original_file_name} | Exception caught while processing the document',
                  exc_info=e)
        deliver_error(request_id, request_callback_info, exc=e)


@celery_app.task(acks_late=True, bind=True)
def process_document(task, request_id: str, request_callback_info: RequestCallbackInfo) -> bool:
    with handle_errors(request_id, request_callback_info):
        webdav_client: WebDavClient = get_webdav_client()
        req: RequestMetadata = load_request_metadata(request_id)
        if not req:
            log.warning(f'{request_callback_info.original_file_name} | Canceling document processing (#{request_id}):\n'
                        f'Request files do not exist. Probably the request was already canceled.\n')
            return False
        log.info(f'{request_callback_info.original_file_name} | Starting text/data extraction '
                 f'for request #{request_id}\n')
        with webdav_client.get_as_local_fn(f'{request_id}/{req.original_document}') as (fn, _remote_path):
            ext = os.path.splitext(fn)[1]
            if ext and ext.lower() == '.pdf':
                process_pdf(fn, req, webdav_client)
            else:
                log.info(f'{req.original_file_name} | Converting to PDF...')
                with convert_to_pdf(fn, timeout_sec=req.convert_to_pdf_timeout_sec) \
                        as local_converted_pdf_fn:
                    req.converted_to_pdf = os.path.splitext(req.original_document)[0] + '.converted.pdf'
                    webdav_client.upload_file(remote_path=f'{request_id}/{req.converted_to_pdf}',
                                              local_path=local_converted_pdf_fn)
                    save_request_metadata(req)
                    process_pdf(local_converted_pdf_fn, req, webdav_client)
        return True


def process_pdf(pdf_fn: str,
                req: RequestMetadata,
                webdav_client: WebDavClient):
    log.info(f'{req.original_file_name} | Pre-processing PDF document')
    log.info(f'{req.original_file_name} | Splitting to pages to parallelize processing...')
    with split_pdf_to_page_blocks(pdf_fn, pages_per_block=1) as pdf_page_fns:
        webdav_client.mkdir(f'{req.request_id}/{pages_for_processing}')
        webdav_client.mkdir(f'{req.request_id}/{pages_ocred}')
        webdav_client.mkdir(f'{req.request_id}/{pages_tables}')
        task_signatures = list()
        i = 0

        ocr_language = req.doc_language or 'eng'
        if len(ocr_language) == 2:
            try:
                ocr_language = pycountry.languages.get(alpha_2=ocr_language).alpha_3
            except AttributeError:
                ocr_language = 'eng'

        for pdf_page_fn in pdf_page_fns:
            i += 1
            pdf_page_base_fn = os.path.basename(pdf_page_fn)
            webdav_client.upload_file(f'{req.request_id}/{pages_for_processing}/{pdf_page_base_fn}',
                                      pdf_page_fn)
            task_signatures.append(process_pdf_page_task.s(req.request_id,
                                                           req.original_file_name,
                                                           pdf_page_base_fn,
                                                           i,
                                                           ocr_language,
                                                           req.request_callback_info.log_extra))

        log.info(f'{req.original_file_name} | Scheduling {len(task_signatures)} sub-tasks...')
        c = chord(task_signatures)(finish_pdf_processing
                                   .s(req.request_id, req.original_file_name, req.request_callback_info)
                                   .set(link_error=[ocr_error_callback.s(req.request_id,
                                                                         req.request_callback_info)]))
        register_task_id(webdav_client, req.request_id, c.id)
        for ar in c.parent.children:
            register_task_id(webdav_client, req.request_id, ar.id)


def page_num_to_fn(page_num: int) -> str:
    return f'{page_num:05}'


@celery_app.task(acks_late=True, bind=True)
def process_pdf_page_task(_task,
                          request_id: str,
                          original_file_name: str,
                          pdf_page_base_fn: str,
                          page_number: int,
                          ocr_language: str,
                          log_extra: Dict[str, str] = None):
    set_log_extra(log_extra)
    webdav_client = get_webdav_client()
    req = load_request_metadata(request_id)
    if not req:
        log.warning(
            f'{original_file_name} | Could not process pdf page {page_number}: {pdf_page_base_fn}.\n'
            f'Request files do not exist at webdav storage.\n'
            f'Probably the request was already canceled.\n'
            f'(#{request_id})')
        return None
    if req.status != STATUS_PENDING:
        log.info(
            f'{original_file_name} | Canceling pdf page processing sub-task for page {page_number}:'
            f' {pdf_page_base_fn} (request #{request_id})\n'
            f'because the request is already in status {req.status}.')
        return None
    log.info(f'{original_file_name} | Processing PDF page {page_number}...')
    try:
        with webdav_client.get_as_local_fn(f'{req.request_id}/{pages_for_processing}/{pdf_page_base_fn}') \
                as (local_pdf_page_fn, _remote_path):
            with process_pdf_page(local_pdf_page_fn,
                                  page_num=page_number,
                                  ocr_enabled=req.ocr_enable,
                                  ocr_language=ocr_language) as page_proc_res:  # type: PDFPageProcessingResults
                if page_proc_res.page_requires_ocr:
                    webdav_client.upload_file(
                        remote_path=f'{req.request_id}/{pages_ocred}/{page_num_to_fn(page_number)}.pdf',
                        local_path=page_proc_res.ocred_page_fn)
                if page_proc_res.camelot_tables:
                    webdav_client.pickle(page_proc_res.camelot_tables,
                                         f'{req.request_id}/{pages_tables}/{page_num_to_fn(page_number)}.pickle')
    except Exception as e:
        raise Exception(f'{original_file_name} |  Exception caught while processing '
                        f'PDF page {page_number}: {pdf_page_base_fn}') from e

    return page_number


@celery_app.task(bind=True)
def ocr_error_callback(task, some_id: str, request_id: str, req_callback_info: RequestCallbackInfo):
    set_log_extra(req_callback_info.log_extra)
    deliver_error(request_id, req_callback_info)


@celery_app.task(acks_late=True, bind=True)
def finish_pdf_processing(task,
                          _ocred_page_nums: List[int],
                          request_id: str,
                          original_file_name: str,
                          req_callback_info: RequestCallbackInfo):
    with handle_errors(request_id, req_callback_info):
        req: RequestMetadata = load_request_metadata(request_id)
        if not req:
            log.info(f'{original_file_name} | Not re-combining OCR-ed pdf blocks and not '
                     f'processing the data extraction for request {request_id}.\n'
                     f'Request files do not exist. Probably the request was already canceled.')
            return False
        log.info(f'{req.original_file_name} | Re-combining OCR-ed pdf blocks and processing the '
                 f'data extraction for request #{request_id}')
        webdav_client: WebDavClient = get_webdav_client()
        if req.status != STATUS_PENDING or not webdav_client.is_dir(f'{req.request_id}/{pages_for_processing}'):
            log.info(f'{req.original_file_name} | Request is already processed/failed/canceled (#{request_id})')
            return
        temp_dir = tempfile.mkdtemp()
        try:
            pages_dir = os.path.join(temp_dir, 'pages')
            os.mkdir(pages_dir)

            camelot_tables_total: List[CamelotTable] = list()
            for remote_base_fn in webdav_client.list(f'{request_id}/{pages_tables}'):
                camelot_tables_of_page: List[CamelotTable] \
                    = webdav_client.unpickle(f'{request_id}/{pages_tables}/{remote_base_fn}')
                camelot_tables_total += camelot_tables_of_page

            repl_page_num_to_fn: Dict[int, str] = dict()
            for remote_base_fn in webdav_client.list(f'{request_id}/{pages_ocred}'):
                remote_page_pdf_fn = f'{req.request_id}/{pages_ocred}/{remote_base_fn}'
                local_page_pdf_fn = os.path.join(pages_dir, remote_base_fn)
                webdav_client.download_file(remote_page_pdf_fn, local_page_pdf_fn)
                page_num = int(os.path.splitext(remote_base_fn)[0])
                repl_page_num_to_fn[page_num] = local_page_pdf_fn

            if repl_page_num_to_fn:
                original_pdf_in_storage = req.converted_to_pdf or req.original_document
                local_orig_pdf_fn = os.path.join(temp_dir, original_pdf_in_storage)

                webdav_client.download_file(f'{req.request_id}/{original_pdf_in_storage}', local_orig_pdf_fn)
                with merge_pdf_pages(local_orig_pdf_fn, repl_page_num_to_fn) as local_merged_pdf_fn:
                    req.ocred_pdf = os.path.splitext(original_pdf_in_storage)[0] + '.ocred.pdf'
                    webdav_client.upload_file(f'{req.request_id}/{req.ocred_pdf}', local_merged_pdf_fn)
                    extract_data_and_finish(req, webdav_client, local_merged_pdf_fn, camelot_tables_total)
            else:
                remote_fn = req.converted_to_pdf or req.original_document
                with webdav_client.get_as_local_fn(f'{req.request_id}/{remote_fn}') as (local_pdf_fn, _remote_path):
                    extract_data_and_finish(req, webdav_client, local_pdf_fn, camelot_tables_total)

        finally:
            shutil.rmtree(temp_dir)


def extract_data_and_finish(req: RequestMetadata,
                            webdav_client: WebDavClient,
                            local_pdf_fn: str,
                            camelot_tables: List[CamelotTable]):
    req.pdf_file = req.ocred_pdf or req.converted_to_pdf or req.original_document
    pdf_fn_in_storage_base = os.path.splitext(req.original_document)[0]

    text, plain_text_structure = extract_text_and_structure(local_pdf_fn)
    req.plain_text_file = pdf_fn_in_storage_base + '.plain.txt'
    webdav_client.upload_to(text.encode('utf-8'), f'{req.request_id}/{req.plain_text_file}')

    req.plain_text_structure_file = pdf_fn_in_storage_base + '.plain_struct.json'
    plain_text_structure = json.dumps(plain_text_structure.to_dict(), indent=2)
    webdav_client.upload_to(plain_text_structure.encode('utf-8'), f'{req.request_id}/{req.plain_text_structure_file}')

    tables, df_tables = get_table_dtos_from_camelot_output(camelot_tables)
    if tables and tables.tables or df_tables and df_tables.tables:
        req.tables_json_file = pdf_fn_in_storage_base + '.tables.json'
        webdav_client.upload_to(json.dumps(tables.to_dict(), indent=2).encode('utf-8'),
                                f'{req.request_id}/{req.tables_json_file}')

        req.tables_df_file = pdf_fn_in_storage_base + '.tables.pickle'
        webdav_client.upload_to(pickle.dumps(df_tables), f'{req.request_id}/{req.tables_df_file}')

    if settings.delete_temp_files_on_request_finish:
        if req.converted_to_pdf and req.converted_to_pdf != req.pdf_file:
            webdav_client.clean(f'{req.request_id}/{req.converted_to_pdf}')
        if req.ocred_pdf and req.ocred_pdf != req.pdf_file:
            webdav_client.clean(f'{req.request_id}/{req.ocred_pdf}')
        if req.pages_for_ocr:
            webdav_client.clean(f'{req.request_id}/{pages_for_processing}/')
            webdav_client.clean(f'{req.request_id}/{pages_ocred}/')
            webdav_client.clean(f'{req.request_id}/{pages_tables}/')

    req.status = STATUS_DONE

    if load_request_metadata(req.request_id):
        save_request_metadata(req)
        deliver_results(req.request_callback_info, req.to_request_status())
    else:
        log.info(f'{req.original_file_name} | Canceling results delivery '
                 f'because the request files are already removed (#{req.request_id})')


def deliver_results(req: RequestCallbackInfo, req_status: RequestStatus):
    if req.call_back_url:
        try:
            log.info(f'{req.original_file_name} | POSTing the extraction results to {req.call_back_url}...')
            requests.post(req.call_back_url, json=req_status.to_dict())
        except Exception as err:
            log.error(f'{req.original_file_name} | Unable to POST the extraction results to {req.call_back_url}',
                      exc_info=err)

    if req.call_back_celery_broker:
        try:
            log.info(f'{req.original_file_name} | Sending the extraction results as a celery task:\n'
                     f'broker: {req.call_back_celery_broker}\n'
                     f'queue: {req.call_back_celery_queue}\n'
                     f'task_name: {req.call_back_celery_task_name}\n')
            send_task(broker_url=req.call_back_celery_broker,
                      queue=req.call_back_celery_queue,
                      task_name=req.call_back_celery_task_name,
                      task_kwargs=req_status.to_dict(),
                      task_id=req.call_back_celery_task_id,
                      parent_task_id=req.call_back_celery_parent_task_id,
                      root_task_id=req.call_back_celery_root_task_id,
                      celery_version=req.call_back_celery_version)
        except Exception as err:
            log.error(f'{req.original_file_name} | Unable to send the extraction results as a celery task:\n'
                      f'broker: {req.call_back_celery_broker}\n'
                      f'queue: {req.call_back_celery_queue}\n'
                      f'task_name: {req.call_back_celery_task_name}\n', exc_info=err)

    log.info(f'{req.original_file_name} | Finished processing request (#{req.request_id}).')


@celery_app.task(acks_late=True, bind=True, queue=queue_celery_beat)
def check_task_health(task):
    re_schedule_unknown_pending_tasks(log=log)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    log.info('Scheduling periodic task health checking...')
    sender.add_periodic_task(schedule=30.0, sig=check_task_health.s(), name='Check task health')
