---
name: merge-transcripts
description: Reconcile two or more AI transcripts of the same meeting, including VTT, SRT, CSV, Markdown, or text exports, when accurate speaker boundaries and a reviewed final transcript are required. Do not use for single-source proofreading or for transcribing audio from scratch.
---

# Merge Transcripts

Use the repository's deterministic CLI to organize evidence and audits, then apply contextual judgment to ambiguous boundaries and wording. The CLI's draft is never the final authority.

## Required workflow

1. Read [references/workflow.md](references/workflow.md) before starting a merge.
2. Extract the user's output contract separately for each meeting: source roles, speaker labels, anonymity, headings or metadata, paragraph behavior, terminology, and whether audio verification is requested.
3. Keep customer inputs and meeting-specific configuration outside this repository. Resolve this `SKILL.md` to its real path; its fourth parent (`parents[3]`) is the tool repository. Use `scripts/transcript-reconcile` from that root.
4. Create or adapt a session JSON. Read [references/configuration.md](references/configuration.md) when selecting columns, source authorities, fallbacks, replacements, or overrides.
5. Run `inspect`, then `reconcile`. Review every JSONL record with `"needs_review": true`, plus the beginning, end, coverage gaps, short acknowledgements, and any region where source wording conflicts.
6. Store confirmed speaker or wording decisions as segment-indexed `overrides`. Use global `replacements` only when every occurrence is demonstrably safe. Rerun until the draft is reproducible.
7. Read [references/review-checklist.md](references/review-checklist.md), complete its contextual and mechanical checks, and run `audit` before delivery.

## Non-negotiable boundaries

- Treat a readable source as a chunk skeleton only when the current meeting supports that role. Treat a fine-grained source as speaker authority only after checking its actual coverage and speaker provenance.
- Do not invent a plausible utterance, silently merge conflicting source text, or assign an identity unsupported by the sources.
- Split questions, answers, short acknowledgements, boundary words, and closing greetings when speaker evidence requires it.
- Preserve meeting-specific vocabulary and labels in the session config; never import another meeting's dictionary blindly.
- If audio was not checked, describe the result as reconciliation of the supplied transcripts and context, not audio-perfect verification.
- If a source has a gap, identify the affected range and distinguish conservative fallback from verified evidence.

## Improving the workflow

When a completed meeting reveals a genuinely reusable failure mode, read [references/maintenance.md](references/maintenance.md). Add a synthetic regression fixture and make the narrowest code or documentation change. Keep one-off vocabulary and judgment in the meeting config. Do not commit or push customer data, and do not perform external Git operations unless currently authorized.
