"""Watchbird Memory — the page inside the local multipage app.

A thin wrapper. The screen itself is watchbird_memory_ui.render(), shared with the standalone
public app in streamlit_cloud/watchbird_app.py so the two cannot drift apart.

No st.set_page_config() here: app.py already sets it for the multipage app.

Like the shared module, this talks to the LIVE Render API by default, not localhost, so this page
works whether or not a local uvicorn is running.
"""

import sys
from pathlib import Path

# Under `streamlit run app.py` the repository root is already importable, because sys.path[0] is
# the main script's directory. Run this page file on its own, though, and sys.path[0] is pages/,
# so the import below fails with ModuleNotFoundError. Both ways of running it are reasonable, so
# the root goes on the path explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from watchbird_memory_ui import render  # noqa: E402  (must follow the sys.path line above)

render()
