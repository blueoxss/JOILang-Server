# version0_14 Feedback Loop Report

- profile: version0_15
- base_genome: gen-0d925104-a481-fa79-3ebe-d866f61d584c
- baseline_avg_det_score: 24.0
- best_avg_det_score: 24.0
- validation_size: 1
- patch_dir: /home/andrew/joi-llm/gpt_mg/version0_15/results/patch_attempts/gen-0d925104-a481-fa79-3ebe-d866f61d584c_20260413_203559

## Top Failure Types
- arg_type: 1
- extraneous: 1
- gt_mismatch: 1
- precondition: 1
- semantic: 1
- service_match: 1

## Patch Attempts
- attempt 1: failures=arg_type avg_det_score=24.0 improved=False
- attempt 2: failures=arg_type,extraneous avg_det_score=24.0 improved=False

## Manual Focus Rules
- Keep receiver tags after # unchanged, such as #Kitchen, #LivingRoom, #DoorLock, or #MeetingRoom.
- Lowercase every service or value token after ). or all(...). so Device_Service becomes device_service in the final JOILang code.
- Handle concise English natural-language commands directly and preserve the requested action ordering, tags, and timing semantics.
- If an admin feedback case has a known correct pattern, prefer the smallest schema-valid program that matches that known target behavior exactly.
