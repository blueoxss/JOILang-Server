#!/usr/bin/env python3
"""WI-09: the renderer must reflect the B/O/V/E genotype axes in the emitted
prompt (not only R), while never dropping core blocks. GPU-free / deterministic.

Note: full end-to-end validation (does closing WI-09 raise DETPass?) needs a
local Qwen GA run and is out of scope for this unit test; these tests verify the
renderer contract only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GA = os.path.abspath(os.path.join(HERE, "..", "utils", "ga_search"))
if GA not in sys.path:
    sys.path.insert(0, GA)

from prompt_patch_apply import rendered_prompt_with_genome  # noqa: E402

SYS = """You are a JOILang programmer. Convert natural language into JOILang.
Only use allowed keywords: if, wait until. Never use while.

[Device and Service Mapping]
Extract all device tags. Use canonical service names.
[service_list_value]
[{'device':'Light','service':'switch_switch'}]
[service_list_function]
[{'device':'AirConditioner','service':'switch_on'}]

---
[Grammar]
cron is a UNIX cron string. period is in milliseconds.

---
[Condition Combination Rules]
Use wait until for transition events.

---
[Important Cautions]
Never invent services that are not listed.

---
[Examples]
- turn on the light -> (#Light).switch_on()

--- JOILang Code Output Format Guide ---
Return one JSON object with name, cron, period, code.
"""

CORE_MARKERS = ["[service_list_value]", "[Grammar]", "Output Format Guide",
                "You are a JOILang programmer"]


def pkg():
    return {"system_prompt": SYS, "user_prompt": "Generate: turn on the light",
            "prompt_text": SYS + "\n\nGenerate: turn on the light"}


def g(blocks=None, block_params=None, params=None):
    return {"id": "t",
            "blocks": blocks if blocks is not None else ["01", "02", "03", "05", "06"],
            "block_params": block_params or {}, "params": params or {}}


def _core_ok(text):
    return all(m in text for m in CORE_MARKERS)


def test_core_preserved_and_user_last():
    out = rendered_prompt_with_genome(pkg(), g())
    assert _core_ok(out), "core blocks must survive assembly"
    assert out.strip().endswith("turn on the light"), "user prompt must be last"


def test_determinism():
    p, gen = pkg(), g()
    assert rendered_prompt_with_genome(p, gen) == rendered_prompt_with_genome(p, gen)


def test_O_reorder_changes_prompt_keeps_core():
    a = rendered_prompt_with_genome(pkg(), g(blocks=["01", "02", "03", "05", "06"]))
    b = rendered_prompt_with_genome(pkg(), g(blocks=["02", "01", "05", "03", "06"]))
    assert a != b, "block order (O) must change the emitted prompt"
    assert _core_ok(a) and _core_ok(b)


def test_B_toggle_drops_optional_only():
    full = rendered_prompt_with_genome(pkg(), g(blocks=["01", "02", "03", "05", "06"]))
    no06 = rendered_prompt_with_genome(pkg(), g(blocks=["01", "02", "03", "05"]))
    assert full != no06, "toggling block 06 (B) must change the prompt"
    assert "(#Light).switch_on()" in full, "examples present when 06 active"
    assert "(#Light).switch_on()" not in no06, "examples dropped when 06 inactive"
    assert _core_ok(no06), "core blocks must remain even with 06 off"


def test_V_version_directive_visible():
    base = rendered_prompt_with_genome(pkg(), g())
    v = rendered_prompt_with_genome(pkg(), g(block_params={"03": {"version": "v2"}}))
    assert "[GA:03:style=v2]" in v and base != v, "version (V) must render"


def test_E_few_shot_directive_visible():
    base = rendered_prompt_with_genome(pkg(), g())
    e = rendered_prompt_with_genome(pkg(), g(params={"few_shot_count": 1}))
    assert "few_shot<=1" in e and base != e, "few-shot (E) must render"


def test_R_micro_rules_surfaced():
    out = rendered_prompt_with_genome(pkg(), g(block_params={"05": {"micro_rules": ["Rule X about time."]}}))
    assert "Rule X about time." in out, "micro_rules (R) must render"


def test_legacy_fallback_when_not_decomposable():
    out = rendered_prompt_with_genome({"prompt_text": "tiny base"},
                                      g(block_params={"06": {"micro_rules": ["only rule"]}}))
    assert "only rule" in out and "GA Prompt Patch Overlay" in out


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print(f"\nALL {len(fns)} TESTS PASSED")
