SYSTEM_PROMPT = """You are a bilingual Vietnamese/English document QA assistant.

Answer only from the provided context. If the context does not contain enough evidence, say that the answer is not available in the uploaded documents.

Rules:
- Preserve the user's language when possible.
- Use concise, professional language.
- Format the answer in Markdown when structure helps: short headings, bullet lists, tables, or code blocks.
- Include citation markers like [C1], [C2] for claims grounded in the context.
- Do not invent facts, page numbers, filenames, or citations.
"""


def build_context(chunks: list[dict]) -> str:
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        page = chunk.get("page") or "unknown"
        filename = chunk.get("filename") or "unknown file"
        blocks.append(
            f"[C{index}] filename={filename}; page={page}; score={chunk.get('score', 0):.4f}\n"
            f"{chunk.get('text', '')}"
        )
    return "\n\n---\n\n".join(blocks)


def build_user_prompt(question: str, context: str) -> str:
    return f"""Question:
{question}

Context:
{context}

Return JSON with:
- answer: string, formatted as Markdown when useful
- no_answer: boolean
- confidence: number from 0 to 1
- used_citations: array of citation ids like ["C1"]
"""
