import codecs
import logging
import os

from text_extraction_system.config import get_settings, Settings
from text_extraction_system.processes import read_output

log = logging.getLogger(__name__)


def tika_extract_xhtml(src_fn: str) -> str:
    conf: Settings = get_settings()

    encoding_name = 'utf-8'
    os.environ['LEXNLP_TIKA_PARSER_MODE'] = 'pdf_only'
    # other possible values are 'coords_embedded' and ''
    os.environ['LEXNLP_TIKA_XML_DETAIL'] = 'coords_flat'

    cmd = ['java',
           '-cp',
           f'{conf.tika_jar_path}/*',
           '-Dsun.java2d.cmm=sun.java2d.cmm.kcms.KcmsServiceProvider',
           'org.apache.tika.cli.TikaCLI',
           f'--config={conf.tika_config}',
           '-x',
           f'-e{encoding_name}',
           src_fn]

    def err(line):
        log.error(f'TIKA parsing {src_fn}:\n{line}')

    return read_output(cmd, stderr_callback=err,
                       encoding=encoding_name,
                       timeout_sec=60 * 20) or ''
