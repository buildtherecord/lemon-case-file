#!/usr/bin/env python3
"""Find clips that are the same footage, so one recording is never counted twice.

Compares clips by what they show, not by their captions or file names:
  1. exact duplicates (same SHA-256), then
  2. clips of similar length compared frame by frame with ffmpeg's SSIM score.

  SSIM >= 0.90   same footage (a re-export or re-upload)  -> fold one into the other
  0.60 - 0.90    very similar scene                        -> look before deciding
  below 0.60     different footage (a retake is NOT a duplicate)

A score is a lead, not a ruling: a person confirms before anything is folded, and a
folded clip is hidden and not counted, never deleted.

  python3 dupcheck.py CLIP_OR_DIR [...] [--window 1.0] [--all]
Requires ffmpeg and ffprobe on PATH.
"""
import argparse, hashlib, itertools, os, re, subprocess

VIDEO_EXT = ('.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm')


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def ssim(a, b, secs):
    flt = (f'[0:v]scale=320:240,fps=5,trim=duration={secs}[x];'
           f'[1:v]scale=320:240,fps=5,trim=duration={secs}[y];[x][y]ssim')
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', a, '-i', b, '-lavfi', flt, '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.findall(r'All:([0-9.]+)', r.stderr)
    return float(m[-1]) if m else None


def gather(inputs):
    for p in inputs:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                if name.lower().endswith(VIDEO_EXT):
                    yield os.path.join(p, name)
        else:
            yield p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--window', type=float, default=1.0, help='compare clips whose lengths differ by at most this many seconds')
    ap.add_argument('--all', action='store_true', help='compare every pair (slow on big sets)')
    a = ap.parse_args()
    files = list(gather(a.inputs))
    info = {f: duration(f) for f in files}
    name = lambda f: os.path.splitext(os.path.basename(f))[0]
    found = 0
    seen = {}
    for f in files:
        seen.setdefault(sha(f), []).append(f)
    for group in seen.values():
        if len(group) > 1:
            found += 1
            print('IDENTICAL FILES  ' + ' = '.join(name(g) for g in group))
    for x, y in itertools.combinations(files, 2):
        if not a.all and abs(info[x] - info[y]) > a.window:
            continue
        secs = max(1.0, min(info[x], info[y]) - 0.2)
        s = ssim(x, y, round(secs, 1))
        if s is None:
            continue
        if s >= 0.90:
            found += 1
            print(f'SAME FOOTAGE  {name(x)} / {name(y)}  ssim {s:.3f}  -> fold one into the other')
        elif s >= 0.60:
            found += 1
            print(f'VERY SIMILAR  {name(x)} / {name(y)}  ssim {s:.3f}  -> look before deciding')
    if not found:
        print('No duplicates or near-duplicates found.')


if __name__ == '__main__':
    main()
