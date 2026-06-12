"""
Infinitum — Bulk document seeding script.

Reads all .txt files from a source directory, splits them into overlapping
chunks using the same RecursiveCharacterTextSplitter used by the live API,
and batch-uploads the records to Pinecone via integrated inference.

Usage (run from project root with venv active):
    python scripts/seed_large_data.py --docs_dir ./data/documents

    # Dry-run (chunk and report counts without uploading):
    python scripts/seed_large_data.py --docs_dir ./data/documents --dry_run

    # Custom batch size and pause between batches:
    python scripts/seed_large_data.py --docs_dir ./data/documents \
        --batch_size 50 --pause 1.0

Notes:
  - The script reads the same .env file as the API server (project root).
  - Each .txt filename becomes the "source" label on every chunk.
  - Records are idempotent: re-running with the same files will overwrite
    existing vectors (same _id = same document_id + chunk index).
"""

import argparse
import sys
import time
import uuid
from pathlib import Path

# ── Make `app.*` importable when running from the project root ────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402  (after sys.path patch)
from app.ingestion import split_document  # noqa: E402
from app.pinecone_client import (  # noqa: E402
    EMBED_TEXT_FIELD,
    PINECONE_NAMESPACE,
    index,
)

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_BATCH_SIZE = 100   # records per upsert_records() call
DEFAULT_PAUSE_SEC = 0.5    # seconds to sleep between batches (rate-limit safety)


def _build_record(document_id: str, chunk: str, chunk_idx: int, source: str) -> dict:
    return {
        "_id": f"{document_id}_chunk_{chunk_idx}",
        EMBED_TEXT_FIELD: chunk,
        "source": source,
        "chunk_index": chunk_idx,
        "document_id": document_id,
    }


def _upload_batch(records: list[dict], batch_num: int, dry_run: bool) -> int:
    """Upload one batch. Returns number of records sent (0 on dry-run)."""
    if dry_run:
        print(f"  [dry-run] batch {batch_num:>3} — would upsert {len(records)} records")
        return 0
    index.upsert_records(PINECONE_NAMESPACE, records)
    print(f"  ✓ batch {batch_num:>3} — upserted {len(records)} records")
    return len(records)


def seed(docs_dir: Path, batch_size: int, pause: float, dry_run: bool) -> None:
    txt_files = sorted(docs_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {docs_dir}. Exiting.")
        return

    print(f"\nInfinitum Seed — {len(txt_files)} file(s) found in {docs_dir}")
    print(f"  Index : {settings.PINECONE_INDEX_NAME}")
    print(f"  Batch : {batch_size} records  |  Pause: {pause}s  |  Dry-run: {dry_run}\n")

    total_chunks = 0
    total_uploaded = 0
    failed_files: list[str] = []

    pending: list[dict] = []
    batch_num = 0

    for file_path in txt_files:
        source = file_path.stem          # e.g. "employee_handbook"
        document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, str(file_path)))

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as exc:
            print(f"  ✗ Could not read {file_path.name}: {exc}")
            failed_files.append(file_path.name)
            continue

        if not content:
            print(f"  ⚠ Skipping {file_path.name} (empty file)")
            continue

        chunks = split_document(content)
        total_chunks += len(chunks)
        print(f"  → {file_path.name:<40} {len(chunks):>4} chunks")

        for i, chunk in enumerate(chunks):
            pending.append(_build_record(document_id, chunk, i, source))

            if len(pending) >= batch_size:
                batch_num += 1
                total_uploaded += _upload_batch(pending, batch_num, dry_run)
                pending.clear()
                if not dry_run and pause > 0:
                    time.sleep(pause)

    # ── Flush remaining records ───────────────────────────────────────────────
    if pending:
        batch_num += 1
        total_uploaded += _upload_batch(pending, batch_num, dry_run)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  Files processed : {len(txt_files) - len(failed_files)} / {len(txt_files)}")
    print(f"  Total chunks    : {total_chunks}")
    if dry_run:
        print("  Uploaded        : 0 (dry-run — no data sent to Pinecone)")
    else:
        print(f"  Uploaded        : {total_uploaded} records across {batch_num} batch(es)")
    if failed_files:
        print(f"  Failed files    : {', '.join(failed_files)}")
    print(f"{'─' * 50}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-seed .txt documents into Infinitum's Pinecone index."
    )
    parser.add_argument(
        "--docs_dir",
        type=Path,
        required=True,
        help="Directory containing .txt files to ingest.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Records per Pinecone upsert call (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=DEFAULT_PAUSE_SEC,
        help=f"Seconds to sleep between batches (default: {DEFAULT_PAUSE_SEC}).",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Parse and chunk files but do NOT upload to Pinecone.",
    )
    args = parser.parse_args()

    if not args.docs_dir.is_dir():
        print(f"Error: {args.docs_dir} is not a directory.")
        sys.exit(1)

    seed(
        docs_dir=args.docs_dir,
        batch_size=args.batch_size,
        pause=args.pause,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
