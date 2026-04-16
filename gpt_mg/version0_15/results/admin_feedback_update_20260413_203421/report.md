# version0_15 admin feedback update

- admin_case_count: 1
- admin_replay_case_count: 1
- admin_working_row_count: 0
- admin_failing_row_count: 1
- manual_rule_count: 2
- final_genome_json: /home/andrew/joi-llm/gpt_mg/version0_15/results/admin_feedback_update_20260413_203421/best_after_admin_feedback.json
- promotion_performed: False
- promotion_reason: benchmark_skipped

## Benchmark Guard
{
  "ok": true,
  "reason": "not_applicable"
}

## Admin Guard
{
  "ok": true,
  "avg_det_score_non_decreasing": true,
  "avg_gt_similarity_non_decreasing": true,
  "gt_exact_count_non_decreasing": true,
  "fail_count_non_increasing": true,
  "before": {
    "row_count": 1,
    "avg_det_score": 24.0,
    "avg_gt_similarity": 0.3,
    "gt_exact_count": 0,
    "pass_count": 0,
    "fail_count": 1,
    "top_failure_types": [
      [
        "arg_type",
        1
      ],
      [
        "extraneous",
        1
      ],
      [
        "gt_mismatch",
        1
      ],
      [
        "precondition",
        1
      ],
      [
        "semantic",
        1
      ],
      [
        "service_match",
        1
      ]
    ],
    "failed_row_nos": [
      1
    ],
    "failed_cases": [
      {
        "row_no": 1,
        "command_eng": "Switch the dishwasher to dry mode.",
        "det_score": 24.0,
        "threshold": 60.0,
        "failure_reasons": [
          "arg_type",
          "extraneous",
          "gt_mismatch",
          "precondition",
          "semantic",
          "service_match"
        ],
        "output": "{\"name\":\"MockCandidate\",\"cron\":\"\",\"period\":0,\"code\":\"\"}",
        "gt": "{\"name\": \"\", \"cron\": \"\", \"period\": 0, \"script\": \"(#Dishwasher).Dishwasher_SetDishwasherMode(\\\"dry\\\")\"}",
        "source_path": "/tmp/tmp.Yvu7kjlKwC/slack/test.jsonl",
        "case_id": "test:1"
      }
    ]
  },
  "after": {
    "row_count": 1,
    "avg_det_score": 24.0,
    "avg_gt_similarity": 0.3,
    "gt_exact_count": 0,
    "pass_count": 0,
    "fail_count": 1,
    "top_failure_types": [
      [
        "arg_type",
        1
      ],
      [
        "extraneous",
        1
      ],
      [
        "gt_mismatch",
        1
      ],
      [
        "precondition",
        1
      ],
      [
        "semantic",
        1
      ],
      [
        "service_match",
        1
      ]
    ],
    "failed_row_nos": [
      1
    ],
    "failed_cases": [
      {
        "row_no": 1,
        "command_eng": "Switch the dishwasher to dry mode.",
        "det_score": 24.0,
        "threshold": 60.0,
        "failure_reasons": [
          "arg_type",
          "extraneous",
          "gt_mismatch",
          "precondition",
          "semantic",
          "service_match"
        ],
        "output": "{\"name\":\"MockCandidate\",\"cron\":\"\",\"period\":0,\"code\":\"\"}",
        "gt": "{\"name\": \"\", \"cron\": \"\", \"period\": 0, \"script\": \"(#Dishwasher).Dishwasher_SetDishwasherMode(\\\"dry\\\")\"}",
        "source_path": "/tmp/tmp.Yvu7kjlKwC/slack/test.jsonl",
        "case_id": "test:1"
      }
    ]
  }
}

