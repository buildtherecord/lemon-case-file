"""Metadata scrubbing and PDF page rendering for files that go on the outward page.

Every outgoing file is rewritten without its metadata, then read back; a leftover Author, Subject, Title, Creator or GPS tag is an error.
  images   re-saved from their pixels (no EXIF, no GPS, no comments, no XMP); orientation is applied first so they look the same
  PDFs     rewritten from their pages (qpdf if installed, else pypdf if installed, else an image-only PDF made with Pillow and pdftoppm)
  video    ffmpeg copies the streams and drops all metadata and data tracks (GPS lives there)
  html/txt copied as text; checked by the builder for markers and personal details
Nothing here uploads anything. Every tool is run with a fixed argument list, never through a shell."""
import io, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btr_common import BuildError

IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
PDF_EXT = ('.pdf',)
MEDIA_EXT = ('.mp4', '.mov', '.m4v', '.webm', '.mp3', '.m4a', '.wav', '.aac')
TEXT_EXT = ('.html', '.htm', '.txt')
ALLOWED_EXT = IMAGE_EXT + PDF_EXT + MEDIA_EXT + TEXT_EXT
INSTALL = {'pdfinfo': 'brew install poppler', 'pdftoppm': 'brew install poppler', 'pdftotext': 'brew install poppler', 'qpdf': 'brew install qpdf',
           'exiftool': 'brew install exiftool', 'ffmpeg': 'brew install ffmpeg', 'ffprobe': 'brew install ffmpeg'}
BAD_PDF_KEYS = ('Title', 'Subject', 'Author', 'Creator', 'Keywords')
BAD_MEDIA_TAGS = ('title', 'author', 'artist', 'album_artist', 'composer', 'comment', 'description', 'copyright', 'location', 'location-eng', 'gps', 'make', 'model', 'publisher')


class ScrubError(BuildError):
    pass


def have(cmd):
    return shutil.which(cmd) is not None


def need(cmd, why):
    if not have(cmd):
        raise ScrubError(f'{why} needs {cmd}, which is not installed. Install it ({INSTALL.get(cmd, cmd)}) and run again. python3 tools/views/doctor.py lists what is missing.')


def first_line(text, n=100):
    lines = [l.strip() for l in (text or '').splitlines() if l.strip()]
    return lines[0][:n] if lines else 'no details'


def run(args, timeout=300):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ScrubError(f'{os.path.basename(args[0])} took longer than {timeout} seconds on one file. Try a smaller file.')


def kind_of(path):
    ext = os.path.splitext(path.split('?')[0])[1].lower()
    return ('image' if ext in IMAGE_EXT else 'pdf' if ext in PDF_EXT else 'media' if ext in MEDIA_EXT else 'text' if ext in TEXT_EXT else None), ext


def tools_status():
    out = {}
    for c in ('pdfinfo', 'pdftoppm', 'pdftotext', 'qpdf', 'exiftool', 'ffmpeg', 'ffprobe'):
        out[c] = have(c)
    try:
        import PIL
        out['Pillow'] = True
    except ImportError:
        out['Pillow'] = False
    try:
        import pypdf
        out['pypdf'] = True
    except ImportError:
        out['pypdf'] = False
    return out


# ---------- images ----------

def _scrub_image(src, dst, ext):
    try:
        from PIL import Image, ImageOps, ImageSequence
    except ImportError:
        raise ScrubError('Removing photo metadata needs Pillow, which is not installed. Install it (pip install pillow) and run again.')
    try:
        with Image.open(src) as im:
            fmt = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.gif': 'GIF', '.webp': 'WEBP'}[ext]
            icc = im.info.get('icc_profile')
            frames = []
            for fr in (ImageSequence.Iterator(im) if getattr(im, 'is_animated', False) and fmt in ('GIF', 'WEBP') else [im]):
                fr = ImageOps.exif_transpose(fr) or fr
                frames.append(_clean_pixels(fr, fmt, icc))
            first = frames[0]
            if fmt == 'JPEG':
                first.save(dst, 'JPEG', quality=92, optimize=True)
            elif len(frames) > 1:
                first.save(dst, fmt, save_all=True, append_images=frames[1:], loop=0)
            else:
                first.save(dst, fmt)
    except ScrubError:
        raise
    except Exception as e:
        raise ScrubError(f'The image {os.path.basename(src)!r} could not be rewritten without its metadata ({type(e).__name__}: {e}). Open it, save a copy, and try again.')


def _clean_pixels(fr, fmt, icc):
    from PIL import Image
    mode = fr.mode
    if icc and mode in ('RGB', 'RGBA', 'L', 'LA'):
        try:
            from PIL import ImageCms
            fr = ImageCms.profileToProfile(fr.convert('RGBA' if 'A' in mode else 'RGB'), ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile('sRGB'),
                                           outputMode='RGBA' if 'A' in mode else 'RGB') or fr
            mode = fr.mode
        except Exception:
            pass
    if fmt == 'JPEG' and mode not in ('RGB', 'L'):
        if mode in ('RGBA', 'LA', 'P'):
            rgba = fr.convert('RGBA')
            bg = Image.new('RGB', rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            fr, mode = bg, 'RGB'
        else:
            fr, mode = fr.convert('RGB'), 'RGB'
    clean = Image.frombytes(fr.mode, fr.size, fr.tobytes())
    if fr.mode == 'P':
        clean.putpalette(fr.getpalette())
        if 'transparency' in fr.info:
            clean.info['transparency'] = fr.info['transparency']
    return clean


def _image_problems(path):
    try:
        from PIL import Image
    except ImportError:
        return ['Pillow is not installed, so this image could not be checked for metadata.']
    out = []
    try:
        with Image.open(path) as im:
            ex = im.getexif()
            if ex:
                try:
                    if ex.get_ifd(0x8825):
                        out.append('a GPS location tag')
                except Exception:
                    pass
                names = {315: 'Author', 270: 'Title or description', 33432: 'Copyright', 0x9C9B: 'Title', 0x9C9C: 'Comment', 0x9C9D: 'Author', 0x9C9F: 'Subject', 37510: 'Comment'}
                for tag, name in names.items():
                    if ex.get(tag):
                        out.append(f'an {name} tag' if name[0] in 'AEIOU' else f'a {name} tag')
            xmp = im.info.get('xmp') or im.info.get('XML:com.adobe.xmp')
            if xmp:
                x = xmp.decode('utf-8', 'ignore') if isinstance(xmp, bytes) else str(xmp)
                if re.search(r'dc:creator|dc:title|dc:description|dc:subject|exif:GPS|photoshop:Credit', x):
                    out.append('an XMP block with author, title or location')
            for k, v in list(im.info.items()):
                if str(k).lower() in ('author', 'title', 'description', 'subject', 'comment', 'copyright', 'artist') and v:
                    out.append(f'a {k} text tag')
    except Exception as e:
        out.append(f'could not be read back ({type(e).__name__})')
    return out


# ---------- PDFs ----------

def pdf_info(path):
    need('pdfinfo', 'Reading a PDF')
    r = run(['pdfinfo', path], 60)
    if r.returncode != 0:
        raise ScrubError(f'{os.path.basename(path)!r} could not be read as a PDF ({first_line(r.stderr)}). Open it, print it to a new PDF, and try again.')
    info = {}
    for line in r.stdout.splitlines():
        k, _, v = line.partition(':')
        info[k.strip()] = v.strip()
    return info


def _pdf_problems(path):
    info = pdf_info(path)
    out = [f'a PDF {k} field ({info[k][:40]!r})' for k in BAD_PDF_KEYS if info.get(k)]
    if info.get('JavaScript', '').lower() == 'yes':
        out.append('embedded JavaScript')
    r = run(['pdfinfo', '-meta', path], 60)
    if r.returncode == 0 and re.search(r'dc:creator|dc:title|dc:description|dc:subject|pdf:Author|pdf:Keywords|xmp:CreatorTool', r.stdout):
        out.append('an XMP metadata block with author, title or subject')
    return out


def _scrub_pdf(src, dst):
    """Try, in order: qpdf (keeps the text), pypdf (keeps the text), then an image-only copy. Each result is read back; one that still carries a tag is thrown away."""
    if have('qpdf'):
        r = run(['qpdf', '--empty', '--pages', src, '--', dst])
        if r.returncode in (0, 3) and os.path.exists(dst):
            if not _pdf_problems(dst):
                return 'qpdf'
            os.remove(dst)
    try:
        import logging
        import pypdf
        logging.getLogger('pypdf').setLevel(logging.CRITICAL)
        w = pypdf.PdfWriter()
        for pg in pypdf.PdfReader(src).pages:
            for k in ('/Metadata', '/PieceInfo', '/Annots'):
                if k in pg:
                    del pg[k]
            w.add_page(pg)
        with open(dst, 'wb') as fh:
            w.write(fh)
        if not _pdf_problems(dst):
            return 'pypdf'
        os.remove(dst)
    except ImportError:
        pass
    except Exception:
        if os.path.exists(dst):
            os.remove(dst)
    return _image_only_pdf(src, dst)


def _image_only_pdf(src, dst):
    try:
        from PIL import Image
    except ImportError:
        raise ScrubError('Removing PDF metadata needs qpdf, pypdf or Pillow, and none is installed. Install qpdf (brew install qpdf) and run again.')
    need('pdftoppm', 'Rewriting a PDF without its metadata')
    with tempfile.TemporaryDirectory(prefix='.btr-pdf-') as tmp:
        r = run(['pdftoppm', '-r', '150', '-png', src, os.path.join(tmp, 'p')], 600)
        pages = sorted(f for f in os.listdir(tmp) if f.endswith('.png'))
        if r.returncode != 0 or not pages:
            raise ScrubError(f'{os.path.basename(src)!r} could not be read as a PDF ({first_line(r.stderr)}). Open it, print it to a new PDF, and try again.')
        ims = [Image.open(os.path.join(tmp, p)).convert('RGB') for p in pages]
        ims[0].save(dst, 'PDF', save_all=True, append_images=ims[1:], resolution=150.0, title='')   # Pillow would otherwise put the file name in Title
        for i in ims:
            i.close()
    return 'image-only copy (text in the PDF can no longer be selected; install qpdf to keep it)'


def render_pdf_pages(src, dst_dir, base, max_pages=8, dpi=100):
    """Page images for the viewer: [file names], page count. Names are <base>-<n>.jpg."""
    info = pdf_info(src)
    n = int(re.sub(r'\D', '', info.get('Pages', '0')) or 0)
    need('pdftoppm', 'Showing a PDF page by page')
    os.makedirs(dst_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.btr-pages-') as tmp:
        r = run(['pdftoppm', '-f', '1', '-l', str(min(n or 1, max_pages)), '-r', str(dpi), '-jpeg', '-jpegopt', 'quality=72', src, os.path.join(tmp, 'p')], 600)
        got = sorted(f for f in os.listdir(tmp) if f.endswith('.jpg'))
        if r.returncode != 0 or not got:
            raise ScrubError(f'{os.path.basename(src)!r} could not be turned into page images ({first_line(r.stderr)}).')
        names = []
        for i, f in enumerate(got, 1):
            name = f'{base}-{i}.jpg'
            shutil.copyfile(os.path.join(tmp, f), os.path.join(dst_dir, name))
            names.append(name)
    return names, n


# ---------- video and audio ----------

def _scrub_media(src, dst):
    need('ffmpeg', 'Removing location and other metadata from a recording')
    args = ['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', src, '-map', '0:v?', '-map', '0:a?', '-map_metadata', '-1', '-map_chapters', '-1',
            '-c', 'copy', '-fflags', '+bitexact', '-flags:v', '+bitexact', '-flags:a', '+bitexact', dst]
    r = run(args, 1800)
    if r.returncode != 0 or not os.path.exists(dst):
        raise ScrubError(f'The recording {os.path.basename(src)!r} could not be rewritten without its metadata ({first_line(r.stderr, 160)}).')


def _media_problems(path):
    if not have('ffprobe'):
        return ['ffprobe is not installed, so this recording could not be checked for metadata.']
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format_tags:stream_tags', '-of', 'json', path], 120)
    if r.returncode != 0:
        return ['could not be read back by ffprobe']
    try:
        data = json.loads(r.stdout or '{}')
    except json.JSONDecodeError:
        return ['could not be read back by ffprobe']
    tags = dict(data.get('format', {}).get('tags', {}))
    for st in data.get('streams', []):
        tags.update({f'{k}': v for k, v in st.get('tags', {}).items() if k.lower() not in ('handler_name', 'vendor_id', 'language', 'encoder', 'creation_time')})
    out = []
    for k, v in tags.items():
        kl = k.lower()
        if v and (kl in BAD_MEDIA_TAGS or 'location' in kl or 'gps' in kl or kl.startswith('com.apple.quicktime')):
            out.append(f'a {k} tag')
    return out


# ---------- html ----------

_HTML_META = re.compile(r'(?is)<meta\s+[^>]*name\s*=\s*["\']?(?:author|creator|subject|keywords|description|generator|copyright|publisher|designer|owner|geo\.[a-z.]+|icbm)["\']?[^>]*>')
_HTML_COMMENT = re.compile(r'(?s)<!--(?!\[if|<!\[endif).*?-->')


def _scrub_html(src, dst):
    with open(src, encoding='utf-8', errors='replace') as fh:
        t = fh.read()
    t = _HTML_COMMENT.sub('', _HTML_META.sub('', t))
    with open(dst, 'w', encoding='utf-8') as fh:
        fh.write(t)


def _html_problems(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        t = fh.read()
    out = []
    if _HTML_META.search(t):
        out.append('a meta tag with author, subject or keywords')
    if re.search(r'(?i)saved from url', t):
        out.append('a "saved from url" comment')
    return out


# ---------- the one entry points ----------

def scrub_copy(src, dst):
    """Copy src to dst with metadata removed. Returns a short note. Raises ScrubError (plain language) on any problem."""
    kind, ext = kind_of(src)
    if kind is None:
        raise ScrubError(f'{os.path.basename(src)!r} is a {ext or "no-extension"} file, which this tool cannot scrub of metadata. '
                         f'Allowed outgoing types: {", ".join(ALLOWED_EXT)}. Convert it, or leave it unshared.')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    note = {'image': 'rewritten from pixels', 'media': 'streams copied, metadata dropped', 'text': 'copied as text'}.get(kind, '')
    if kind == 'image':
        _scrub_image(src, dst, ext)
    elif kind == 'pdf':
        note = _scrub_pdf(src, dst)
    elif kind == 'media':
        _scrub_media(src, dst)
    elif ext in ('.html', '.htm'):
        _scrub_html(src, dst)
        note = 'copied as text; author and similar meta tags and comments removed'
    else:
        shutil.copyfile(src, dst)
    problems = outgoing_problems(dst)
    if problems:
        raise ScrubError(f'After scrubbing, {os.path.basename(src)!r} still carries {", ".join(problems)}. It was not published. Re-save it without metadata (or leave it unshared).')
    return note


_EXIF_BAD = {'author', 'creator', 'subject', 'title', 'artist', 'keywords', 'copyright', 'imagedescription', 'description', 'xpauthor', 'xptitle', 'xpsubject',
             'xpcomment', 'usercomment', 'ownername', 'gpslatitude', 'gpslongitude', 'gpsposition', 'gpscoordinates', 'location'}


def _exiftool_problems(path):
    """A second, independent read-back when exiftool is installed."""
    if not have('exiftool'):
        return []
    r = run(['exiftool', '-j', '-a', '-s', path], 120)
    try:
        data = json.loads(r.stdout or '[]')[0]
    except (ValueError, IndexError):
        return []
    return [f'a {k} tag' for k, v in data.items() if v and k.lower() in _EXIF_BAD]


def outgoing_problems(path):
    kind, _ext = kind_of(path)
    if kind == 'image':
        out = _image_problems(path)
    elif kind == 'pdf':
        out = _pdf_problems(path)
    elif kind == 'media':
        out = _media_problems(path)
    elif path.lower().endswith(('.html', '.htm')):
        return _html_problems(path)
    else:
        return []
    return out + [x for x in _exiftool_problems(path) if x not in out]


def pdf_text(path):
    """Text layer of a PDF for the marker scan, or None when pdftotext is missing or the PDF has no text."""
    if not have('pdftotext'):
        return None
    r = run(['pdftotext', '-layout', path, '-'], 120)
    return r.stdout if r.returncode == 0 and r.stdout.strip() else None
