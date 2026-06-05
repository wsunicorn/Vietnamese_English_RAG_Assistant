from pathlib import Path

from app.core.config import Settings
from app.ingestion.chunking import DocumentChunk, MetadataChunker, ParsedDocument, TokenCounter
from app.ingestion.parsers import DocumentParser


class IngestionPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.parser = DocumentParser()
        self.chunker = MetadataChunker(
            chunk_size_tokens=settings.chunk_size_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
            token_counter=TokenCounter(settings.tokenizer_model),
        )

    def parse_and_chunk(
        self,
        path: Path,
        *,
        document_id: str,
        filename: str,
        content_type: str,
    ) -> tuple[ParsedDocument, list[DocumentChunk]]:
        parsed = self.parser.parse(path, filename=filename, content_type=content_type)
        chunks = self.chunker.chunk(document_id=document_id, parsed=parsed)
        return parsed, chunks

    def parse_many(
        self,
        path: Path,
        *,
        filename: str,
        content_type: str,
    ) -> list[ParsedDocument]:
        return self.parser.parse_many(path, filename=filename, content_type=content_type)

    def chunk_parsed(
        self,
        *,
        document_id: str,
        parsed: ParsedDocument,
    ) -> list[DocumentChunk]:
        return self.chunker.chunk(document_id=document_id, parsed=parsed)
