# Transcript reconciliation workflow

## 1. Establish the contract

Record these facts before transforming text:

- Which source is easiest to read and should define ordinary chunk size?
- Which source has trustworthy microphone- or participant-based speaker separation?
- Which source has the strongest contextual wording?
- What are the required output labels, anonymity rules, headings, metadata, and blank-line behavior?
- Does every source cover the same time range?
- Is audio verification in scope, or are only transcript files being reconciled?

Do not infer these answers from a previous interview.

## 2. Configure sources

Use one timestamped source as `skeleton_source` and one timestamped, fine-grained source as `boundary_source`. Additional timed or untimed sources may be supplied as contextual evidence. The first version of the CLI requires every skeleton segment to have a start timestamp.

Map raw speaker IDs only to names allowed by the current output contract. Configure fallback identity separately; CSV speaker IDs, `TRUE/FALSE`, and similar classifier fields are never boundary evidence.

## 3. Inspect before aligning

Run:

```bash
transcript-reconcile inspect --config /path/to/session.json
```

Check counts, first and last timestamps, unexpected speakers, empty sources, and partial coverage. A clean-looking source can still have incorrect speaker boundaries.

## 4. Generate a provisional draft and review report

Run:

```bash
transcript-reconcile reconcile \
  --config /path/to/session.json \
  --output /path/to/draft.md \
  --review /path/to/review.jsonl
```

The tool treats each skeleton row as starting at its timestamp and ending at the next skeleton row's timestamp. It scores overlapping boundary cues using shared normalized text and time overlap. It does not automatically split a row with multiple speakers. A second speaker with only weak overlap is retained as diagnostic evidence but does not by itself force a review candidate; this prevents filler absent from the readable source from overwhelming the review queue.

Prioritize records marked `needs_review`, but also sample high-confidence records. For each candidate, compare the skeleton text, ordered boundary cues, speaker scores, and additional source matches. Very short acknowledgements may have weak shared-text evidence even when their speaker timing is decisive.

## 5. Record decisions reproducibly

Add a segment-indexed override for every confirmed split or meeting-specific wording correction. The index is stable even when displayed timestamps repeat. Use a replacement only when the same correction is safe in all occurrences.

Rerun the command after editing the config. Do not make an important final correction only in the generated Markdown; it would be lost on regeneration.

## 6. Contextual wording review

Compare both or all supplied sources. Prefer a source-supported form that fits the surrounding conversation. For uncertain proper nouns, services, product names, or domain terms, search authoritative sources when current instructions permit it. Keep a note of unresolved uncertainty instead of fabricating certainty.

## 7. Audit and deliver

Run:

```bash
transcript-reconcile audit \
  --config /path/to/session.json \
  --input /path/to/final.md
```

Complete the linked review checklist. Report uncovered time ranges, unresolved wording, and whether audio was checked.
