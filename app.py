"""Home — pick an app from the sidebar."""

import streamlit as st

st.set_page_config(page_title="AI Eng Bootcamp", page_icon="🏠", layout="centered")

st.title("AI Eng Bootcamp")
st.markdown(
    """
Welcome. Use the **sidebar on the left** to switch apps:

1. **Cost Estimator** — *course demo* of model cost math (`POST /estimate`)
2. **Bootcamp Q&A** — ask questions (`POST /ask`)

Start the API:
"""
)
st.code("./start.sh", language="bash")

st.info("Sidebar: **Cost Estimator** (demo) or **Bootcamp Q&A**. Full product → ai-build-crew.")
