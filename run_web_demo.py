import os
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    os.environ.setdefault("SMARTOFFICE_USE_VECTOR", "1")
    os.environ.setdefault("HF_HOME", str(project_root / ".cache" / "huggingface"))

    from streamlit.web import cli as streamlit_cli

    sys.argv = [
        "streamlit",
        "run",
        "app.py",
        "--server.headless",
        "true",
        *sys.argv[1:],
    ]
    streamlit_cli.main()


if __name__ == "__main__":
    main()
