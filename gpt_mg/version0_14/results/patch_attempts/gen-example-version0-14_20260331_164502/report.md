# version0_14 Feedback Loop Report

- profile: version0_14
- base_genome: gen-example-version0-14
- baseline_avg_det_score: 98.898
- best_avg_det_score: 98.898
- validation_size: 1
- patch_dir: /home/andrew/joi-llm/gpt_mg/version0_14/results/patch_attempts/gen-example-version0-14_20260331_164502

## Top Failure Types
- gt_mismatch: 1

## Patch Attempts
- attempt 1: failures=gt_mismatch avg_det_score=98.898 improved=False

## Manual Focus Rules
- Keep receiver tags after # unchanged, such as #Kitchen, #LivingRoom, #DoorLock, or #MeetingRoom.
- Lowercase every service or value token after ). or all(...). so Device_Service becomes device_service in the final JOILang code.
