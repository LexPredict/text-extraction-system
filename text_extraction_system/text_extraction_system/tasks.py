import itertools
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
from celery import Celery, chord
from celery.signals import after_setup_logger

from text_extraction_system.celery_log import JSONFormatter, set_log_extra
from text_extraction_system.config import get_settings
from text_extraction_system.constants import pages_for_ocr, pages_ocred, pages_pre_processed, from_original_doc, \
    task_ids
from text_extraction_system.data_extract.data_extract import extract_text_and_structure, pre_extract_data
from text_extraction_system.data_extract.tables import get_table_dtos_from_camelot_output
from text_extraction_system.file_storage import get_webdav_client, WebDavClient
from text_extraction_system.internal_dto import PDFPagePreProcessResults
from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.pdf.convert_to_pdf import convert_to_pdf
from text_extraction_system.pdf.pdf import merge_pfd_pages, cleanup_pdf, extract_all_page_images
from text_extraction_system.request_metadata import RequestCallbackInfo, RequestMetadata, \
    save_request_metadata, \
    load_request_metadata
from text_extraction_system.result_delivery.celery_client import send_task
from text_extraction_system_api.dto import RequestStatus
from text_extraction_system_api.dto import STATUS_FAILURE, STATUS_PENDING, STATUS_DONE

settings = get_settings()

celery_app = Celery(
    'celery_app',
    backend=settings.celery_backend,
    broker=settings.celery_broker,
)

celery_app.conf.update(task_track_started=True)
celery_app.conf.update(task_serializer='pickle')
celery_app.conf.update(accept_content=['pickle', 'json'])
celery_app.conf.update(task_acks_late=True)
celery_app.conf.update(task_reject_on_worker_lost=True)
celery_app.conf.update(worker_prefetch_multiplier=1)

log = logging.getLogger(__name__)


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


def register_task_id(webdav_client: WebDavClient, request_id: str, task_id: str):
    webdav_client.mkdir(f'{request_id}/{task_ids}/{task_id}')


def get_request_task_ids(webdav_client: WebDavClient, request_id: str) -> List[str]:
    return [s.strip('/') for s in webdav_client.list(f'{request_id}/{task_ids}')]


def deliver_error(request_id: str,
                  request_callback_info: RequestCallbackInfo,
                  problem: Optional[str] = None,
                  exc: Optional[Exception] = None):
    try:
        req = load_request_metadata(request_id)
        if not req:
            log.warning(f'Not delivering error '
                        f'because the request files do not exist in storage: '
                        f'{request_callback_info.original_file_name} (#{request_id})\n'
                        f'This usually means the request is canceled.')
            return
        req.status = STATUS_FAILURE

        if problem or exc:
            req.append_error(problem, exc)

        save_request_metadata(req)
    except Exception as req_upd_err:
        log.error(f'Unable to store failed status into metadata of request #{request_id}', exc_info=req_upd_err)
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
        deliver_error(request_id, request_callback_info, exc=e)
        raise e


@celery_app.task(acks_late=True, bind=True)
def process_document(task, request_id: str, request_callback_info: RequestCallbackInfo) -> bool:
    with handle_errors(request_id, request_callback_info):
        webdav_client: WebDavClient = get_webdav_client()
        req: RequestMetadata = load_request_metadata(request_id)
        if not req:
            log.warning(f'Canceling document processing: {request_callback_info.original_file_name} (#{request_id}):\n'
                        f'Request files do not exist. Probably the request was already canceled.\n')
            return False
        log.info(f'Starting text/data extraction for request uid: {request_id}\n'
                 f'File name: {req.original_file_name}')
        with webdav_client.get_as_local_fn(f'{request_id}/{req.original_document}') as (fn, _remote_path):
            ext = os.path.splitext(fn)[1]
            if ext and ext.lower() == '.pdf':
                # cleanup pdf and convert it to the format understood by other pdf libs
                with cleanup_pdf(fn) as local_converted_pdf_fn:
                    req.converted_to_pdf = os.path.splitext(req.original_document)[0] + '.converted.pdf'
                    webdav_client.upload(f'{request_id}/{req.converted_to_pdf}', local_converted_pdf_fn)
                    save_request_metadata(req)
                    process_pdf(local_converted_pdf_fn, req, webdav_client)
            else:
                with convert_to_pdf(fn) as local_converted_pdf_fn:
                    req.converted_to_pdf = os.path.splitext(req.original_document)[0] + '.converted.pdf'
                    webdav_client.upload(f'{request_id}/{req.converted_to_pdf}', local_converted_pdf_fn)
                    save_request_metadata(req)
                    process_pdf(local_converted_pdf_fn, req, webdav_client)
        return True


def process_pdf(pdf_fn: str,
                req: RequestMetadata,
                webdav_client: WebDavClient):
    """
    Steps:

    Render page images - we need them anyway for table detection (Camelot).
    First loop over the PDF pages:
        - Find pages requiring OCR.
        - But maybe no pages require OCR and we could extract tables and text right in the first and single loop.
    We extract text per page anyway.

    Iterating over the PDF pages and building the layouts costs much. Trying to minimize the number of loops.
    Camelot's read_pdf() internally splits PDF into pages itself and renders page images.
    Integrating it into our loop and replacing the Ghostscript call with our page images made by pdf2img.

    Right in the first loop:
        1. If page layout requires OCR -> send page image to OCR.
        2. If page layout does not require OCR -> extract text from page, extract tables.
    Accumulate the per-page extraction results in some structure.
    Result of the first loop:
        1. Dict of page_num -> PageExtractionResults(page_text, page_tables)
            for pages not requiring OCR. Pickled to webdav.
        2. Dict of page_num -> page image fn in webdav
            for pages requiring OCR.
    Pages requiring OCR are sent to OCR tasks with chord.
    Each OCR task makes a one-page PDF from image, extracts data from it,
        gets Dict of single page num -> PageExtractionResults(page_text, page_tables), stores them to WebDav.
    When all OCR tasks are finished we merge all dicts into one and concatenate the results.
    """
    log.info(f'Pre-processing PDF document: {pdf_fn}')

    with extract_all_page_images(pdf_fn) as page_image_fns:
        page_num_to_image_fn = {i: image_fn for i, image_fn in enumerate(page_image_fns)}
        pre_process_results = pre_extract_data(pdf_fn=pdf_fn,
                                               page_images_fns=page_num_to_image_fn,
                                               page_num_starts_from=0,
                                               ocr_enabled=req.ocr_enable)

        if not pre_process_results.pages_to_ocr:
            log.info(f'PDF document {pdf_fn} does not need any OCR work. Proceeding to the data extraction...')
            extract_data_and_finish(pre_process_results.ready_results, req, webdav_client)
        else:
            log.info(f'PDF document {pdf_fn} needs OCR for {len(pre_process_results.pages_to_ocr)} pages. '
                     f'Scheduling OCR tasks...')
            webdav_client.mkdir(f'{req.request_id}/{pages_pre_processed}')
            webdav_client.mkdir(f'{req.request_id}/{pages_for_ocr}')
            webdav_client.mkdir(f'{req.request_id}/{pages_ocred}')

            webdav_client.upload_to(pickle.dumps(pre_process_results.ready_results),
                                    f'{req.request_id}/{pages_pre_processed}/{from_original_doc}')

            ocr_language = req.doc_language or 'eng'
            if len(ocr_language) == 2:
                try:
                    ocr_language = pycountry.languages.get(alpha_2=ocr_language).alpha_3
                except AttributeError:
                    ocr_language = 'eng'

            req.pages_for_ocr = dict()
            task_signatures = list()
            for page_num, image_fn in pre_process_results.pages_to_ocr.items():
                basename = os.path.basename(image_fn)
                webdav_client.upload(f'{req.request_id}/{pages_for_ocr}/{basename}',
                                     image_fn)
                req.pages_for_ocr[page_num] = basename
                dst_basename = os.path.splitext(basename)[0] + '.pdf'
                dst_preprocess_basename = os.path.splitext(basename)[0] + '.pickle'
                task_signatures.append(ocr_and_preprocess.s(
                    req.request_id,
                    pdf_fn,
                    page_num,
                    f'{req.request_id}/{pages_for_ocr}/{basename}',
                    f'{req.request_id}/{pages_ocred}/{dst_basename}',
                    f'{req.request_id}/{pages_pre_processed}/{dst_preprocess_basename}',
                    ocr_language,
                    req.request_callback_info.log_extra))

            save_request_metadata(req)
            log.info(f'Starting sub-tasks for OCR-ing pdf pages:\n{req.pages_for_ocr}')
            c = chord(task_signatures)(merge_ocred_pages_and_extract_data
                .s(req.request_id, req.request_callback_info)
                .set(
                link_error=[ocr_error_callback.s(req.request_id, req.request_callback_info)]))
            register_task_id(webdav_client, req.request_id, c.id)
            for ar in c.parent.children:
                register_task_id(webdav_client, req.request_id, ar.id)


@celery_app.task(bind=True)
def ocr_error_callback(task, some_id: str, request_id: str, req_callback_info: RequestCallbackInfo):
    set_log_extra(req_callback_info.log_extra)
    deliver_error(request_id, req_callback_info)


@celery_app.task(acks_late=True, bind=True)
def ocr_and_preprocess(task,
                       request_id: str,
                       pdf_fn: str,
                       page_num: int,
                       page_image_webdav_path: str,
                       page_pdf_dst_webdav_path: str,
                       pre_process_results_dst_webdav_path: str,
                       ocr_language: str = 'eng',
                       log_extra: Dict[str, str] = None
                       ) -> Optional[str]:
    set_log_extra(log_extra)
    webdav_client = get_webdav_client()
    req = load_request_metadata(request_id)
    if not req:
        log.warning(
            f'Not OCR-ing page {page_num} of {pdf_fn}.\n'
            f'Request files do not exist.\n'
            f'Probably the request was already canceled.\n'
            f'{pdf_fn} (#{request_id})')
        return None
    if req.status != STATUS_PENDING:
        log.info(f'Canceling OCR sub-task for file: {pdf_fn}, page {page_num}. (request #{request_id})\n'
                 f'because the request is already in status {req.status}.')
        return None
    log.info(f'OCR-ing page {page_num} of {pdf_fn}: {page_image_webdav_path}...')
    try:
        with webdav_client.get_as_local_fn(page_image_webdav_path) \
                as (local_image_src, _remote_path):
            with ocr_page_to_pdf(local_image_src, language=ocr_language) as local_pdf_fn:
                webdav_client.upload(page_pdf_dst_webdav_path, local_pdf_fn)
                page_images_fns = {page_num: local_image_src}
                pre_process_results = pre_extract_data(pdf_fn=local_pdf_fn,
                                                       page_images_fns=page_images_fns,
                                                       page_num_starts_from=page_num,
                                                       ocr_enabled=False)
                webdav_client.upload_to(pickle.dumps(pre_process_results.ready_results[page_num]),
                                        pre_process_results_dst_webdav_path)
    except Exception as e:
        raise Exception(f'Exception caught while OCR-ing and pre-processing image: {page_image_webdav_path}') from e

    return page_pdf_dst_webdav_path


@celery_app.task(acks_late=True, bind=True)
def merge_ocred_pages_and_extract_data(task,
                                       _ocred_page_paths: List[str],
                                       request_id: str,
                                       req_callback_info: RequestCallbackInfo):
    with handle_errors(request_id, req_callback_info):
        req: RequestMetadata = load_request_metadata(request_id)
        if not req:
            log.info(f'Not re-combining OCR-ed pdf blocks and not processing the data extraction '
                     f'for request {request_id}: {req.original_file_name}'
                     f'Request files do not exist. Probably the request was already canceled.\n'
                     f'{req_callback_info.original_file_name} (#{request_id})')
            return False
        log.info(f'Re-combining OCR-ed pdf blocks and processing the data extraction for request {request_id}: '
                 f'{req.original_file_name}')
        webdav_client: WebDavClient = get_webdav_client()
        if req.status != STATUS_PENDING or not webdav_client.is_dir(f'{req.request_id}/{pages_for_ocr}'):
            log.info(f'Request is already processed/failed/canceled for file: {req.original_file_name} (#{request_id})')
            return
        temp_dir = tempfile.mkdtemp()
        try:
            pages_dir = os.path.join(temp_dir, 'pages')
            os.mkdir(pages_dir)

            merged_pre_process_results: Dict[int, PDFPagePreProcessResults] = webdav_client.unpickle(
                f'{req.request_id}/{pages_pre_processed}/{from_original_doc}')

            repl_page_num_to_fn: Dict[int, str] = dict()
            for page_num, image_fn in req.pages_for_ocr.items():
                basename = os.path.splitext(image_fn)[0]
                remote_page_pdf_fn = f'{req.request_id}/{pages_ocred}/{basename}.pdf'
                local_page_pdf_fn = os.path.join(pages_dir, basename)
                webdav_client.download(remote_page_pdf_fn, local_page_pdf_fn)
                repl_page_num_to_fn[page_num] = local_page_pdf_fn

                page_pre_process_results: PDFPagePreProcessResults = \
                    webdav_client.unpickle(f'{req.request_id}/{pages_pre_processed}/{basename}.pickle')
                merged_pre_process_results[page_num] = page_pre_process_results

            original_pdf_in_storage = req.converted_to_pdf or req.original_document

            local_orig_pdf_fn = os.path.join(temp_dir, original_pdf_in_storage)
            req.ocred_pdf = os.path.splitext(original_pdf_in_storage)[0] + '.ocred.pdf'

            webdav_client.download(f'{req.request_id}/{original_pdf_in_storage}', local_orig_pdf_fn)
            with merge_pfd_pages(local_orig_pdf_fn, repl_page_num_to_fn) as local_merged_pdf_fn:
                webdav_client.upload(f'{req.request_id}/{req.ocred_pdf}', local_merged_pdf_fn)
                save_request_metadata(req)
                extract_data_and_finish(merged_pre_process_results, req, webdav_client)

        finally:
            shutil.rmtree(temp_dir)


def extract_data_and_finish(pre_processed_pages: Dict[int, PDFPagePreProcessResults],
                            req: RequestMetadata,
                            webdav_client: WebDavClient):
    req.pdf_file = req.ocred_pdf or req.converted_to_pdf or req.original_document
    pdf_fn_in_storage_base = os.path.splitext(req.original_document)[0]

    # tika_xhtml: str = tika_extract_xhtml(pdf_fn)
    # req.tika_xhtml_file = pdf_fn_in_storage_base + '.tika.xhtml'
    # webdav_client.upload_to(tika_xhtml, f'{req.request_id}/{req.tika_xhtml_file}')

    text, plain_text_structure = extract_text_and_structure(pre_processed_pages)
    req.plain_text_file = pdf_fn_in_storage_base + '.plain.txt'
    webdav_client.upload_to(text.encode('utf-8'), f'{req.request_id}/{req.plain_text_file}')

    req.plain_text_structure_file = pdf_fn_in_storage_base + '.plain_struct.json'
    plain_text_structure = json.dumps(plain_text_structure.to_dict(), indent=2)
    webdav_client.upload_to(plain_text_structure.encode('utf-8'), f'{req.request_id}/{req.plain_text_structure_file}')

    camelot_tables = itertools.chain(*[p.camelot_tables for p in pre_processed_pages.values()])
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
            webdav_client.clean(f'{req.request_id}/{pages_for_ocr}')
            webdav_client.clean(f'{req.request_id}/{pages_ocred}')
            webdav_client.clean(f'{req.request_id}/{pages_pre_processed}')

    req.status = STATUS_DONE

    if load_request_metadata(req.request_id):
        save_request_metadata(req)
        deliver_results(req.request_callback_info, req.to_request_status())
    else:
        log.info(f'Canceling results delivery '
                 f'because the request files are already removed: {req.original_file_name} (#{req.request_id})')


def deliver_results(req: RequestCallbackInfo, req_status: RequestStatus):
    if req.call_back_url:
        try:
            log.info(f'POSTing the extraction results of {req.original_file_name} to {req.call_back_url}...')
            requests.post(req.call_back_url, json=req_status.to_dict())
        except Exception as err:
            log.error(f'Unable to POST the extraction results of {req.original_file_name} to {req.call_back_url}',
                      exc_info=err)

    if req.call_back_celery_broker:
        try:
            log.info(f'Sending the extraction results of {req.original_file_name} as a celery task:\n'
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
            log.error(f'Unable to send the extraction results of {req.original_file_name} as a celery task:\n'
                      f'broker: {req.call_back_celery_broker}\n'
                      f'queue: {req.call_back_celery_queue}\n'
                      f'task_name: {req.call_back_celery_task_name}\n', exc_info=err)

    log.info(f'Finished processing request {req.request_id} ({req.original_file_name}).')
