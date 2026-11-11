#!/usr/bin/env python3
"""Dense contact sheets of video evidence, for an assistant (or you) to review.

A sheet is a 4-column grid read left to right, top to bottom. Frame i sits at
(i + 0.5) * duration / frames seconds. Short clips get 8 frames, long clips up to 20.
Sheets show what is VISIBLE in sampled frames. They cannot show motion between frames
or sound, so anything whose grade depends on movement or audio belongs on the watch list.

  python3 contact_sheets.py CLIP_OR_DIR [...] --out sheets
Requires ffmpeg and ffprobe on PATH.
"""
import argparse, json, math, os, subprocess, sys

VIDEO_EXT = ('.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm')


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def frame_count(d):
    return 8 if d <= 6 else 12 if d <= 30 else 16 if d <= 90 else 20


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
    ap.add_argument('--out', default='sheets')
    ap.add_argument('--width', type=int, default=480, help='frame width in pixels (default 480)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    index, failed = {}, 0
    for src in gather(a.inputs):
        cid = os.path.splitext(os.path.basename(src))[0]
        d = duration(src)
        if d <= 0:
            print(f'SKIP  {cid}: unreadable')
            failed += 1
            continue
        n = frame_count(d)
        out = os.path.join(a.out, cid + '.jpg')
        vf = f'fps={n}/{d},scale={a.width}:-2,tile=4x{math.ceil(n / 4)}'
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', vf, '-frames:v', '1', '-q:v', '4', out],
                           capture_output=True, text=True)
        if r.returncode or not os.path.exists(out):
            print(f'FAIL  {cid}: {r.stderr.strip()[:120]}')
            failed += 1
            continue
        index[cid] = {'sheet': out, 'duration_s': round(d, 2), 'frames': n,
                      'frame_times_s': [round((i + 0.5) * d / n, 1) for i in range(n)]}
        print(f'OK    {cid}: {n} frames over {d:.1f}s')
    with open(os.path.join(a.out, 'index.json'), 'w') as f:
        json.dump(index, f, indent=1)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
