#!/usr/bin/env python3
"""Make a tiny FICTIONAL example set so you can try the triage tools end to end.

  python3 make_example.py OUTPUT_DIR

Writes four synthetic clips (test patterns, not footage of anything), plus grades.csv and
review-queue.csv. Clip c02 is the same footage as c01 re-exported with a different colour
grade (a duplicate the dupcheck tool should catch). Nothing here is from a real case.
Requires ffmpeg on PATH.
"""
import csv, os, subprocess, sys

out = sys.argv[1] if len(sys.argv) > 1 else 'example-out'
os.makedirs(out, exist_ok=True)


def make(name, src, secs, tone):
    p = os.path.join(out, name + '.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'{src}=size=320x240:rate=24',
                    '-f', 'lavfi', '-i', f'sine=frequency={tone}:sample_rate=44100', '-t', str(secs),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', p], check=True)
    return p


c01 = make('c01', 'testsrc2', 6, 440)
c02 = os.path.join(out, 'c02.mp4')   # same footage, different colour grade
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', c01, '-vf', 'eq=saturation=0.8:gamma=1.05',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'copy', c02], check=True)
make('c03', 'smptebars', 6, 330)
make('c04', 'mandelbrot', 5, 220)

GRADES = [
    ['id', 'date', 'time', 'kind', 'caption', 'grade', 'tier', 'fold_into', 'excerpt_of', 'reviewed_by', 'owner_note', 'public_caption'],
    ['c01', '2024-08-14', '21:42', 'video', 'Cluster dark at speed; she says it is “no clue why” (6 s)', 'B', 'B1', '', '', 'assistant', '', ''],
    ['c02', '2024-08-14', '21:42', 'video', 'Cluster dark at speed, exported again (6 s)', 'B', 'B2', '', '', 'assistant', '', ''],
    ['c03', '2024-09-02', '08:10', 'video', 'Door handle will not present on the third pull (6 s)', 'B', 'B1', '', '', 'assistant', '', ''],
    ['c04', '2024-09-02', '08:15', 'video', 'Out-of-focus close-up, nothing identifiable (5 s)', 'C', '', '', '', 'assistant', '', ''],
]
with open(os.path.join(out, 'grades.csv'), 'w', newline='', encoding='utf-8') as f:
    csv.writer(f).writerows(GRADES)

QUEUE = [
    ['id', 'title', 'when', 'current_grade', 'proposed_grade', 'watch_for', 'frames_note', 'media', 'original', 'flags'],
    ['c03', 'Door handle on the third pull', '2024-09-02 08:10', 'B1', 'B1',
     'Does the handle stay flush when the hand pulls? Note the second.',
     'Sampled frames show a hand near a handle; whether it extends happens between frames.', 'proxies/c03.mp4', '', ''],
    ['c01', 'Cluster dark at speed', '2024-08-14 21:42', 'B1', 'B1',
     'Does the cluster go dark on camera, or only in her narration?',
     'Frames show a lit display throughout; the outage may fall between frames.', 'proxies/c01.mp4', '', 'plate visible at 0:03'],
]
with open(os.path.join(out, 'review-queue.csv'), 'w', newline='', encoding='utf-8') as f:
    csv.writer(f).writerows(QUEUE)
print('wrote example clips and CSVs in', out)
