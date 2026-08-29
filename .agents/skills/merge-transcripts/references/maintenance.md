# Continuous improvement procedure

Apply this only after a real task demonstrates a reusable improvement.

## Classify the finding

- Repeated, deterministic transformation or detection: change code and add a regression test.
- Context-dependent judgment or review obligation: update the Skill or checklist.
- One meeting's label, vocabulary, time offset, or correction: keep it in that meeting's session JSON.
- Unsupported speculation or a one-off preference: do not turn it into a global rule.

## Regression-first update

1. Reduce the failure to the smallest synthetic or irreversibly anonymized fixture.
2. Add a test that fails for the demonstrated reason.
3. Make the narrowest code or documentation change.
4. Run the full unit suite, compile check, Skill validator, and an end-to-end CLI example.
5. Update `CHANGELOG.md` when behavior or the public configuration contract changes.

Do not copy a customer sentence merely with names removed if its substance is confidential. Prefer a freshly written synthetic equivalent.

## Release and synchronization

Keep the GitHub repository as the canonical source. The installed Codex Skill should remain a symlink to the checkout, so local Skill behavior follows reviewed repository changes. Do not replace an existing unrelated skill path. Commit or push only when the current task authorizes the external Git operation, and never include case configs, source transcripts, draft outputs, or review JSONL.
