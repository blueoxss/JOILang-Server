*Latest Updates* 🔥
- [2025/06/20] CoD Prompting Method (Cloud)
- [2025/06/26] Static Analyzer

---
## About

### Refined Inference Architecture: Three-Stage Reasoning
Our inference process is designed in two distinct stages to optimize device mapping and code generation.
### Stage 1: Device Mapping & Contextualization
This initial stage focuses on device mapping, where we leverage a GPT model to interpret and align user requests with available devices. We plan to integrate an embedding model in the future to enhance the accuracy and efficiency of this mapping.
### Stage 2: Joi Code Generation with Chain-of-Draft Reasoning
In the second stage, we utilize the device information derived from Stage 1, combined with the main prompt, to generate Joi code. This stage employs a sophisticated [Chain-of-Draft](https://arxiv.org/pdf/2502.18600) reasoning approach, characterized by the following steps:
Step-by-Step Command Analysis: The Large Language Model (LLM) meticulously analyzes the chunked commands in a step-by-step fashion.
Code Generation Plan Formulation: Based on the analysis, the LLM devises a comprehensive code generation plan.
Draft-based Reasoning: Crucially, during this process, the LLM actively performs on-the-fly reasoning by generating its own short, draft-format summary notes. This allows for a more iterative and robust inference.
Final Output Parsing: Ultimately, only the generated Joi code is parsed and returned as the final output, ensuring a clean and executable result.
### Stage 3: Error Correction with Static Analyzer
We use a static analyzer to detect syntax errors and service/device mapping errors in generated code. When issues are found, the system provides natural language feedback and automatically re-invokes Stage 2 to improve the code through iterative reasoning.
## Getting Started

<details>
<summary>Required Files</summary>

- service_list_ver1.5.3.json
- current_device_list.txt
- other_params.txt

</details>

```bash
### Local ###
cd llm/gpt_cap
pip install -r requirements.txt
python main.py
```
To check the drafts, comment out function "extract_code_block()" in run.py.
