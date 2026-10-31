"""Check #333 in Chromium against a built app, real API and controlled database.

Seed a disposable database with web/design/333/seed.sql, then pass the built
app's origin. Only poster images are intercepted. API requests reach FastAPI.
Run from the root with uv run --with playwright python scripts/verify_browse_ui.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, expect, sync_playwright


def check_grid(page: Page, columns: int) -> None:
    """Assert emitted CSS produces the approved grid without page overflow."""
    expect(page.locator(".minimal-card")).to_have_count(24)
    result = page.locator(".minimal-grid").evaluate(
        """grid => ({
            columns: getComputedStyle(grid).gridTemplateColumns.split(' ').length,
            overflow: document.documentElement.scrollWidth > innerWidth,
            background: getComputedStyle(document.body).backgroundColor
        })"""
    )
    assert result == {
        "columns": columns,
        "overflow": False,
        "background": "rgb(255, 255, 255)",
    }, result


def verify(origin: str, output: Path) -> None:
    """Exercise hover, touch, keyboard, independent catalogue and direct detail."""
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        # Deliberately synthetic artwork for controlled rows, never API substitution.
        page.route(
            "https://posters.example/*",
            lambda route: route.fulfill(
                content_type="image/svg+xml",
                body='<svg xmlns="http://www.w3.org/2000/svg" width="200" '
                'height="300"><rect width="200" height="300" fill="#426b73"/>'
                '<text x="12" y="150" fill="white">Test poster</text></svg>',
            ),
        )
        requests: list[str] = []
        page.on(
            "request",
            lambda request: (
                requests.append(request.url) if "/v1/" in request.url else None
            ),
        )
        page.goto(origin)
        check_grid(page, 4)
        assert len(requests) == 1 and "/v1/screening-movies?" in requests[0]
        expect(
            page.get_by_text("About this section").locator("..")
        ).not_to_have_attribute("open", "")
        card = page.locator(".minimal-card").first
        card.hover()
        preview = page.get_by_role("region", name="Controlled film 00 screenings")
        expect(preview).to_be_visible()
        card_bounds = card.bounding_box()
        preview_bounds = preview.bounding_box()
        assert card_bounds and preview_bounds
        assert abs(preview_bounds["y"] - card_bounds["y"] - card_bounds["height"]) < 1
        # Move across the exact card/preview boundary before interacting with its links.
        x = card_bounds["x"] + 40
        page.mouse.move(x, card_bounds["y"] + card_bounds["height"] - 2)
        page.mouse.move(x, preview_bounds["y"] + 8, steps=8)
        expect(preview).to_be_visible()
        expect(preview.get_by_role("link", name="Full schedule")).to_be_visible()
        assert preview.locator(".minimal-time").count() == 3
        # Crossing cards quickly never leaves multiple overlays open.
        for index in range(4):
            page.locator(".minimal-card").nth(index).hover()
            assert page.locator(".minimal-preview").count() == 1
        arrow = page.get_by_role("button", name="Preview Controlled film 03")
        arrow.focus()
        page.keyboard.press("Escape")
        expect(arrow).to_be_focused()
        expect(page.locator(".minimal-preview")).to_have_count(0)
        page.mouse.move(0, 0)
        page.screenshot(path=str(output / "desktop.png"), full_page=True)
        page.locator(".minimal-card").first.hover()
        page.get_by_role("link", name="View Controlled film 00").click()
        expect(page.get_by_role("heading", name="Controlled film 00")).to_be_visible()
        page.get_by_role("link", name="Screenings", exact=True).click()
        check_grid(page, 4)
        page.get_by_role("link", name="Movies", exact=True).click()
        expect(page.locator(".minimal-library-card")).to_have_count(24)
        page.get_by_role("searchbox", name="Search movies").fill("Controlled film 27")
        expect(page.get_by_role("link", name="View Controlled film 27")).to_be_visible()
        expect(page.locator(".minimal-library-card")).to_have_count(1)
        catalogue_requests = [
            url for url in requests if "/v1/movies?" in url and "ids=" not in url
        ]
        assert catalogue_requests and all(
            "size=24" in url for url in catalogue_requests
        )
        assert all(
            "start=" not in url and "from=" not in url for url in catalogue_requests
        )
        page.get_by_role("link", name="View Controlled film 27").click()
        expect(page.get_by_role("heading", name="Controlled film 27")).to_be_visible()
        expect(
            page.get_by_text(
                "No screenings in these dates. Try another date or clear the filters."
            )
        ).to_be_visible()
        expect(page.get_by_role("link", name="Movies", exact=True)).to_have_attribute(
            "aria-current", "page"
        )
        assert page.url.endswith("/movies/catalogue%2F27")
        page.reload()
        expect(page.get_by_role("heading", name="Controlled film 27")).to_be_visible()
        metadata_queries = [
            parse_qs(urlsplit(url).query)
            for url in requests
            if "/v1/movies?" in url and "ids=" in url
        ]
        assert metadata_queries and all(
            len(query["ids"]) == 1 and query.get("size") == ["1"]
            for query in metadata_queries
        )
        assert any(query["ids"] == ["catalogue/27"] for query in metadata_queries)
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        mobile_page = mobile.new_page()
        mobile_page.route("https://posters.example/*", lambda route: route.abort())
        mobile_page.goto(origin)
        check_grid(mobile_page, 2)
        mobile_page.get_by_role("button", name="Preview Controlled film 00").tap()
        expect(mobile_page.locator(".minimal-preview")).to_have_count(1)
        mobile_page.get_by_role("button", name="Close preview").tap()
        expect(mobile_page.locator(".minimal-preview")).to_have_count(0)
        mobile_page.screenshot(path=str(output / "mobile.png"), full_page=True)
        (output / "requests.json").write_text(json.dumps(requests, indent=2))
        browser.close()
        print(
            "PASS: four/two columns, no overflow, hover boundary, sweep, keyboard, "
            "touch, bounded catalogue search, direct movie schedule and refresh."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:14333")
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/marquise-333-browser")
    )
    args = parser.parse_args()
    verify(args.origin, args.output)
