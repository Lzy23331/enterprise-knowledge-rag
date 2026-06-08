# SmartOfficeRAG Deployment Guide

## Recommended: Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Open https://share.streamlit.io/ and choose **New app**.
3. Select the GitHub repository and branch.
4. Set the main file path to:

```text
app.py
```

Do not use `run_web_demo.py` as the cloud entrypoint. It is only a local convenience launcher.

5. Optional: add secrets in **Advanced settings**:

```toml
DEEPSEEK_API_KEY = "your_deepseek_key"
```

Do not commit API keys to GitHub. If no key is configured, the app still works with the local extractive fallback.

## Local Production-like Run

```powershell
cd D:\projects\enterprise-knowledge-rag
.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements.txt
.\.venv\Scripts\python.exe run_web_demo.py
```

Open:

```text
http://localhost:8501
```

## Deployment Notes

- `app.py` is the public entrypoint.
- `requirements.txt` installs Streamlit, optional FAISS, BM25, sentence-transformers, NumPy, and the OpenAI-compatible client package.
- `runtime.txt` pins Python 3.12 for managed hosting.
- The app defaults to vector retrieval and uses FAISS when the package is available; otherwise it falls back to NumPy similarity search.
- `BAAI/bge-small-zh-v1.5` is downloaded on first startup if not already cached. If the model is unavailable, the app falls back to local hashing vectors so the public demo can still run.
- `eval_report.json` is committed so the public demo can show evaluation metrics immediately.
- `.venv/`, `.cache/`, `.env/`, and `vector_index/` are intentionally ignored.
