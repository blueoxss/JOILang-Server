# version0_14

A self-contained prompt-block + GA + DET workspace that lives entirely under `gpt_mg/version0_14/`.

## Goals
- Generate JOILang JSON from `datasets/JOICommands-280.csv`
- Use `datasets/service_list_ver2.0.1.json` as the authoritative schema
- Score candidates with a deterministic evaluator
- Search prompt/block/parameter combinations with a genetic algorithm
- Trigger a constrained prompt-surgery feedback loop when validation plateaus
- Persist logs, genomes, checkpoints, patch attempts, and reports only inside `gpt_mg/version0_14/`

## Folder Layout
```text
version0_14/
  README.md                         # this guide
  blocks/
    01_preamble.txt                # global deterministic rules
    02_generator_prompt.txt        # main generator prompt with 3 exemplars
    03_postprocessor.txt           # JSON/output cleanup rules
    04_reranker_prompt.txt         # rerank/repair scaffold
    05_repair_prompt.txt           # targeted repair prompt with 3 exemplars
    06_det_helper.txt              # evaluator-aware helper instructions
    generated/                     # auto-created patched prompt variants
  genomes/
    example_genome.json            # baseline genome schema example
  scripts/
    run_generate.py                # generate K candidates per row
    run_rerank.py                  # DET score + repair low-scoring rows
    run_feedback_loop.py           # validation + prompt-surgery loop
    run_ga_search.py               # GA orchestration with plateau handling
    run_full_pipeline.sh           # example end-to-end wrapper
    commit_results.py              # safe git instructions/patch export
  utils/
    pipeline_common.py             # shared path/rendering/dataset helpers
    det_evaluator.py               # pure programmatic DET evaluator
    local_llm_client.py            # local worker / OpenAI-compatible adapter
  results/                         # per-genome JSON, CSV, summaries, patches
  logs/                            # prompt/response logs
  checkpoints/                     # GA generation checkpoints
```

## Quick Run
From the repository root:

```bash
cd /home/andrew/joi-llm/gpt_mg/version0_14

python3 scripts/run_generate.py \
  --profile version0_14 \
  --genome-json genomes/example_genome.json \
  --limit 5 \
  --candidate-k 2
```

Quick GA search:

```bash
python3 scripts/run_ga_search.py \
  --profile version0_14 \
  --genome-json genomes/example_genome.json \
  --population 4 \
  --gens 3 \
  --sample-size 5 \
  --validation-size 5 \
  --limit 5
```

Explicit feedback loop on a genome:

```bash
python3 scripts/run_feedback_loop.py \
  --profile version0_14 \
  --genome-json genomes/example_genome.json \
  --validation-size 5 \
  --limit 5
```

## Manual Feedback Rules
If you want prompt surgery to respect a hand-written rule, add it under:

```text
gpt_mg/version0_14/logs/manual_feedback.txt
```

One rule per line is enough. Lines starting with `#` are ignored. The feedback loop also scans JSON files under `logs/feedback_attempt_*` and will consume top-level keys such as `manual_feedback`, `manual_rules`, `feedback_notes`, or `prompt_rules` if you add them manually.

Example:

```text
# keep receiver tags unchanged
Keep receiver tags after # unchanged, such as #Kitchen or #LivingRoom.
Lowercase every service or value token after ). or all(...). so Device_Service becomes device_service.
```

When `run_feedback_loop.py` runs, those manual rules are appended under `MANUAL FOCUS RULES` inside patched prompt blocks written to `blocks/generated/`, and the patched genome JSON is saved under `results/patch_attempts/...`.

Rerank + repair candidates:

```bash
python3 scripts/run_rerank.py \
  --profile version0_14 \
  --genome-json genomes/example_genome.json \
  --candidates-csv results/candidates_gen-example-version0-14.csv
```

End-to-end example:

```bash
bash scripts/run_full_pipeline.sh --profile version0_14 --mode quick
bash scripts/run_full_pipeline.sh --profile version0_14 --mode full
```

Compare one row across generations like `query_*.sh`:

```bash
bash scripts/query_generations.sh 183
bash scripts/query_generations.sh --row-no 183
bash scripts/query_generations.sh --row-no 183 --only-best
bash scripts/query_generations.sh --row-no 275 --category 8
bash scripts/query_generations.sh "Lock the doorlock every day at midnight."
```

Render overall/category DET tables. The default pass threshold is now `50`, and the script writes markdown, HTML heatmap, PNG heatmap, and CSV tables under `results/`. A threshold suffix is added automatically, such as `_t50` or `_t70`.

```bash
python3 scripts/report_generations.py
python3 scripts/report_generations.py --pass-threshold 50
python3 scripts/report_generations.py \
  --pass-threshold 50 \
  --output-markdown results/generation_report.md \
  --output-html results/generation_report.html \
  --output-png results/generation_report.png \
  --output-csv-prefix results/generation_report

python3 scripts/report_generations.py \
  --pass-threshold 70 \
  --output-markdown results/generation_report.md \
  --output-html results/generation_report.html \
  --output-png results/generation_report.png \
  --output-csv-prefix results/generation_report
```

Generated report artifacts:

```text
results/generation_report_t50.md
results/generation_report_t50.html
results/generation_report_t50.png
results/generation_report_t50_overall.csv
results/generation_report_t50_category_pass.csv
results/generation_report_t50_category_exact.csv
results/generation_report_t50_category_avg.csv
```

## CLI Compatibility
The main scripts support the selection flags used throughout the repo:
- `--profile`
- `--limit`
- `--start-row`
- `--end-row`

## Local LLM Defaults
`utils/local_llm_client.py` defaults to `worker` mode and reuses the local worker at:
- `gpt_mg/version0_13/qwen_local_worker.py`

Environment overrides:
- `JOI_V14_LLM_MODE=worker|openai|mock`
- `JOI_V14_WORKER_PATH=/abs/path/to/qwen_local_worker.py`
- `JOI_V14_WORKER_PYTHON=/abs/path/to/python`
- `JOI_V14_LOCAL_DEVICE=cuda:1`
- `JOI_V14_OPENAI_ENDPOINT=http://host:port/v1/chat/completions`

## DET Metrics
`utils/det_evaluator.py` computes:
- `det_valid_json`
- `det_schema_ok`
- `det_service_match`
- `det_arg_type_ok`
- `det_precondition_ok`
- `det_semantic_ok`
- `det_min_extraneous`
- `det_score`

Default weighted score:
- schema: 20%
- service match: 25%
- arg type: 20%
- precondition: 10%
- semantic: 20%
- extraneous penalty: 5%

Invalid JSON is treated as zero fitness.

## Results And Logs
Important outputs:
- `results/candidates_*.csv` - raw generated candidates per row
- `results/rerank_*.csv` - selected output plus DET fields
- `results/genome_<id>.json` - per-genome evaluation payload
- `results/best_genomes.json` - generation-by-generation best history
- `results/ga_summary.json` - final GA summary
- `results/patch_attempts/...` - feedback loop reports and patched genomes
- `logs/...` - prompt/response traces for auditability
- `checkpoints/ga_generation_*.json` - GA checkpoints

## Notes
- Placeholder substitution is implemented with explicit string replacement, not Python `f-string` formatting. This avoids accidental brace interpolation bugs inside prompt text.
- Prompt surgery only writes new prompt variants under `blocks/generated/` and new genome JSON files under `results/patch_attempts/`.
- This workspace intentionally does not modify `utils/build_profile_csv.py`, `query_raw.sh`, or other files outside `gpt_mg/version0_14/`.
