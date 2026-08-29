# Review and completion checklist

## Source and coverage

- Confirm each input belongs to the same meeting and is read in the correct encoding.
- Compare segment counts, first timestamp, last timestamp, and gaps.
- Confirm why each source is trusted for chunks, wording, timing, or speakers.
- Do not claim audio verification unless the audio was actually checked.

## Speaker boundaries

- Review every `needs_review` record and every source gap.
- Inspect questions followed by answers, short acknowledgements, interruptions, sentence-final boundary words, and closing greetings.
- Confirm observer or third-party speech is not folded into a moderator or interviewee chunk.
- Use row indexes, not displayed timestamps alone, for repeated times.
- Sample supposedly high-confidence rows at the beginning, middle, and end.

## Wording

- Compare all sources before correcting a doubtful phrase.
- Verify proper nouns and current service names from authoritative sources when necessary.
- Keep meeting-specific terminology out of global replacements.
- Do not smooth away a meaningful hesitation, negation, number, qualification, or disagreement.
- Do not add a plausible sentence unsupported by any source.

## Output contract

- Every paragraph after a blank line begins with an allowed speaker label when requested.
- Required interviewee and team labels are exact.
- Required anonymity is complete; forbidden original names and source IDs are absent.
- Headings and metadata are present or absent exactly as requested.
- No `SPEAKER_*`, classifier flags, VTT tags, cue IDs, or timestamps leak into body-only output.

## Mechanical audit

- Run `transcript-reconcile audit` and resolve every error.
- Check adjacent duplicates and accidental omissions around overridden rows.
- Check Japanese quotation marks and any configured delimiter pairs.
- Record output paragraph count, speaker counts, and any unverified ranges.
