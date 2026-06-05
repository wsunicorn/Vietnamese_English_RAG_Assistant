from app.api.schemas import ChatResponse


def parse_ask_command(text: str, *, command: str = "/ask") -> str:
    value = (text or "").strip()
    if value.lower().startswith(command):
        value = value[len(command) :].strip()
    return value


def compact_citations(answer: ChatResponse, *, limit: int = 3) -> str:
    lines = []
    for citation in answer.citations[:limit]:
        label = citation.source_url or citation.source_path or citation.filename
        lines.append(f"[{citation.citation_id}] {label}")
    return "\n".join(lines)


def format_chat_response(answer: ChatResponse) -> str:
    citations = compact_citations(answer)
    if citations:
        return f"{answer.answer}\n\nSources:\n{citations}"
    return answer.answer
