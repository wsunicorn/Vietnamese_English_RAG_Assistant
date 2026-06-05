from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from urllib.parse import urldefrag, urlparse
from xml.etree import ElementTree

import httpx

from app.core.config import Settings
from app.ingestion.chunking import DocumentPage, ParsedDocument, normalize_whitespace
from app.ingestion.parsers import detect_language, html_to_text, repair_mojibake


@dataclass(slots=True)
class WebPage:
    url: str
    title: str
    text: str
    content_type: str


async def fetch_web_documents(
    *,
    url: str,
    mode: str,
    max_pages: int,
    settings: Settings,
) -> list[ParsedDocument]:
    if mode == "sitemap":
        urls = await fetch_sitemap_urls(url, max_pages=max_pages, settings=settings)
        pages = [await fetch_page(page_url, settings=settings) for page_url in urls]
    else:
        pages = [await fetch_page(url, settings=settings)]

    documents = [page_to_parsed_document(page, source_type=mode) for page in pages if page.text.strip()]
    if not documents:
        raise ValueError("No readable text was found at the requested URL.")
    return documents


async def fetch_sitemap_urls(url: str, *, max_pages: int, settings: Settings) -> list[str]:
    response = await http_get(url, settings=settings)
    try:
        root = ElementTree.fromstring(decode_response_text(response))
    except ElementTree.ParseError as exc:
        raise ValueError(f"Sitemap XML could not be parsed: {exc}") from exc

    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"

    requested_domain = urlparse(url).netloc
    urls: list[str] = []
    if root.tag.endswith("sitemapindex"):
        sitemap_locs = [loc.text or "" for loc in root.findall(f".//{namespace}sitemap/{namespace}loc")]
        for sitemap_url in sitemap_locs[:max_pages]:
            nested = await fetch_sitemap_urls(
                sitemap_url.strip(),
                max_pages=max_pages - len(urls),
                settings=settings,
            )
            urls.extend(nested)
            if len(urls) >= max_pages:
                break
    else:
        for loc in root.findall(f".//{namespace}url/{namespace}loc"):
            candidate = normalize_url(loc.text or "")
            if not candidate:
                continue
            if requested_domain and urlparse(candidate).netloc != requested_domain:
                continue
            urls.append(candidate)
            if len(urls) >= max_pages:
                break

    return urls[:max_pages]


async def fetch_page(url: str, *, settings: Settings) -> WebPage:
    response = await http_get(url, settings=settings)
    content_type = response.headers.get("content-type", "text/html").split(";")[0].strip()
    body = decode_response_text(response)
    if "html" in content_type:
        title, text = html_page_to_text(body)
    elif content_type.startswith("text/"):
        title = urlparse(str(response.url)).path.rsplit("/", 1)[-1] or str(response.url)
        text = body
    else:
        raise ValueError(f"Unsupported URL content type: {content_type}")
    return WebPage(
        url=normalize_url(str(response.url)) or url,
        title=repair_mojibake(title or url),
        text=repair_mojibake(normalize_whitespace(unescape(text))),
        content_type=content_type,
    )


async def http_get(url: str, *, settings: Settings) -> httpx.Response:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Upgrade-Insecure-Requests": "1"
    }
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=settings.web_ingest_timeout_seconds,
        headers=headers,
    ) as client:
        response = await client.get(url)
    response.raise_for_status()
    return response


def html_page_to_text(html: str) -> tuple[str, str]:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for node in soup(["script", "style", "noscript", "svg", "canvas"]):
            node.decompose()
        title = normalize_whitespace(soup.title.get_text(" ")) if soup.title else ""
        text = soup.get_text("\n")
        return title, text
    except Exception:
        return "", html_to_text(html)


def decode_response_text(response: httpx.Response) -> str:
    content = getattr(response, "content", None)
    if content is None:
        return repair_mojibake(getattr(response, "text", ""))

    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded = response.text
    return repair_mojibake(decoded)


def page_to_parsed_document(page: WebPage, *, source_type: str) -> ParsedDocument:
    title = page.title[:255] or page.url
    return ParsedDocument(
        filename=title,
        pages=[
            DocumentPage(
                page_number=None,
                text=page.text,
                metadata={
                    "parser": "beautifulsoup",
                    "section": title,
                    "source_url": page.url,
                    "source_title": title,
                },
            )
        ],
        metadata={
            "content_type": page.content_type,
            "source_type": source_type,
            "source_url": page.url,
            "source_title": title,
            "source_path": urlparse(page.url).path or "/",
            "parser": "beautifulsoup",
        },
        language=detect_language(page.text),
    )


def normalize_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    url, _fragment = urldefrag(value)
    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = urlparse(f"https://{url.lstrip('/')}")
    return parsed.geturl()
