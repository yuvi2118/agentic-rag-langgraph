"""Routes a file path to the right loader based on its extension."""

from pathlib import Path

from app.ingestion.loaders import load_docx, load_html, load_pdf, load_pptx, load_txt

_LOADERS = {
    "pdf": load_pdf,
    "html": load_html,
    "htm": load_html,
    "docx": load_docx,
    "pptx": load_pptx,
    "txt": load_txt,
}


def load_document(path: Path) -> tuple[str, dict]:
    ext = path.suffix.lstrip(".").lower()
    loader = _LOADERS.get(ext)
    if loader is None:
        raise ValueError(f"No loader registered for file type '.{ext}' ({path.name})")
    return loader(path)
