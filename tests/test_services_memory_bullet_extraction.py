"""Regression: services.memory bullet/numbered extraction must not crash.

routes/memory_routes.py imports `MemoryManager` from **services.memory** and
calls `extract_memory_from_chat(...)` as the fallback when the LLM
memory-suggestion call fails. The fallback parser's regex left capture group 1
as None for markdown bullet lines (`- ...`, `* ...`, `• ...`), so `.strip()`
raised `AttributeError: 'NoneType' object has no attribute 'strip'`, surfacing
as a 500.

The same bug was fixed in the separate src/memory.py copy (#873), but the
services/memory/memory.py module the live route actually uses was never patched
— and the existing tests/test_memory_bullet_extraction.py imports src.memory, so
it stayed green while the real path was broken. This test imports the live
module.
"""
from services.memory import MemoryManager


def test_extract_handles_bullet_and_numbered_lines(tmp_path):
    mgr = MemoryManager(str(tmp_path))
    out = mgr.extract_memory_from_chat([
        {"role": "assistant",
         "content": "- User likes coffee\n* Prefers tea in winter\n1. Wakes at 6am"},
    ])
    texts = [m["text"] for m in out]
    assert "User likes coffee" in texts
    assert "Prefers tea in winter" in texts
    assert "Wakes at 6am" in texts
