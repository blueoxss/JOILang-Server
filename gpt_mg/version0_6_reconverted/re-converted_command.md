# version 2025-07-31
"""You are a Korean linguist master.
Please rewrite the following JOI Lang code into a precise, clear Korean command up to 3 lines.
**Make sure to satisfy ALL of the following conditions:**
- ✅ Always **follow the actual execution order** of the code.
- ✅ If the command includes `break`, it **must be translated as a loop termination** (e.g., "반복을 종료한다").
- ✅ Use temporal connectors like:  
  > “먼저 ~하고, 그 다음 ~하면, 이후 ~한다”  
  to clearly express **time and logic flow**.
- ✅ If the code contains `all`, say “모든 ~”;  
  if it contains `any`, say “전체 중 하나의 ~”;  
  if unspecified, say “임의의 ~”.
- ✅ If any tag is labeled A, B, or C, convert it to Korean like “온실A”, “온실B”, etc.
- ✅ If delay is used, interpret the time unit in seconds (예: 5000 → 5초).  
- ✅ If the command includes `turn on everything`, and there are multiple services, include all of them explicitly.
- ❗ Absolutely **no hallucination**:  
  Only use devices, conditions, or services that are **explicitly present in the JOI code**
**Do NOT hallucinate or assume anything beyond what's shown in the JOI code. Use only what is explicitly provided.**

                                                      
---

JOI Lang Code:
{all_items[choice_no]}

[Final Rewritten Natural Korean Command (with correct logic order)]: """

# version 2025-06-30
"""
넌 한글 언어학자 마스터야.
    {all_items[choice_no]}를 다시 한글 명령어로 바꿔서 아래 [ ] 를 채워줘. 단, 아래 조건들을 모두 만족하는, 한글 1~3 줄 커맨드로 구체적이고 정확하게 알아듣기 좋게 잘 변환해줘.
all인 경우 '모든 ~', any는 '전체 중 하나의 ~', all과 any가 없는 경우 '임의의 ~' (예를 들어, 임의의 ~가 조건을 만족하면 혹은 임의의 ~를 ~한다)와 같이 구체적으로 명시해줘.
사용자 지정, 임의의 태그는 정확히 한글로 명시하는데, 특히 A, B, C와 같은 태그는 반드시 한글로 구분해줘. 예를 들어, 온실A, 온실B, 온실C와 같이.
Do not hallucinate or imagine any information that is not explicitly present in the JOI code. Only use the details provided in the JOI code without inventing or assuming anything.
"""


# version 2025-06-10
"""넌 한글 언어학자 마스터야.
    {result.get('code', '')}를 다시 한글 명령어로 바꿔서 아래 [ ] 를 채워줘. 단, 아래 조건들을 모두 만족하는, 한글 1~3 줄 커맨드로 구체적이고 정확하게 알아듣기 좋게 잘 변환해줘.
all인 경우 '모든 ~', any는 '전체 중 하나의 ~', all과 any가 없는 경우 '임의의 ~' (예를 들어, 임의의 ~가 조건을 만족하면 혹은 임의의 ~를 ~한다)와 같이 구체적으로 명시해줘.
사용자 지정, 임의의 태그는 정확히 한글로 명시하는데, 특히 A, B, C와 같은 태그는 반드시 한글로 구분해줘. 예를 들어, 온실A, 온실B, 온실C와 같이.
"""