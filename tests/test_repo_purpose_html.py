from html.parser import HTMLParser
from pathlib import Path


PAGE = Path(__file__).parents[1] / "repo-purpose.html"
PURPOSE_DOC = Path(__file__).parents[1] / "docs" / "architecture" / "repository-purpose.md"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang = None
        self.external_assets: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
        if tag in {"link", "script", "img"}:
            source = values.get("href") or values.get("src")
            if source and not source.startswith(("#", "data:")):
                self.external_assets.append(source)

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def test_repo_purpose_page_is_self_contained_and_explains_the_project() -> None:
    parser = PageParser()
    parser.feed(PAGE.read_text(encoding="utf-8"))
    text = " ".join(parser.text)

    assert parser.lang == "ko"
    assert parser.external_assets == []
    assert "백업이 아니라" in text
    assert "장비 데이터 지도" in text
    for label in ("Inventory", "Grouping", "Sampling", "Extraction", "Local LLM", "Data Map"):
        assert label in text
    for stage in range(1, 6):
        assert f"{stage}단계" in text
    for safeguard in ("읽기 전용", "회사망", "대표 샘플", "근거"):
        assert safeguard in text


def test_repository_purpose_doc_points_to_the_canonical_architecture() -> None:
    text = PURPOSE_DOC.read_text(encoding="utf-8")

    assert text.startswith("# Equipment Data Map 저장소의 목적")
    assert "백업이 아니라" in text
    assert "장비 데이터 지도" in text
    assert "[Equipment Data Map 아키텍처](equipment-data-map.md)" in text
