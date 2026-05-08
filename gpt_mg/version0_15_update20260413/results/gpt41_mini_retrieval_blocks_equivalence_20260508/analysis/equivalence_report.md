# Cloud Monolith vs Blocks Equivalence Report (GPT-4.1-mini)

## 1. Goal

Validate whether `prompt_render_mode=blocks` preserves pass-level behavior of the cloud prompt baseline (`legacy_v13_monolith`) under the same retrieval + strict DET benchmark setup.

## 2. B Run (Blocks) Execution

Command used:

```bash
bash gpt_mg/version0_15_update20260413/scripts/run_gpt41_mini_by_category.sh \
  --condition retrieval \
  --prompt-render-mode blocks \
  --retrieval-device cpu \
  --output-root gpt_mg/version0_15_update20260413/results/gpt41_mini_retrieval_blocks_equivalence_20260508
```

Model/runtime:

- model key: `gpt41_mini`
- endpoint: `https://api.openai.com/v1/chat/completions`
- suite: `paper_with_cloud_ref`
- dataset: `datasets/JOICommands-280.csv`
- DET profile: `strict`
- candidate-k: `1`
- repair-attempts: `0`
- retrieval: `hybrid`, `topk=10`

Reference manifest example:

- `.../retrieval_gpt41_mini_cat1/suite_manifest.json`
- `prompt_render_mode = "blocks"` verified

## 3. Aggregate Result

Blocks (B) summary:

- total rows: `280`
- total pass: `267`
- total fail: `13`
- pass rate: `95.36%`

Conclusion:

- `blocks` did **not** reach all-pass under this run.
- Equivalence to cloud monolith baseline is **not yet achieved**.

## 4. Category Breakdown (Blocks)

| Category | Rows | Pass | Fail |
| --- | ---: | ---: | ---: |
| 1 | 30 | 28 | 2 |
| 2 | 30 | 30 | 0 |
| 3 | 30 | 30 | 0 |
| 4 | 30 | 28 | 2 |
| 5 | 30 | 30 | 0 |
| 6 | 30 | 27 | 3 |
| 7 | 50 | 47 | 3 |
| 8 | 50 | 47 | 3 |

## 5. Failure Rows (Blocks)

Fail rows (`13`):

- cat1: `2`, `13`
- cat4: `94`, `118`
- cat6: `157`, `175`, `178`
- cat7: `187`, `212`, `218`
- cat8: `247`, `259`, `271`

Detailed CSV:

- `analysis/category_failure_rows.csv`
- `analysis/failure_analysis.md`
- `analysis/failure_analysis.html`

## 6. Baseline Comparison Snapshot

Compared against prior monolith retrieval run root:

- `gpt_mg/version0_15_update20260413/results/gpt41_mini_retrieval_allcats_20260508`

Observed totals:

- monolith pass/fail: `273 / 7`
- blocks pass/fail: `267 / 13`
- delta: `-6` pass

Per-category pass delta (`blocks - monolith`):

- cat1: `-2`
- cat2: `0`
- cat3: `+2`
- cat4: `+1`
- cat5: `+1`
- cat6: `-2`
- cat7: `-3`
- cat8: `-3`

## 7. Prompt Locations

Cloud monolith prompt assets (`legacy_v13_monolith`):

- `gpt_mg/version0_13/caution_prompt_8.md`
- `gpt_mg/version0_13/grammar_ver1.5.10.md`
- `gpt_mg/version0_13/service_prompt_10.md`
- `gpt_mg/version0_13/tempo_prompt_9.md`
- `gpt_mg/version0_13/response_prompt_baseline_cot.md`

Renderer path:

- `gpt_mg/version0_15_update20260413/utils/pipeline_common.py`
  - `render_legacy_v13_monolithic_prompt(...)`
  - `LEGACY_V13_PROMPT_FILES`

Blocks prompt assets (`prompt_render_mode=blocks`):

- `gpt_mg/version0_15_update20260413/blocks/01_preamble.txt`
- `gpt_mg/version0_15_update20260413/blocks/02_generator_prompt.txt`
- `gpt_mg/version0_15_update20260413/blocks/03_postprocessor.txt`
- `gpt_mg/version0_15_update20260413/blocks/04_reranker_prompt.txt`
- `gpt_mg/version0_15_update20260413/blocks/05_repair_prompt.txt`
- `gpt_mg/version0_15_update20260413/blocks/06_det_helper.txt`

Resolver path:

- `gpt_mg/version0_15_update20260413/utils/pipeline_common.py`
  - `BLOCK_FILE_MAP`
  - `render_blocks_for_genome(...)`

