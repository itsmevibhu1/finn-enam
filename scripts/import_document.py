#!/usr/bin/env python3
"""Import a local PDF without losing its provenance or page boundaries."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit


def import_document(args):
    path = args.pdf.resolve(strict=True)
    ticker = args.ticker.upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9&_.-]{0,39}", ticker):
        raise ValueError("Ticker contains unsupported characters")
    source = urlsplit(args.source_url)
    if source.scheme not in {"https", "http"} or not source.hostname:
        raise ValueError("Source URL must be an HTTP(S) document URL")
    if source.username or source.password:
        raise ValueError("Source URL must not contain credentials")
    content = path.read_bytes()
    if not content.startswith(b"%PDF-"):
        raise ValueError("Input is not a PDF")
    digest = hashlib.sha256(content).hexdigest()
    destination = args.output.resolve() / ticker / args.kind / digest
    if destination.exists():
        existing = json.loads((destination / "manifest.json").read_text())
        if existing["period"] != args.period or existing["source_url"] != args.source_url:
            raise ValueError("Document already imported with different metadata; review the existing manifest")
        return {"status": "already_imported", "directory": str(destination), "document_id": digest}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stage the immutable bytes first: extracted text and its hash must describe the same PDF.
    with tempfile.TemporaryDirectory(prefix=".import-", dir=destination.parent) as staging:
        stage = Path(staging)
        original = stage / "original.pdf"
        original.write_bytes(content)
        extracted = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(original), "-"],
            capture_output=True, check=True, timeout=120,
        ).stdout.decode("utf-8")
        pages = extracted.split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        if not any(page.strip() for page in pages):
            raise ValueError("No extractable text; this PDF may require OCR")
        records = [{"pdf_page": i, "text": page.strip()} for i, page in enumerate(pages, 1)]
        manifest = {
            "schema_version": 1,
            "document_id": digest,
            "ticker": ticker,
            "kind": args.kind,
            "period": args.period,
            "source_url": args.source_url,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "sha256": digest,
            "pdf_page_count": len(records),
            "text_extractor": "pdftotext -layout -enc UTF-8",
            "source_verified": False,
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (stage / "pages.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stage.rename(destination)
    return {"status": "imported", "directory": str(destination), "document_id": digest, "pages": len(records)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--kind", required=True, choices=["annual_report", "transcript", "results"])
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--period", required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/documents")
    args = parser.parse_args()
    if not shutil.which("pdftotext"):
        parser.exit(1, "Install Poppler's pdftotext executable first.\n")
    try:
        print(json.dumps(import_document(args), indent=2))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
