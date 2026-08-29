# Session configuration reference

The session file is UTF-8 JSON. Relative paths are resolved from the JSON file's directory. See `examples/session.example.json` in the repository for a complete example.

## `sources`

At least two sources are required.

- `id`: Unique identifier used by alignment settings.
- `path`: Absolute path or path relative to the session JSON.
- `format`: `csv`, `vtt`, `srt`, `md`, or `txt`.
- `roles`: Descriptive values such as `chunk`, `text`, `speaker`, or `timing`. Roles document intent; authority is selected explicitly under `alignment`.
- `columns`: For CSV, maps logical fields `start`, `end`, `display_time`, `speaker`, `text`, and `interviewee` to actual headers. Common English and Japanese headers are auto-detected, but explicit mappings are safer.
- `speaker_map`: Optional mappings that apply only to this source.
- `options.default_speaker`: Optional fallback for caption or text formats without embedded names.

Markdown and text paragraphs may begin with `**Speaker:**`, `Speaker:`, or `Speaker：`. A leading bracketed timestamp is recognized. Untimed sources can provide contextual matches but cannot be the skeleton or boundary authority in version 0.1.

## `alignment`

- `skeleton_source`: Timestamped source that defines ordinary readable chunk intervals.
- `boundary_source`: Timestamped fine-grained source used for speaker evidence.
- `min_anchor_chars`: Minimum normalized matching block length. Default `4`; very short values cause false anchors.
- `meaningful_speaker_score`: Score above which a second speaker receives an additional ambiguity flag.
- `low_margin_score`: Flag when the two leading speaker scores are closer than this value.
- `evidence_max_matches`: Maximum contextual matches retained per additional source and skeleton segment.

## `speaker_map` and `fallback`

`speaker_map` normalizes raw participant names or IDs to final labels. `fallback` is used only when boundary evidence is unavailable:

- `metadata_field`: Usually the normalized CSV metadata field `interviewee`.
- `true_values`: Case-insensitive values treated as the interviewee class.
- `true_speaker`, `false_speaker`, `default_speaker`: Output labels.

Fallback classification does not prove a speaker boundary inside a mixed row.

## `replacements`

Each object has `from` and `to`. Replacements are literal and global. Use them only for corrections safe in every occurrence. Put contextual corrections inside a segment override.

## `overrides`

Each override identifies a zero-based skeleton `segment`. Use the narrowest form that records the decision actually made:

- `text`: Correct only the wording and keep speaker inference active. A text-only override does not resolve a speaker-boundary review candidate.
- `speaker`: Fix only the speaker and keep the skeleton text.
- `speaker` plus `text`: Fix both fields while keeping the segment as one chunk.
- `chunks`: Replace the segment with ordered chunks, each containing `speaker` and `text`. An empty array intentionally suppresses the source segment.

Do not combine `chunks` with scalar `speaker` or `text`. Speaker and chunk overrides count as explicit boundary decisions; text-only overrides do not. The reconciler rejects override indexes that do not exist in the parsed skeleton instead of silently ignoring them. Indexes avoid collisions caused by repeated displayed timestamps, but the private session configuration must stay with the exact source files it was reviewed against.

```json
{
  "overrides": [
    {"segment": 10, "text": "Corrected wording."},
    {"segment": 11, "speaker": "Interviewee"},
    {
      "segment": 12,
      "chunks": [
        {"speaker": "Moderator", "text": "Question."},
        {"speaker": "Interviewee", "text": "Answer."}
      ]
    }
  ]
}
```

## `output`

- `path` and `review_path`: Optional default output paths.
- `allowed_speakers`: Complete set of labels permitted in the final transcript.
- `label_template`: Must contain `{speaker}` and `{text}`.
- `label_regex`: Audit pattern with named groups `speaker` and `text`.
- `prohibit_headings`: Reject Markdown headings when body-only output is required.
- `forbidden_patterns`: Regular expressions for raw IDs, original names, metadata markers, or known uncorrected forms.
- `quote_pairs`: Pairs whose opening and closing counts must match.
