#!/usr/bin/env python3
"""Check this computer for what the record builders need, and say what to install.

  python3 doctor.py

Reads nothing from your record and sends nothing anywhere. Exit code 0 means both layers can be built; 1 means something required is missing."""
import os, platform, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks, btr_scrub as scrub

MAC = platform.system() == 'Darwin'
HINT = {
    'poppler': 'brew install poppler' if MAC else 'sudo apt install poppler-utils',
    'qpdf': 'brew install qpdf' if MAC else 'sudo apt install qpdf',
    'exiftool': 'brew install exiftool' if MAC else 'sudo apt install libimage-exiftool-perl',
    'ffmpeg': 'brew install ffmpeg' if MAC else 'sudo apt install ffmpeg',
    'pillow': 'python3 -m pip install pillow',
}


def line(ok, name, why, fix=''):
    print(f'  {"ok     " if ok else "MISSING"}  {name:<22} {why}' + (f'   -> {fix}' if (fix and not ok) else ''))
    return ok


def main():
    st = scrub.tools_status()
    print('INWARD pages (build_views.py): the full linked record, needs only Python and the schema file')
    need_inward = [line(sys.version_info >= (3, 9), f'python3 {platform.python_version()}', 'runs everything (3.9 or newer)', 'install Python 3.9 or newer from python.org'),
                   line(os.path.isfile(os.path.abspath(checks.SCHEMA_PATH)), 'record.schema.json', 'the record contract both builders check against',
                        'run from a full copy of the repository; schema/record.schema.json sits two folders above tools/views')]
    print()
    print('OUTWARD page (build_home.py): what you could hand to the other side')
    need_out = [line(st['Pillow'], 'Pillow', 'rewrites photos without their metadata', HINT['pillow']),
                line(st['pdfinfo'] and st['pdftoppm'], 'poppler (pdfinfo, pdftoppm)', 'reads PDFs and makes the page images', HINT['poppler'])]
    print('  recommended:')
    line(st['pdftotext'], 'pdftotext (poppler)', 'scans PDF text for counsel markers and personal details', HINT['poppler'])
    line(st['qpdf'], 'qpdf', 'removes PDF metadata and keeps the text; without it a PDF is rebuilt with pypdf or as pictures', HINT['qpdf'])
    line(st['pypdf'], 'pypdf', 'second choice for PDF metadata when qpdf is missing', 'python3 -m pip install pypdf')
    print('  only if you share recordings:')
    line(st['ffmpeg'] and st['ffprobe'], 'ffmpeg (ffmpeg, ffprobe)', 'removes location and other tags from recordings; sharing a recording fails without it', HINT['ffmpeg'])
    print('  optional:')
    line(shutil.which('tesseract') is not None, 'tesseract', 'extract_text.py --ocr reads pictures and scans with it', 'brew install tesseract' if MAC else 'sudo apt install tesseract-ocr')
    line(st['exiftool'], 'exiftool', 'a second, independent read-back of every outgoing file', HINT['exiftool'])
    try:
        import jsonschema  # noqa: F401
        has_js = True
    except ImportError:
        has_js = False
    line(has_js, 'jsonschema', 'only the tests use it, to cross-check the schema', 'python3 -m pip install jsonschema')
    print()
    inward, outward = all(need_inward), all(need_out)
    print(f'Inward pages: {"ready" if inward else "NOT ready"}.   Outward page: {"ready" if outward else "NOT ready"}.')
    if inward and outward and not (st['qpdf'] and st['pdftotext']):
        print('Outward page works; install qpdf and poppler\'s pdftotext for the best result with PDFs.')
    hosts = checks.private_hosts()
    listed = len(hosts) - len(checks.DEFAULT_PRIVATE_HOSTS)
    print(f'Private hosts the outward page may never link to: {len(hosts)} ({", ".join(checks.DEFAULT_PRIVATE_HOSTS)}' + (f' and {listed} from private-hosts.txt)' if listed > 0 else '; add your own, one per line, in tools/views/private-hosts.txt)'))
    print('Run the tests:  python3 -m unittest discover -s tools/views/tests -t tools/views   (or python3 -m unittest from inside tools/views)')
    return 0 if inward and outward else 1


if __name__ == '__main__':
    sys.exit(main())
