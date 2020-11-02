import os
import shutil
from typing import List, Optional

import pikepdf


def build_block_fn(src_fn: str, page_start: int, page_end: int) -> str:
    fn: str = os.path.basename(src_fn)
    if page_start == page_end:
        fn = f'{os.path.splitext(fn)[0]}_{(page_start + 1):04}.pdf'
    else:
        fn = f'{os.path.splitext(fn)[0]}_{(page_start + 1):04}_{(page_end + 1):04}.pdf'
    return fn


def split_pdf_to_page_blocks(src_pdf_fn: str,
                             dst_dir: str,
                             pages_per_block: int = 1,
                             page_block_base_name: str = None,) -> List[str]:
    if not page_block_base_name:
        page_block_base_name = os.path.basename(src_pdf_fn)
    res: List[str] = list()
    with pikepdf.open(src_pdf_fn) as pdf:
        if len(pdf.pages) < 1:
            return res

        if len(pdf.pages) < pages_per_block:
            dst_fn = os.path.join(dst_dir, page_block_base_name)
            shutil.copy(src_pdf_fn, dst_fn)
            res.append(dst_fn)
            return res

        page_start: int = 0
        out_pdf: Optional[pikepdf.Pdf] = None
        try:
            for n, page in enumerate(pdf.pages):
                if n % pages_per_block == 0:
                    if out_pdf is not None:
                        out_fn = build_block_fn(str(page_block_base_name), page_start, n - 1)
                        out_pdf.save(os.path.join(dst_dir, out_fn))
                        out_pdf.close()
                        res.append(os.path.join(dst_dir, out_fn))

                    page_start = n
                    out_pdf = pikepdf.new()

                out_pdf.pages.append(page)

            if out_pdf is not None and len(out_pdf.pages) > 0:
                out_fn = build_block_fn(str(page_block_base_name), page_start, n)
                out_pdf.save(os.path.join(dst_dir, out_fn))
                res.append(os.path.join(dst_dir, out_fn))
        finally:
            out_pdf.close()

    return res


def join_pdf_blocks(block_fns: List[str], dst_fn: str):
    if len(block_fns) == 1:
        shutil.copy(block_fns[0], dst_fn)
        return

    with pikepdf.new() as dst_pdf:  # type: pikepdf.Pdf
        for block_fn in block_fns:
            with pikepdf.open(block_fn) as block_pdf:
                dst_pdf.pages.extend(block_pdf.pages)
        dst_pdf.save(dst_fn)
