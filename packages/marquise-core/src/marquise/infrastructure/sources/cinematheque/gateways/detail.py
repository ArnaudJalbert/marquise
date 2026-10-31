"""Extract cinema website facts linked by ticket performance IDs."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

_ARTICLE_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.DOTALL)
_DETAIL_LINK_RE = re.compile(r'href="(/en/cinema/[^"?#]+/)"')
_MODAL_RE = re.compile(r"modal-tickets-\d+")
_FACT_RE = re.compile(
    r'<div class="color-black-60 text-shorter line-height-compressed">'
    r"([^<]+)</div>\s*<div[^>]*>(.*?)</div>",
    re.DOTALL,
)


class _TicketModals(HTMLParser):
    """Read each modal's dated ticket performance IDs."""

    def __init__(self) -> None:
        """Initialize the current modal stack and performance links."""
        super().__init__()
        self.divs: list[str | None] = []
        self.modals: dict[tuple[str, str], set[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Read ticket links inside provider ticket modals."""
        values = dict(attrs)
        if tag == "div":
            modal = values.get("data-id") or ""
            self.divs.append(
                modal
                if _MODAL_RE.fullmatch(modal)
                else self.divs[-1]
                if self.divs
                else None
            )
        if not self.divs or not self.divs[-1]:
            return
        target = values.get("href") or values.get("data-href") or ""
        url = urlsplit(target)
        if url.hostname not in {"omniwebticketing.com", "omniwebticketing6.com"}:
            return
        if url.path.rstrip("/") != "/cinematheque":
            return
        query = parse_qs(url.query)
        for date in query.get("schdate", []):
            for performance in query.get("perfix", []):
                self.modals.setdefault((date, performance), set()).add(self.divs[-1])

    def handle_endtag(self, tag: str) -> None:
        """Leave a modal when its containing div closes."""
        if tag == "div" and self.divs:
            self.divs.pop()


def find_detail_url(
    index_html: str, performances: set[tuple[str, str]], base_url: str
) -> str | None:
    """Resolve a unique film card through its ticket modal, never a title guess."""
    parser = _TicketModals()
    parser.feed(index_html)
    modals = set().union(*(parser.modals.get(key, set()) for key in performances))
    urls: set[str] = set()
    for article in _ARTICLE_RE.findall(index_html):
        if modals.intersection(_MODAL_RE.findall(article)):
            urls.update(
                urljoin(base_url, path) for path in _DETAIL_LINK_RE.findall(article)
            )
    return next(iter(urls)) if len(urls) == 1 else None


def extract_detail(detail_html: str) -> dict:
    """Read labelled year, people and runtime facts from a cinema film page."""
    facts = {
        label: " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())
        for label, value in _FACT_RE.findall(detail_html)
    }
    result: dict = {}
    for label, field in (("Directed by", "directors"), ("Actors", "cast")):
        names = [
            name.strip() for name in facts.get(label, "").split(",") if name.strip()
        ]
        if names:
            result[field] = names
    year = facts.get("Year", "")
    if re.fullmatch(r"\d{4}", year) and int(year) > 0:
        result["release_year"] = int(year)
    duration = re.fullmatch(r"(\d+)\s*min", facts.get("Duration", ""))
    if duration and int(duration.group(1)) > 0:
        result["duration_minutes"] = int(duration.group(1))
    return result
