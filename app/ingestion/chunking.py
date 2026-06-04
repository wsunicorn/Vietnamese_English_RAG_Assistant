from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class DocumentPage:
    page_number: int | None
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    filename: str
    pages: list[DocumentPage]
    metadata: dict = field(default_factory=dict)
    language: str | None = None


@dataclass(slots=True)
class DocumentChunk:
    id: str
    document_id: str
    point_id: str
    text: str
    page: int | None
    section: str | None
    token_count: int
    metadata: dict


class TokenCounter:
    def __init__(self, model_name: str = "text-embedding-3-large"):
        self._encoding = None
        try:
            import tiktoken

            self._encoding = tiktoken.encoding_for_model(model_name)
        except Exception:
            self._encoding = None

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        return max(1, int(len(text.split()) * 1.35))


class MetadataChunker:
    def __init__(
        self,
        *,
        chunk_size_tokens: int,
        chunk_overlap_tokens: int,
        token_counter: TokenCounter | None = None,
    ):
        if chunk_overlap_tokens >= chunk_size_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_size_tokens")
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        self.token_counter = token_counter or TokenCounter()

    def chunk(self, document_id: str, parsed: ParsedDocument) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for page in parsed.pages:
            for text in self._split_text(page.text):
                clean = normalize_whitespace(text)
                if not clean:
                    continue
                chunks.append(
                    DocumentChunk(
                        id=str(uuid4()),
                        document_id=document_id,
                        point_id=str(uuid4()),
                        text=clean,
                        page=page.page_number,
                        section=page.metadata.get("section"),
                        token_count=self.token_counter.count(clean),
                        metadata={
                            **parsed.metadata,
                            **page.metadata,
                            "page": page.page_number,
                            "filename": parsed.filename,
                        },
                    )
                )
        return chunks

    def _split_text(self, text: str) -> list[str]:
        paragraphs = [normalize_whitespace(part) for part in text.split("\n\n")]
        paragraphs = [part for part in paragraphs if part]
        if not paragraphs:
            return []

        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = self.token_counter.count(paragraph)
            if paragraph_tokens > self.chunk_size_tokens:
                if current:
                    chunks.append("\n\n".join(current))
                    current, current_tokens = [], 0
                chunks.extend(self._split_large_paragraph(paragraph))
                continue

            if current and current_tokens + paragraph_tokens > self.chunk_size_tokens:
                chunks.append("\n\n".join(current))
                overlap = self._tail_overlap(current)
                current = overlap
                current_tokens = self.token_counter.count("\n\n".join(current))

            current.append(paragraph)
            current_tokens += paragraph_tokens

        if current:
            chunks.append("\n\n".join(current))
        return chunks

    def _split_large_paragraph(self, paragraph: str) -> list[str]:
        words = paragraph.split()
        max_words = max(80, int(self.chunk_size_tokens * 0.75))
        overlap_words = min(max_words // 2, max(0, int(self.chunk_overlap_tokens * 0.75)))
        step = max(1, max_words - overlap_words)
        chunks = []
        for start in range(0, len(words), step):
            piece = " ".join(words[start : start + max_words])
            if piece:
                chunks.append(piece)
            if start + max_words >= len(words):
                break
        return chunks

    def _tail_overlap(self, paragraphs: list[str]) -> list[str]:
        if self.chunk_overlap_tokens <= 0:
            return []
        selected: list[str] = []
        tokens = 0
        for paragraph in reversed(paragraphs):
            paragraph_tokens = self.token_counter.count(paragraph)
            if selected and tokens + paragraph_tokens > self.chunk_overlap_tokens:
                break
            selected.insert(0, paragraph)
            tokens += paragraph_tokens
        return selected


def normalize_whitespace(text: str) -> str:
    lines = [" ".join(line.strip().split()) for line in text.splitlines()]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines).strip()
