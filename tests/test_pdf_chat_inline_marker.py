"""Regression: a PDF attached to a chat message must keep its body intact.

build_user_content stripped the "[PDF content]:" marker with
`_process_pdf(path).lstrip("\\n[PDF content]:")`. str.lstrip(chars) treats its
argument as a *set* of characters, so it kept eating leading chars that happen to
be in that set — including the 'P' of the following '[Page 1 text]:' marker (and
more, if the page prose itself starts with those chars). The shared
strip_pdf_content_marker() helper (added in #966, which fixed the other call
sites) does the correct prefix-strip; this call site was missed.

The corrupted text flows into both the inlined chat content and the auto-created
sidebar document, so the model and the user see mangled text.
"""
import os

from src import document_processor as dp


class _Handler:
    def is_image_file(self, name, mime):
        return False

    def is_audio_file(self, name, mime):
        return False

    def is_document_file(self, name, mime):
        return True

    def _inside_upload_dir(self, path):
        return True


def test_pdf_inline_body_marker_not_corrupted(monkeypatch, tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    # _process_pdf returns the real marker shape: "[PDF content]:" then the page.
    monkeypatch.setattr(
        dp, "_process_pdf",
        lambda p: "\n\n[PDF content]:\n\n[Page 1 text]:\nPolicy details follow",
    )
    # Force the plain-PDF path and give it a doc id so the body is inlined.
    # has_form_fields / create_plain_pdf_document are imported inside the
    # function from src.pdf_forms / src.pdf_form_doc, so patch them there.
    import src.pdf_forms as pforms
    import src.pdf_form_doc as pfd
    monkeypatch.setattr(pforms, "has_form_fields", lambda p: False)
    monkeypatch.setattr(pfd, "create_plain_pdf_document", lambda **kw: "docid-1")

    result = dp.build_user_content(
        "hi",
        ["fid"],
        str(tmp_path),
        _Handler(),
        session_id="s1",
        auto_opened_docs=None,
        resolved_uploads={"fid": {"path": str(pdf_path),
                                  "mime": "application/pdf", "name": "doc.pdf"}},
    )
    text = result if isinstance(result, str) else " ".join(
        i.get("text", "") for i in result if isinstance(i, dict))

    # Before the fix the lstrip ate the '[P' and the body began "age 1 text]:";
    # the correct marker is preserved intact after the fix.
    assert "[Page 1 text]:\nPolicy details follow" in text
