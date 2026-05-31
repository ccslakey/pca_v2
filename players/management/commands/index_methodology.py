"""
Chunk, embed, and store the methodology docs for semantic retrieval.

    python manage.py index_methodology

Reads frontend/src/methodology/*.md, splits each into ~120-word chunks on
paragraph boundaries, embeds them with Voyage, and upserts into
MethodologyChunk. Re-running is safe — each doc's chunks are replaced wholesale.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from players import embeddings
from players.models import MethodologyChunk

_TARGET_WORDS = 120  # approximate chunk size; docs are short so a few chunks each


def _title_of(text: str, slug: str) -> str:
    """First markdown H1, else a title-cased slug."""
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else slug.replace("-", " ").title()


def _chunk(text: str) -> list[str]:
    """Group paragraphs into ~_TARGET_WORDS windows, keeping paragraphs intact."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    words = 0
    for para in paras:
        n = len(para.split())
        if buf and words + n > _TARGET_WORDS:
            chunks.append("\n\n".join(buf))
            buf, words = [], 0
        buf.append(para)
        words += n
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


class Command(BaseCommand):
    help = "Embed and index the methodology docs for semantic retrieval."

    def handle(self, *args, **options):
        if not getattr(settings, "RAG_ENABLED", False):
            raise CommandError("VOYAGE_API_KEY is not set — cannot embed. Set it and retry.")

        doc_dir = Path(settings.BASE_DIR) / "frontend" / "src" / "methodology"
        md_files = sorted(doc_dir.glob("*.md"))
        if not md_files:
            raise CommandError(f"No .md files found in {doc_dir}")

        total = 0
        for path in md_files:
            slug = path.stem
            text = path.read_text(encoding="utf-8")
            title = _title_of(text, slug)
            chunks = _chunk(text)
            vectors = embeddings.embed(chunks, input_type="document")

            with transaction.atomic():
                MethodologyChunk.objects.filter(slug=slug).delete()
                MethodologyChunk.objects.bulk_create(
                    [
                        MethodologyChunk(
                            slug=slug, title=title, chunk_index=i, content=chunk, embedding=vec
                        )
                        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
                    ]
                )
            total += len(chunks)
            self.stdout.write(f"  {slug}: {len(chunks)} chunks")

        self.stdout.write(self.style.SUCCESS(f"Indexed {total} chunks from {len(md_files)} docs."))
