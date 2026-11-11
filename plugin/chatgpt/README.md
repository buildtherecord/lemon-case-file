# Build the Record for ChatGPT (plugin)

A ChatGPT plugin that walks a person through the method one step at a time: what happened, whose claim it is,
where the papers are (including Google Drive, with nothing to download), then a document list, a dated timeline,
a money table, and the gaps. It states only what documents show, quotes word for word, adds up totals from rows,
never calls anything a crime, and is not legal advice.

- `plugin.json`: the manifest. Bump `version` for each release.
- `skills/build-the-record/SKILL.md`: the assistant's instructions.
- `assistant-playbook.md`: the page layout and note format.
- `build.py`: builds the archive, copying the reference files from this repository's method.

Build: `python3 plugin/chatgpt/build.py`. Install: ChatGPT, Plugins, Add, Upload plugin archive, where your plan offers it.
Status: prototype. Uploading has not yet been confirmed to work on personal ChatGPT accounts.
