"""Cloud Run entrypoint: the ADK FastAPI app, with the ADK chat UI at /."""

import os

from google.adk.cli.fast_api import get_fast_api_app

AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents")

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=True,
    allow_origins=["*"],
)
