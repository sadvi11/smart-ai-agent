"""Make the app importable in CI without credentials or a model download.

Two module-level side effects otherwise make `import app` impossible in a
clean environment:

  * memory.py and rag.py call supabase.create_client() at import time, and the
    client validates its key format — so a missing or fake key raises before
    any test runs.
  * rag.py constructs SentenceTransformer("all-MiniLM-L6-v2") at import time,
    which downloads ~90 MB on first use.

Both are stubbed here, before app is imported. That keeps the suite offline,
fast, and free — and it means these tests exercise the wiring between the API
and the agent, which is what actually broke, rather than the third-party
libraries underneath it.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Must be registered before app.py -> agent.py -> rag.py/memory.py import them.
sys.modules.setdefault("sentence_transformers", MagicMock())
sys.modules.setdefault("supabase", MagicMock())
