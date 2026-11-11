#!/usr/bin/env python3
"""Make small, review-friendly copies of video evidence.

Originals are never touched. Each copy is 720p, 24 fps, H.264 with stereo 44.1 kHz AAC
and a loudness boost (quiet phone audio is the usual reason a reviewer hears nothing),
sized to stay under --max-mb so it can be uploaded to a review page.

  python3 proxy_clips.py CLIP_OR_DIR [CLIP_OR_DIR ...] --out proxies
Requires ffmpeg and ffprobe on PATH. Runs entirely on your machine.
"""
import argparse, os, subprocess, sys

VIDEO_EXT = ('.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm')


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


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
    ap.add_argument('--out', default='proxies')
    ap.add_argument('--max-mb', type=float, default=15.0, help='target size per clip (default 15)')
    ap.add_argument('--max-bitrate', type=int, default=1400, help='video kbit/s ceiling (default 1400)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    failed = 0
    for src in gather(a.inputs):
        cid = os.path.splitext(os.path.basename(src))[0]
        out = os.path.join(a.out, cid + '.mp4')
        d = duration(src)
        if d <= 0:
            print(f'SKIP  {cid}: unreadable or zero length (keep the original; note it in the catalogue)')
            failed += 1
            continue
        vb = int(min(a.max_bitrate, max(250, (a.max_mb * 8e6 / d) / 1000 - 100)))
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src,
               '-vf', "scale='min(720,iw)':-2,fps=24", '-c:v', 'libx264', '-preset', 'veryfast',
               '-b:v', f'{vb}k', '-maxrate', f'{int(vb * 1.3)}k', '-bufsize', f'{vb * 2}k', '-pix_fmt', 'yuv420p',
               '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '96k', '-ac', '2', '-ar', '44100',
               '-movflags', '+faststart', out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode or not os.path.exists(out):
            print(f'FAIL  {cid}: {r.stderr.strip()[:120]}')
            failed += 1
            continue
        mb = os.path.getsize(out) / 1e6
        flag = '  (over budget: shorten or lower --max-bitrate)' if mb > a.max_mb * 1.35 else ''
        print(f'OK    {cid}: {d:.1f}s -> {mb:.1f} MB{flag}')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
