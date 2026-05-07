# JOILang Prompt Context Study

## Study Scope

- Baseline result dirs: 1
- Retrieval result dirs: 1
- Runnable models in both conditions: 2
- Blocked or unrun models: 1

## Main Findings

- Best quality condition: `qwen25_coder_14b` under `retrieval` with strict DET `91.16`.
- Fastest condition: `qwen25_coder_7b` under `retrieval` with warm latency p50 `2.59` s.
- Largest strict DET gain from retrieval: `qwen25_coder_14b` (`6.45`).
- Largest prompt reduction: `qwen25_coder_14b` (`54.42%`).

## Category Findings

- Strongest category gain: model `qwen25_coder_14b`, category `1`, delta DET `12.89`.
- Largest category drop: model `qwen25_coder_7b`, category `1`, delta DET `-9.58`.

## Strengths

- At least two deployment-relevant local models completed both baseline and retrieval conditions.
- Prompt compression effect is large enough to support a token-efficiency claim.
- Retrieval premapping improves strict DET for at least one strong local model.

## Limitations

- The intended five-model local suite is not fully executable under the current environment; blocked models must be reported transparently.
- The strongest claim should be framed around the runnable Qwen local subset unless the blocked models are fixed and rerun.

## Output Files

- `combined_suite_condition.csv`
- `combined_category_condition.csv`
- `condition_delta_by_model.csv`
- `condition_delta_by_category.csv`
- `condition_delta_by_row.csv`
- `availability_summary.csv`
