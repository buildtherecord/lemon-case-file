#!/usr/bin/env python3
"""Builds the Build the Record ChatGPT plugin archive from this repository.

  python3 plugin/chatgpt/build.py [OUT.zip]

The archive holds plugin.json (also as .codex-plugin/plugin.json), the skill (SKILL.md) and its reference files,
which are copied from the method in this repository at build time, so the plugin never drifts from METHOD.md.
To install: ChatGPT, Plugins, Add, Upload plugin archive (where your plan offers it)."""
import json, os, shutil, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REFS = ['METHOD.md', 'prompts/00-START-HERE.md', 'prompts/01-evidence-inventory.md', 'prompts/01b-evidence-triage.md', 'prompts/02-timeline-and-bundle.md',
        'prompts/08-adversarial-review.md', 'prompts/09-redaction-and-publishing.md', 'docs/claimant-journeys/two-layer-model.md',
        'docs/claimant-journeys/safety-gates.md', 'schema/record.schema.json']


def main(argv):
    version = json.load(open(os.path.join(HERE, 'plugin.json')))['version']
    out = argv[0] if argv else os.path.join(REPO, f'build-the-record-{version}.zip')
    tmp = tempfile.mkdtemp()
    try:
        ref = os.path.join(tmp, 'skills', 'build-the-record', 'references')
        os.makedirs(ref)
        os.makedirs(os.path.join(tmp, '.codex-plugin'))
        for d in ('plugin.json',):
            shutil.copy(os.path.join(HERE, d), os.path.join(tmp, d))
            shutil.copy(os.path.join(HERE, d), os.path.join(tmp, '.codex-plugin', d))
        shutil.copy(os.path.join(HERE, 'skills', 'build-the-record', 'SKILL.md'), os.path.join(tmp, 'skills', 'build-the-record', 'SKILL.md'))
        shutil.copy(os.path.join(HERE, 'assistant-playbook.md'), ref)
        for r in REFS:
            shutil.copy(os.path.join(REPO, r), ref)
        seed = os.path.join(tmp, 'seed')
        subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'views', 'example', 'seed.py'), seed], check=True, capture_output=True)
        shutil.copy(os.path.join(seed, 'FULL3.json'), os.path.join(ref, 'estate-example-record.json'))
        shutil.rmtree(seed)
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, _d, files in os.walk(tmp):
                for f in sorted(files):
                    z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), tmp))
        print(f'wrote {out} (version {version})')
    finally:
        shutil.rmtree(tmp)


if __name__ == '__main__':
    main(sys.argv[1:])
