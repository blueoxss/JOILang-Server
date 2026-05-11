# Cloud-to-Block Prompt Equivalence

This verifies that prompt block decomposition itself does not degrade the cloud reference behavior.

## Result

- model backend: gpt-4.1-mini/openai-compatible
- prompt modes compared: legacy_v13_monolith, blocks
- row/category scope: categories=1; limit_per_category=1
- DET profile: strict
- monolithic pass rate: None
- block-rendered pass rate: None
- mismatch count: None
- all-pass equivalence: False

## Files

- `summary.json`
- `monolith_vs_blocks.csv`
- `command.txt`
