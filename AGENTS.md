# Transcript Reconciler development guide

This repository contains a deterministic assistant for reconciling multiple AI-generated transcripts of the same meeting. It does not replace contextual review by Codex or a human.

## Project rules

- Support Python 3.10 or newer and keep the runtime dependency-free unless a demonstrated format requirement justifies a dependency.
- Keep parsers, alignment heuristics, rendering, and auditing separate from meeting-specific corrections.
- Never commit customer transcripts, real names, cloud-storage paths, or generated review reports. Tests must use synthetic or irreversibly anonymized fixtures.
- Do not silently resolve ambiguous speaker boundaries. Surface them in the review report or require an explicit segment-indexed override.
- Add a regression fixture before or with every reusable bug fix.
- Run `python3 -m unittest discover -s tests -v`, `python3 -m compileall -q src scripts`, and the bundled Skill validator before committing changes.
- Preserve the user's per-meeting output contract. Do not globalize vocabulary, labels, or formatting from one interview.
