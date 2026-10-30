"""Standalone Watchbird Memory app — the entry point for Streamlit Community Cloud.

Why this file is in its own directory rather than at the repository root
-----------------------------------------------------------------------
Streamlit builds its sidebar navigation from a `pages/` directory sitting next to the entry
point. The repository root has one, holding six pages that talk to a LOCAL API on 127.0.0.1. An
entry point at the root would therefore publish those six pages too, and every one of them would
be broken for the public, because there is no local API next to a Streamlit Cloud container.

This directory has no `pages/` subdirectory, so the deployed app is exactly one screen.

Deploy settings on Community Cloud
---------------------------------
    Main file path:  streamlit_cloud/watchbird_app.py
    Dependencies:    streamlit_cloud/requirements.txt  (a dependency file beside the entry point
                     takes precedence over the one at the repository root, which is what keeps
                     fastapi, uvicorn, openai and tiktoken out of this build)
    Secrets:         none. The app makes unauthenticated HTTPS calls to a public API.

The theme stays in the root `.streamlit/config.toml`: Community Cloud requires the config file to
remain at the repository root when the entry point is in a subdirectory.
"""

import sys
from pathlib import Path

# watchbird_memory_ui lives at the repository root, and Python puts only THIS file's directory on
# sys.path. Community Cloud sets the working directory to the repository root, but the working
# directory is not importable, so the root goes on the path explicitly rather than by luck.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402  (must follow the sys.path line above)

from watchbird_memory_ui import render  # noqa: E402

# Safe here, unlike in the multipage page: this file IS the app, so it owns the page config.
st.set_page_config(page_title="Watchbird Memory", page_icon="🔔", layout="centered")

render()
