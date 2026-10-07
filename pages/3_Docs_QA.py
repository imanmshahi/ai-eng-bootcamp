"""Docs Q&A — ingest documents and ask grounded questions via the RAG API."""

import requests
import streamlit as st

from api_client import API_BASE, server_is_up

st.title("Docs Q&A")
st.caption("Ingest documents, then ask questions grounded in your own text.")

if server_is_up():
    st.success("Connected to your API")
else:
    st.warning("Your API is not running. Start it in a separate terminal, then refresh this page.")

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. **Ingest** a document — it gets chunked, embedded, and stored.\n"
        "2. **Ask** a question — the API retrieves the best chunks, "
        "feeds them to the LLM, and cites what it used.\n\n"
        "Re-ingesting the same `document_id` replaces the old version."
    )

# ── Ingest section ────────────────────────────────────────────────────
st.header("Ingest a document")

document_id = st.text_input("Document ID", placeholder="POL-114")
text = st.text_area("Document text", height=180, placeholder="Paste your document here…")

if st.button("Ingest", type="primary", use_container_width=True):
    if not document_id.strip():
        st.warning("Enter a document ID first.")
    elif not text.strip():
        st.warning("Enter some text to ingest.")
    elif not server_is_up():
        st.error("Start the API server first, then try again.")
    else:
        try:
            response = requests.post(
                f"{API_BASE}/ingest",
                json={"document_id": document_id.strip(), "text": text.strip()},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            col1, col2, col3 = st.columns(3)
            col1.metric("Chunks added", data["chunks_added"])
            col2.metric("Chunks replaced", data["chunks_replaced"])
            col3.metric("Total chunks", data["total_chunks"])
            st.caption(f"Tokens used: {data['tokens_used']}  ·  Cost: ${data['cost_usd']:.6f}")
        except requests.ConnectionError:
            st.error("Lost connection to the API. Check that the server is still running.")
        except requests.HTTPError:
            detail = response.json().get("detail", response.text)
            st.error(f"API error ({response.status_code}): {detail}")

# ── Ask section ───────────────────────────────────────────────────────
st.divider()
st.header("Ask a question")

question = st.text_input("Your question", placeholder="Who approves remote days?")

if st.button("Ask", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("Enter a question first.")
    elif not server_is_up():
        st.error("Start the API server first, then try again.")
    else:
        try:
            response = requests.post(
                f"{API_BASE}/ask",
                json={"question": question.strip()},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("refused"):
                st.error("🚫 Refused — the answer is not in the ingested documents.")

            st.subheader("Answer")
            st.write(data["answer"])

            if data.get("citations"):
                st.markdown("**Citations:**")
                for cid in data["citations"]:
                    st.markdown(f"- `{cid}`")

            st.caption(
                f"Tokens used: {data['tokens_used']}  ·  "
                f"Cost: ${data['cost_usd']:.6f}  ·  "
                f"Confidence: {data['confidence']}"
            )
        except requests.ConnectionError:
            st.error("Lost connection to the API. Check that the server is still running.")
        except requests.HTTPError:
            detail = response.json().get("detail", response.text)
            st.error(f"API error ({response.status_code}): {detail}")
