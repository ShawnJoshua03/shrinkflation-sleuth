"""Cloud Run entrypoint — serves the ADK agent (with dev UI) via FastAPI.

    uvicorn main:app --host 0.0.0.0 --port 8080
"""
import os

from google.adk.cli.fast_api import get_fast_api_app

AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents")

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=True,            # serve the built-in ADK chat UI at /
    allow_origins=["*"],
)
