"""Extract source material and cache it until a document changes."""
from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from pypdf import PdfReader
from pptx import Presentation

from config import CACHE_DIR, CACHE_FILE, CACHE_MANIFEST, DOCS_DIR

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx")


def _source_files() -> list[Path]:
    if not DOCS_DIR.exists():
        return []
    return sorted(
        (path for path in DOCS_DIR.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=lambda path: path.name.lower(),
    )


def _manifest(files: list[Path]) -> dict[str, int]:
    return {path.name: path.stat().st_mtime_ns for path in files}


def _read_pdf(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def _read_docx(path: Path) -> str:
    document = Document(str(path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    table_cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return "\n".join(paragraphs + table_cells)


def _read_pptx(path: Path) -> str:
    presentation = Presentation(str(path))
    parts: list[str] = []
    for slide in presentation.slides:
        parts.extend(shape.text for shape in slide.shapes if hasattr(shape, "text") and shape.text)
        # python-pptx exposes notes when the underlying presentation contains them.
        try:
            notes = slide.notes_slide
            parts.extend(shape.text for shape in notes.shapes if hasattr(shape, "text") and shape.text)
        except (AttributeError, KeyError):
            pass
    return "\n".join(parts)


def _extract(path: Path) -> str:
    readers = {".pdf": _read_pdf, ".docx": _read_docx, ".pptx": _read_pptx}
    return readers[path.suffix.lower()](path)


def load_combined_text() -> str:
    """Return cached document text, refreshing the cache when sources changed."""
    files = _source_files()
    if not files:
        raise FileNotFoundError(
            f"No PDF, DOCX, or PPTX files found in {DOCS_DIR}. Add source materials and try again."
        )

    current_manifest = _manifest(files)
    if CACHE_FILE.exists() and CACHE_MANIFEST.exists():
        try:
            if json.loads(CACHE_MANIFEST.read_text(encoding="utf-8")) == current_manifest:
                return CACHE_FILE.read_text(encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass

    chunks = []
    for path in files:
        extracted = _extract(path).strip()
        if extracted:
            chunks.append(f"\n\n===== Source: {path.name} =====\n{extracted}")
    combined = "".join(chunks).strip()
    if not combined:
        raise ValueError("The source documents did not contain extractable text.")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(combined, encoding="utf-8")
    CACHE_MANIFEST.write_text(json.dumps(current_manifest, indent=2), encoding="utf-8")
    return combined
