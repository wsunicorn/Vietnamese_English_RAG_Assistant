from zipfile import ZipFile

import asyncio

from app.core.config import Settings
from app.ingestion.parsers import DocumentParser
from app.ingestion.web import fetch_sitemap_urls, normalize_url, page_to_parsed_document, WebPage


def test_markdown_parser_preserves_heading_sections(tmp_path):
    path = tmp_path / "handbook.md"
    path.write_text("# Leave Policy\nEmployees get 12 days.\n\n## Approval\nManager approval required.")

    parsed = DocumentParser().parse(path, filename="handbook.md", content_type="text/markdown")

    assert parsed.metadata["source_type"] == "markdown"
    assert [page.metadata["section"] for page in parsed.pages] == ["Leave Policy", "Approval"]


def test_notion_zip_parser_walks_markdown_pages(tmp_path):
    path = tmp_path / "notion.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("Team Wiki/Onboarding.md", "# Onboarding\nBring your laptop.")
        archive.writestr("Team Wiki/assets/logo.png", b"ignored")

    parsed = DocumentParser().parse_many(path, filename="notion.zip", content_type="application/zip")

    assert len(parsed) == 1
    assert parsed[0].metadata["source_type"] == "notion"
    assert parsed[0].metadata["source_path"] == "Team Wiki/Onboarding.md"


def test_page_to_parsed_document_adds_url_metadata():
    parsed = page_to_parsed_document(
        WebPage(
            url="https://example.com/docs",
            title="Docs",
            text="Internal policy content",
            content_type="text/html",
        ),
        source_type="web",
    )

    assert parsed.metadata["source_url"] == "https://example.com/docs"
    assert parsed.pages[0].metadata["source_title"] == "Docs"


def test_sitemap_parser_filters_to_same_domain(monkeypatch):
    class Response:
        text = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/a</loc></url>
          <url><loc>https://other.test/b</loc></url>
        </urlset>
        """

    async def fake_get(url, *, settings):
        return Response()

    monkeypatch.setattr("app.ingestion.web.http_get", fake_get)

    urls = asyncio.run(
        fetch_sitemap_urls(
            "https://example.com/sitemap.xml",
            max_pages=10,
            settings=Settings(),
        )
    )

    assert urls == ["https://example.com/a"]


def test_normalize_url_defaults_to_https():
    assert normalize_url("example.com/docs#section") == "https://example.com/docs"
