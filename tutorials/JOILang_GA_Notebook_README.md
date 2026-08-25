# JOILang GA Search Tutorial Notebooks

These files are the canonical tutorial files for `tutorial/`.

They replace/update:

- `tutorial/01_cloudless_det_feedback_ga_search.ipynb`
- `tutorial/02_cloud_only_feedback_ga_search.ipynb`
- `tutorial/03_merged_feedback_ga_search.ipynb`
- `tutorial/JOILang_GA_Notebook_README.md`

## Canonical runtime

All notebooks use only the repository-level canonical runtime:

```bash
python -m utils.ga_search.cli
```

They do **not** call:

```bash
gpt_mg/version0_15_update20260413/scripts/run_ga_search.py
gpt_mg/version0_15_update20260413/scripts/run_benchmark.py
gpt_mg/version0_15_update20260413/scripts/run_feedback_loop.py
```

The `gpt_mg/version0_15_update20260413` package is backup/reference only and should not be required.

## Tutorial files

### 01_cloudless_det_feedback_ga_search.ipynb

Use this first.

It checks:

- canonical import origin;
- `python -m compileall utils`;
- render smoke;
- strict DET eval using official `gt`;
- `engine-mode=mock` foundation path;
- `engine-mode=real` + `llm-mode=local` unavailable honesty test;
- optional worker real row smoke;
- prompt patch application;
- patch visibility;
- prompt logs/raw response paths.

### 02_cloud_only_feedback_ga_search.ipynb

Use this after the cloudless notebook.

It checks:

- strict DET evidence generation;
- cloud/hybrid advisor dry-run artifacts;
- advisor transport/effectiveness checks with artifacts;
- advisor-generated prompt patches;
- patch-applied search;
- optional OpenAI smoke.

### 03_merged_feedback_ga_search.ipynb

Use this after 01 and 02.

It checks:

- strict DET primary signal;
- cloud/advisor auxiliary evidence;
- baseline vs hybrid-patched search;
- advisor effectiveness via `--run-dir`;
- prompt patch report;
- optional worker real comparison.

## Required policy

- Official ground truth column: `gt`
- `gt_raw` is not used as official evaluation GT.
- Official metric: strict DET
- Cloud/advisor feedback: auxiliary only
- `llm-mode=mock`: deterministic smoke/foundation path
- `llm-mode=worker|local|openai`: real generation or explicit failure, never silent mock fallback

## Recommended smoke commands

```bash
cd /root/llm/JOILang-Server

python -m compileall utils

./run_eval_pipeline_check.sh smoke2 /root/llm/JOILang-Server
./run_ga_search_check.sh smoke /root/llm/JOILang-Server
```

## Optional worker configuration

For real local worker smoke, set the worker path and model path:

```bash
export JOI_GA_MODEL=gpt_mg.version0_13
export MODEL_KEY=qwen25_coder_14b
export JOI_GA_WORKER_PATH=gpt_mg/version0_13/qwen_local_worker.py
export JOI_GA_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python
export JOI_GA_LOCAL_MODEL_NAME=/home/mgjeong/Desktop/llm/local_models/qwen25_coder_14b
export JOI_GA_LOCAL_DEVICE=cuda:0
```

Then enable `RUN_WORKER_REAL = True` inside the relevant notebook cell.

## Optional OpenAI configuration

For OpenAI smoke, set your endpoint/API key according to the current `utils.ga_search.llm_backends` implementation and then enable:

```python
RUN_OPENAI_SMOKE = True
```

inside `02_cloud_only_feedback_ga_search.ipynb`.

## Interpretation

The notebooks are designed to separate:

1. canonical runtime health;
2. mock deterministic artifact validation;
3. explicit non-mock failure behavior;
4. real worker/openai generation when environment is ready;
5. advisor artifact and patch visibility checks.

A PASS in mock mode confirms the pipeline and artifact structure, not model quality.

## 04_premapping_finetune_nl2joilang_pipeline.ipynb (separate series)

- Not part of the GA notebook series above; the canonical-runtime-only rule does not apply to it.
- Full paper pipeline for Service Pre-mapping: data load -> role-document corpus -> query pools
  (template / LLM-audited natural / clause) -> fine-tuning pairs -> `intfloat/e5-small` MNRL
  fine-tuning -> held-out retrieval evaluation -> split pre-mapping with clause decomposition ->
  fine-tuned retrieval bundle for `gpt_mg/version0_15_update20260413` -> NL-to-JOILang generation
  (gpt-4.1-mini) -> strict DET evaluation on `JOICommands-280.csv`.
- Unlike 00-03 it runs training and retrieval inside the kernel: start the kernel from the `joi`
  conda environment (torch + sentence-transformers) and export `OPENAI_API_KEY` beforehand.
- Natural-query role labels are cached in `tutorials/data/query_roles_ver2.0.1.json`; with the cache
  present the only API calls are the generation/evaluation rows (`N_DET_ROWS`, default 8).
- Artifacts: `artifacts/premapping_pipeline_runs/<RUN_TAG>/`.

## 05_fullprompt_v06_nl2joilang_eval.ipynb (separate series)

- Reproduces the GPS paper's full-prompt baseline conditions on JOICommands-280:
  CloudRef (gpt-4.1-mini) and DirectTransfer (Qwen2.5-Coder-7B-Instruct from local_models).
- Gate first: premapping device recall must be 1.0 over all retrieval rows (fine-tuned e5 bundle,
  mandatory-category boosts, shortlist k=12) before generation runs.
- Prompt: ModelMagementApp/gpt_mg/version0_6 monolith assets (read-only) with the service lists
  swapped to ver2.0.1; the service field is rendered as the runtime call name
  {device}_{service} (lowercase) to preserve the prompt's "call exactly as listed" contract.
- Evaluation: utils/evaluation/compare_soplang_ir (PLY parser + z3 logic equivalence,
  script/ast similarity) plus strict DET (utils/det_evaluator, det_pass@70).
- Kernel: joi conda env; export OPENAI_API_KEY beforehand. Generation loops resume from
  artifacts/fullprompt_runs/<RUN_TAG>/*.jsonl, so interrupted runs continue where they stopped.

## 06_ga_prompt_search_full_loop.ipynb (separate series)

- Full GPS-style loop in one notebook: stratified testset subsets -> premapping recall gate +
  per-row shortlist schema blocks -> premapped prompt genotype GA (blocks/versions/micro-rules/
  few-shot) with local Qwen generation -> strict DET (+z3) fitness -> diagnosis-guided mutation
  by a DIFFERENT model (gpt-4.1-mini advisor; R4+ adds a cross-model judge that separates
  real errors from valid alternatives).
- 5 recalibration rounds; each round loops generations until the subset score reaches TARGET
  (90) or MAX_GEN, then adopts via a regression gate (R3+). Final adopted prompt is evaluated
  on a 60-row holdout against the DirectTransfer / CloudRef baselines (notebook-05 caches).
- Resumable: eval cache keyed by (genome hash, row), state.json / history.jsonl checkpoints.
- Kernel: joi env; export OPENAI_API_KEY. Artifacts: artifacts/ga_prompt_search/<RUN_TAG>/.
- Prerequisites: notebook 04 (premap bundle, PREMAP_RUN_TAG=v201_paper) and notebook 05
  (full-prompt baseline caches, FULLPROMPT_RUN_TAG=fullprompt_v06_ver201) must have run first.
- Staged verification before a full run (new RUN_TAG whenever the code changes - a completed
  tag only replays its caches and validates nothing; steps 1-2 write to a scratch output,
  only step 3 is `--inplace`):
  1. `LLM_MODE=mock RUN_TAG=mock06_v8 ROUNDS=5 POP=3 MAX_GEN=2 SUBSET_N=6 SUBSET_N_FINAL=8 HOLDOUT_N=6 jupyter nbconvert --to notebook --execute 06_ga_prompt_search_full_loop.ipynb --output /tmp/mock_check.ipynb`
  2. same knobs with `RUN_TAG=smoke06_v8` (small real-path check)
  3. default knobs (full run): `jupyter nbconvert --to notebook --execute --inplace 06_ga_prompt_search_full_loop.ipynb` (default RUN_TAG=ga_loop_v8, paper-budget POP=10/MAX_GEN=12 - takes hours; completed tags only replay)
- Tag history and per-revision validation evidence live in `reviews/06_meta_review_ledger.md`
  (canonical); the notebook builder is `builders/build_nb06.py` and warns at build time when
  this README's staged tags fall out of sync.
- Reproducibility: the first run of a tag records every knob (incl. RENDER/EVAL_VERSION, the
  JOICommands-280.csv content sha, and PROMPT_ASSET_SHA fingerprinting the v0_6 prompt .md
  files + service schema) write-once in run_config.json; reopening the tag with any other knob
  value asserts immediately. z3 logic equivalence uses the notebook's own converter (ev3):
  ordered path-condition comparison, judgment domain fixed by the gold side (rows whose gold
  has convertible conditions), prediction-side failures count as False (not excluded), and
  per-reason coverage is reported in §8. Bumping RENDER/EVAL_VERSION means updating the staged
  tags here and in the notebook header together.
