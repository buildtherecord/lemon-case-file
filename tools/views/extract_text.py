#!/usr/bin/env python3
"""Fill each exhibit's `text` from its own file, so quotes in the record can be checked word for word.

  python3 extract_text.py record.json --files-dir DIR [--ocr] [--write OUT.json]

For every exhibit that has a local file and no `text`:
  PDF with a text layer   pdftotext (poppler)
  .html .htm .txt         the words in the file
  pictures                tesseract, only with --ocr and only if it is installed (a scanned PDF is read page by page the same way)
Prints what it found. With --write it saves a COPY of the record with the text filled in; your record file is never changed.
The text is a machine copy of the document and can contain reading mistakes. A quote that fails the check against it is worth a look at the document itself.
Nothing is uploaded. The extracted text is kept in the record file, which is private; the page builders never print it."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks, btr_scrub as scrub
from btr_common import BuildError, is_http


def _run(args, timeout=600):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _words(html_or_text, is_html):
    if not is_html:
        return html_or_text
    t = re.sub(r'(?is)<(script|style).*?</\1>|<!--.*?-->', ' ', html_or_text)
    import html as h
    return h.unescape(re.sub(r'<[^>]+>', ' ', t))


def text_of(path, ocr=False):
    """The text of one file, or None when there is none to read (and why, as the second value)."""
    kind, ext = scrub.kind_of(path)
    if kind == 'text':
        with open(path, encoding='utf-8', errors='replace') as fh:
            return _words(fh.read(), ext != '.txt'), None
    if kind == 'pdf':
        t = scrub.pdf_text(path) if shutil.which('pdftotext') else None
        if t:
            return t, None
        if not ocr:
            return None, 'no text layer (run with --ocr to read it as pictures, or type the words in)'
        if not (shutil.which('tesseract') and shutil.which('pdftoppm')):
            return None, 'reading pictures needs tesseract and pdftoppm, which are not both installed'
        with tempfile.TemporaryDirectory(prefix='.btr-ocr-') as tmp:
            _run(['pdftoppm', '-r', '200', '-png', path, os.path.join(tmp, 'p')])
            parts = [_run(['tesseract', os.path.join(tmp, f), 'stdout']).stdout for f in sorted(os.listdir(tmp)) if f.endswith('.png')]
        return ('\n'.join(parts) or None), (None if parts else 'no pages could be read')
    if kind == 'image':
        if not ocr:
            return None, 'a picture (run with --ocr, or type the words in)'
        if not shutil.which('tesseract'):
            return None, 'reading pictures needs tesseract, which is not installed (brew install tesseract)'
        out = _run(['tesseract', path, 'stdout']).stdout
        return (out or None), (None if out.strip() else 'no words found')
    return None, 'a type of file this tool does not read'


def fill(rec, files_dir, ocr=False):
    """-> (copy of rec with text filled in, [(exhibit id, message)]). Exhibits that already have text are left alone."""
    rec = json.loads(json.dumps(rec))
    report = []
    root = os.path.realpath(files_dir)
    for e in rec.get('exhibits', []):
        if e.get('text') or not e.get('file') or is_http(e['file']):
            continue
        p = os.path.realpath(os.path.join(root, e['file']))
        if not (p.startswith(root + os.sep) and os.path.isfile(p)):
            report.append((e['id'], f"the file {e['file']!r} is not in the files folder"))
            continue
        try:
            t, why = text_of(p, ocr)
        except (BuildError, subprocess.SubprocessError, OSError) as ex:
            t, why = None, f'could not be read ({ex})'
        if t and t.strip():
            e['text'] = re.sub(r'[ \t]+\n', '\n', t).strip()
            report.append((e['id'], f"{len(e['text'].split())} words found"))
        else:
            report.append((e['id'], why or 'nothing found'))
    return rec, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('record')
    ap.add_argument('--files-dir', required=True)
    ap.add_argument('--ocr', action='store_true', help='also read pictures and scanned PDFs with tesseract')
    ap.add_argument('--write', metavar='OUT.json', help='save a copy of the record with the text filled in')
    a = ap.parse_args(argv)
    rec, errs = checks.load_record(a.record)
    if errs or not isinstance(rec, dict):
        print('\n'.join(errs) or 'The record file should hold one group of fields.')
        return 1
    if not os.path.isdir(a.files_dir):
        print(f'The files folder {a.files_dir!r} does not exist.')
        return 1
    new, report = fill(rec, a.files_dir, a.ocr)
    for i, msg in report:
        print(f'{i}: {msg}')
    found = sum(1 for _i, m in report if m.endswith('words found'))
    print(f'{found} of {len(report)} exhibits without text now have some.')
    if a.write:
        if os.path.abspath(a.write) == os.path.abspath(a.record):
            print('Choose a different file name for --write; the original record is never overwritten.')
            return 1
        with open(a.write, 'w', encoding='utf-8') as fh:
            json.dump(new, fh, indent=1, ensure_ascii=False)
        print(f'saved a copy with the text in {a.write}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
