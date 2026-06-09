# SmartOfficeRAG Deployment Guide

## Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open Streamlit Community Cloud and create a new app.
3. Select the repository and branch.
4. Set the main file path to:

```text
app.py
```

5. Optional: configure an LLM key in **Advanced settings / Secrets**:

```toml
DEEPSEEK_API_KEY = "your_deepseek_key"
```

Do not commit API keys. If no key is configured, the app uses the local extractive fallback and still shows retrieval, citations, scores, refusal state, and evaluation metrics.

## Dependency Profiles

- `requirements.txt`: lightweight public Demo dependencies for Streamlit Cloud. It uses local hashing vectors and NumPy similarity when full embedding packages are unavailable.
- `requirements-full.txt`: local full RAG experience with `sentence-transformers`, `BAAI/bge-small-zh-v1.5`, and FAISS.

Install lightweight dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements.txt
```

Install full local dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements-full.txt
```

## Local Production-like Run

```powershell
cd D:\projects\enterprise-knowledge-rag
$env:SMARTOFFICE_USE_VECTOR="1"
$env:HF_HOME="D:\projects\enterprise-knowledge-rag\.cache\huggingface"
.\.venv\Scripts\python.exe run_web_demo.py
```

Open:

```text
http://localhost:8501
```

## Evaluation Run

Offline evaluation disables LLM calls by default through `SMARTOFFICE_DISABLE_LLM=1` in `evaluate.py`, so metrics are reproducible and do not depend on network latency or API spend.

```powershell
.\.venv\Scripts\python.exe evaluate.py
```

Outputs:

- `eval_report.json`
- `eval_report.md`

## Experiment Run

Use the experiment runner when you need the resume story and real iteration curve across chunking, embedding, retrieval, RRF, and refusal strategies.

```powershell
.\.venv\Scripts\python.exe run_experiments.py --quick
.\.venv\Scripts\python.exe run_experiments.py --full
```

`--full` is strict by default: embedding configs must complete successfully, otherwise the run fails. Use offline mode only to reproduce with an existing cache:

```powershell
.\.venv\Scripts\python.exe run_experiments.py --full --offline --allow-skip
```

Outputs:

- `docs/EXPERIMENT_REPORT.md`
- `experiments/results/experiment_report.json`
- `experiments/results/experiment_report.csv`

## Deployment Notes

- `app.py` is the public entrypoint and calls `smart_office_rag.pipeline.EnterpriseKnowledgeRAG`.
- The app shows the full RAG path: metadata filter, vector retrieval, BM25, RRF, primary-document expansion, confidence gate, answer generation, citations, scores, and latency.
- `runtime.txt` pins Python 3.12 for managed hosting.
- `eval_report.json` is committed so the public Demo can show metrics immediately.
- `.venv/`, `.cache/`, `.env/`, and `vector_index/` are intentionally ignored.
