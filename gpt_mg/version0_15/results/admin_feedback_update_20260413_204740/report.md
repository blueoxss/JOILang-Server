# version0_15 admin feedback update

- admin_case_count: 0
- admin_replay_case_count: 0
- admin_working_row_count: 0
- admin_failing_row_count: 0
- manual_rule_count: 0
- final_genome_json: /home/andrew/joi-llm/gpt_mg/version0_15/results/admin_feedback_update_20260413_204740/best_after_ga.json
- promotion_performed: True
- promotion_reason: benchmark_ok_no_admin_rows

## Benchmark Guard
{
  "ok": true,
  "avg_det_score_non_decreasing": true,
  "avg_gt_similarity_non_decreasing": true,
  "gt_exact_count_non_decreasing": true,
  "fail_count_non_increasing": true,
  "before": {
    "row_count": 1,
    "avg_det_score": 96.7414,
    "avg_gt_similarity": 0.8914,
    "gt_exact_count": 0,
    "pass_count": 1,
    "fail_count": 0,
    "top_failure_types": [],
    "failed_row_nos": [],
    "failed_cases": []
  },
  "after": {
    "row_count": 1,
    "avg_det_score": 98.898,
    "avg_gt_similarity": 0.9633,
    "gt_exact_count": 0,
    "pass_count": 1,
    "fail_count": 0,
    "top_failure_types": [],
    "failed_row_nos": [],
    "failed_cases": []
  }
}

## Admin Guard
{
  "ok": true,
  "reason": "not_applicable"
}

