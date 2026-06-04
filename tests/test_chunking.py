from app.ingestion.chunking import DocumentPage, MetadataChunker, ParsedDocument


class WordCounter:
    def count(self, text: str) -> int:
        return len(text.split())


def test_chunker_preserves_metadata_and_page():
    parsed = ParsedDocument(
        filename="policy.txt",
        pages=[
            DocumentPage(
                page_number=2,
                text="A B C D E F.\n\nG H I J K L.\n\nM N O P Q R.",
                metadata={"section": "Leave policy"},
            )
        ],
        metadata={"source_type": "txt"},
        language="en",
    )
    chunker = MetadataChunker(
        chunk_size_tokens=8,
        chunk_overlap_tokens=2,
        token_counter=WordCounter(),
    )

    chunks = chunker.chunk("doc-1", parsed)

    assert len(chunks) >= 2
    assert chunks[0].document_id == "doc-1"
    assert chunks[0].page == 2
    assert chunks[0].section == "Leave policy"
    assert chunks[0].metadata["filename"] == "policy.txt"


def test_chunker_splits_large_paragraph():
    parsed = ParsedDocument(
        filename="long.txt",
        pages=[DocumentPage(page_number=1, text=" ".join(f"word{i}" for i in range(220)))],
    )
    chunker = MetadataChunker(
        chunk_size_tokens=80,
        chunk_overlap_tokens=10,
        token_counter=WordCounter(),
    )

    chunks = chunker.chunk("doc-1", parsed)

    assert len(chunks) > 1
    assert all(chunk.token_count <= 80 for chunk in chunks)
