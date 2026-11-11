"""Shared by the tests: paths, the example records written once into a temp folder, and a way to run a builder like a person would."""
import atexit, copy, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWS = os.path.dirname(HERE)
sys.path.insert(0, VIEWS)
sys.path.insert(0, os.path.join(VIEWS, 'example'))
import checks, btr_scrub as scrub  # noqa: E402

try:
    import PIL  # noqa: F401
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False
HAVE_FFMPEG = shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None
HAVE_POPPLER = shutil.which('pdfinfo') is not None and shutil.which('pdftoppm') is not None
needs_pillow = unittest.skipUnless(HAVE_PIL, 'Pillow is not installed')
needs_pdf_tools = unittest.skipUnless(HAVE_PIL and HAVE_POPPLER, 'Pillow and poppler are needed')
needs_ffmpeg = unittest.skipUnless(HAVE_PIL and HAVE_FFMPEG, 'ffmpeg is needed')

_tmp = []


def tmpdir(prefix='btr-test-'):
    d = tempfile.mkdtemp(prefix=prefix)
    _tmp.append(d)
    return d


atexit.register(lambda: [shutil.rmtree(d, ignore_errors=True) for d in _tmp])
_seeds = {}


def seeds():
    """The 20 example records and their placeholder files, written once per test run. -> (folder, [ids])"""
    if 'dir' not in _seeds:
        import seed
        d = tmpdir('btr-seeds-')
        for id, rec in seed.all_records():
            rec = json.loads(json.dumps(rec))
            seed.write_files(d, id, rec)
            with open(os.path.join(d, f'{id}.json'), 'w', encoding='utf-8') as fh:
                json.dump(rec, fh, indent=1)
        _seeds['dir'] = d
        _seeds['ids'] = [i for i, _r in seed.all_records()]
    return _seeds['dir'], _seeds['ids']


def seed_record(id):
    d, _ = seeds()
    with open(os.path.join(d, f'{id}.json'), encoding='utf-8') as fh:
        return json.load(fh)


def write_record(rec, folder=None, name='record.json'):
    folder = folder or tmpdir()
    path = os.path.join(folder, name)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(rec, fh)
    return path


def run(tool, *args):
    """Runs build_views.py / build_home.py / checks.py / doctor.py as a command. -> (exit code, all output)"""
    r = subprocess.run([sys.executable, os.path.join(VIEWS, tool), *map(str, args)], capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout + r.stderr


def tree(root):
    """{relative path: bytes} for every file under root."""
    out = {}
    for dp, _d, names in os.walk(root):
        for n in names:
            p = os.path.join(dp, n)
            with open(p, 'rb') as fh:
                out[os.path.relpath(p, root).replace(os.sep, '/')] = fh.read()
    return out


def leftovers(folder):
    """Temp build folders or old-output folders left behind in `folder` (there should be none)."""
    return [n for n in os.listdir(folder) if n.startswith('.btr-build-') or '.btr-old-' in n]


def workspace(id='FULL1'):
    """A private copy of one example record and its files that a test may change. -> Workspace"""
    d, _ = seeds()
    folder = tmpdir()
    shutil.copytree(os.path.join(d, f'{id}-files'), os.path.join(folder, 'files'))
    with open(os.path.join(d, f'{id}.json'), encoding='utf-8') as fh:
        rec = json.load(fh)
    return Workspace(folder, rec)


class Workspace:
    def __init__(self, folder, rec):
        self.folder, self.rec = folder, rec
        self.files = os.path.join(folder, 'files')
        self.out = os.path.join(folder, 'out')
        self.private = self.out + '-private'

    @property
    def record_path(self):
        return write_record(self.rec, self.folder)

    def home(self, *extra, out=None):
        return run('build_home.py', self.record_path, out or self.out, '--files-dir', self.files, *extra)

    def views(self, *extra, out=None):
        return run('build_views.py', self.record_path, out or os.path.join(self.folder, 'inward'), *extra)

    def page(self, rel='index.html', out=None):
        with open(os.path.join(out or self.out, rel), encoding='utf-8') as fh:
            return fh.read()

    def report(self):
        with open(os.path.join(self.private, 'share-report.txt'), encoding='utf-8') as fh:
            return fh.read()

    def manifest(self):
        with open(os.path.join(self.private, 'manifest.json'), encoding='utf-8') as fh:
            return json.load(fh)

    def exhibit(self, id):
        return next(e for e in self.rec['exhibits'] if e['id'] == id)

    def fact(self, id):
        return next(f for f in self.rec['facts'] if f['id'] == id)


class Base(unittest.TestCase):
    """assertIn/assertNotIn that print a short snippet instead of a whole page."""
    def has(self, needle, text, note=''):
        if needle not in text:
            self.fail(f'expected {needle!r} but it is not there. {note} (text starts: {text[:160]!r})')

    def lacks(self, needle, text, note=''):
        if needle in text:
            i = text.index(needle)
            self.fail(f'did not expect {needle!r}. {note} (around it: {text[max(0, i - 80):i + 120]!r})')


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()
