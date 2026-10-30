"""Verify the isolated Compose stack using real HTTP and Chromium.

Start with make local-up. Run from the repository root with:
uv run --with playwright python scripts/verify_local_stack.py
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from playwright.sync_api import expect, sync_playwright

ORIGIN = "http://127.0.0.1:4300"


def read_page(path: str, params: dict) -> dict:
    """Read the real API through the app's same-origin reverse proxy."""
    with urlopen(
        f"{ORIGIN}/v1/{path}?{urlencode(params, doseq=True)}", timeout=10
    ) as response:
        return json.load(response)


def verify() -> None:
    """Check distinct-movie pages, full dense windows and browser navigation."""
    today = datetime.now(ZoneInfo("America/Montreal")).date()
    selection = {"start": today.isoformat(), "end": today.isoformat()}
    first = read_page("screening-movies", selection)
    second = read_page("screening-movies", {**selection, "page": 2})
    assert len(first["items"]) == 24 and first["pages"] == 2
    all_ids = [item["id"] for item in first["items"] + second["items"]]
    assert len(all_ids) == len(set(all_ids)) == first["total"] >= 26
    assert all(len(item["screenings"]) <= 3 for item in first["items"])
    catalogue = read_page("movies", {"size": 24})
    assert catalogue["total"] == 53 and catalogue["pages"] == 3
    catalogue_items = list(catalogue["items"])
    for page in range(2, catalogue["pages"] + 1):
        catalogue_items.extend(
            read_page("movies", {"size": 24, "page": page})["items"]
        )
    assert len(catalogue_items) == catalogue["total"]
    assert all(item["poster_url"] for item in catalogue_items)
    assert not any(
        item["title"].startswith("Local test film") for item in catalogue_items
    )
    title = read_page("movies", {"title": "Arrival", "size": 24})
    assert [item["id"] for item in title["items"]] == ["local/catalogue-only"]
    filtered = read_page(
        "screening-movies",
        {
            **selection,
            "title": "Dune",
            "cinema": ["local-cinema-1"],
            "language": ["VOSTF"],
            "start_hour": 15,
            "end_hour": 17,
        },
    )
    assert [item["id"] for item in filtered["items"]] == ["local-dune"]
    assert all(
        item["cinema_id"] == "local-cinema-1"
        and item["language"] == "VOSTF"
        and "15:00"
        <= datetime.fromisoformat(item["showtime"])
        .astimezone(ZoneInfo("America/Montreal"))
        .strftime("%H:%M")
        <= "17:00"
        for item in filtered["items"][0]["screenings"]
    )
    # Calendar bounds include the DST transition when it falls in the next fortnight.
    zone = ZoneInfo("America/Montreal")
    start = datetime.combine(today, datetime.min.time(), zone)
    end = datetime.combine(today + timedelta(days=14), datetime.min.time(), zone)
    params = {
        "movie_id": "local-dune",
        "from": start.isoformat(),
        "to": (end - timedelta(microseconds=1)).isoformat(),
        "size": 100,
    }
    dense = read_page("screenings", params)
    items = list(dense["items"])
    for page in range(2, dense["pages"] + 1):
        items.extend(read_page("screenings", {**params, "page": page})["items"])
    assert len(items) == dense["total"] == 350 and dense["pages"] == 4
    counts: dict[date, int] = {}
    for item in items:
        day = datetime.fromisoformat(item["showtime"]).astimezone(zone).date()
        counts[day] = counts.get(day, 0) + 1
    assert len(counts) == 14 and set(counts.values()) == {25}
    assert len({item["cinema_id"] for item in items}) == 7

    output = Path("/tmp/marquise-local-stack")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        api_urls: list[str] = []
        page.on(
            "request",
            lambda request: (
                api_urls.append(request.url) if "/v1/" in request.url else None
            ),
        )
        page.goto(ORIGIN)
        loaded_posters = page.evaluate(
            """urls => Promise.all(urls.map(url => new Promise(resolve => {
                const image = new Image();
                image.onload = () => resolve(image.naturalWidth > 0);
                image.onerror = () => resolve(false);
                image.src = url;
            })))""",
            [item["poster_url"] for item in catalogue_items],
        )
        assert all(loaded_posters), "At least one local catalogue poster failed to load"
        expect(page.locator(".minimal-card")).to_have_count(24)
        before = page.evaluate(
            """() => Object.fromEntries(
                ['.minimal-shortcuts', '.minimal-grid'].map(selector => {
                    const element = document.querySelector(selector);
                    const rect = element.getBoundingClientRect();
                    const {x, y, width, height} = rect;
                    return [selector, {x, y, width, height}];
                })
            )"""
        )
        page.get_by_text("Filters", exact=True).click()
        panel = page.locator(".minimal-filter-panels")
        expect(panel).to_be_visible()
        bounds = panel.evaluate(
            """element => {
                const {x, y, right, bottom} = element.getBoundingClientRect();
                return {x, y, right, bottom};
            }"""
        )
        after = page.evaluate(
            """() => Object.fromEntries(
                ['.minimal-shortcuts', '.minimal-grid'].map(selector => {
                    const element = document.querySelector(selector);
                    const rect = element.getBoundingClientRect();
                    const {x, y, width, height} = rect;
                    return [selector, {x, y, width, height}];
                })
            )"""
        )
        assert before == after
        assert bounds["x"] >= 0 and bounds["right"] <= 1280
        start_slider = page.get_by_role("slider", name="Start time")
        start_slider.press("ArrowRight")
        expect(start_slider).to_have_value("1")
        slider_bounds = start_slider.bounding_box()
        assert slider_bounds is not None
        y = slider_bounds["y"] + slider_bounds["height"] / 2
        page.mouse.move(
            slider_bounds["x"] + 8 + (slider_bounds["width"] - 16) / 24,
            y,
        )
        page.mouse.down()
        page.mouse.move(slider_bounds["x"] + slider_bounds["width"] / 2, y)
        page.mouse.up()
        expect(start_slider).to_have_value("12")
        end_slider = page.get_by_role("slider", name="End time")
        end_slider.press("ArrowLeft")
        expect(end_slider).to_have_value("23")
        slider_bounds = end_slider.bounding_box()
        assert slider_bounds is not None
        y = slider_bounds["y"] + slider_bounds["height"] / 2
        page.mouse.move(
            slider_bounds["x"] + 8 + (slider_bounds["width"] - 16) * 23 / 24,
            y,
        )
        page.mouse.down()
        page.mouse.move(
            slider_bounds["x"] + 8 + (slider_bounds["width"] - 16) * 20 / 24,
            y,
        )
        page.mouse.up()
        expect(end_slider).to_have_value("20")
        page.get_by_role("checkbox", name="Local test cinema 1").check()
        page.get_by_role("checkbox", name="VOSTF").check()
        page.get_by_role("searchbox", name="Movie title").fill("Dune")
        page.wait_for_url("**title=Dune**")
        expect(page.locator(".minimal-card")).to_have_count(1)
        query = parse_qs(urlparse(page.url).query)
        assert query["title"] == ["Dune"]
        assert query["cinema"] == ["local-cinema-1"]
        assert query["language"] == ["VOSTF"]
        assert query["from"] == ["12:00"]
        assert query["to"] == ["20:00"]
        page.go_back()
        expect(page.get_by_role("searchbox", name="Movie title")).to_have_value("")
        page.get_by_role("link", name="Movies", exact=True).click()
        page.get_by_role("searchbox", name="Search movies").fill("Dune: Part Two")
        link = page.get_by_role("link", name="View Dune: Part Two")
        expect(link).to_be_visible()
        expect(link.locator("img")).to_be_visible()
        assert link.locator("img").evaluate(
            "img => img.complete && img.naturalWidth > 0"
        )
        link.click()
        expect(
            page.get_by_role("heading", name="Dune: Part Two", exact=True)
        ).to_be_visible()
        expect(page.locator(".minimal-time")).to_have_count(100)
        page.screenshot(path=str(output / "dense-schedule.png"), full_page=True)
        page.get_by_role("link", name="Movies", exact=True).click()
        page.get_by_role("searchbox", name="Search movies").fill("Arrival")
        page.get_by_role("link", name="View Arrival").click()
        expect(page.get_by_role("heading", name="Arrival", exact=True)).to_be_visible()
        assert page.url.endswith("/movies/local%2Fcatalogue-only")
        page.reload()
        expect(
            page.get_by_text(
                "No screenings in these dates. Try another date or clear the filters."
            )
        ).to_be_visible()
        assert api_urls and all(url.startswith(ORIGIN + "/v1/") for url in api_urls)
        mobile = browser.new_page(
            viewport={"width": 390, "height": 844}, has_touch=True
        )
        mobile.goto(ORIGIN)
        expect(mobile.locator(".minimal-card")).to_have_count(24)
        assert mobile.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        mobile_columns = mobile.locator(".minimal-grid").evaluate(
            "element => getComputedStyle(element).gridTemplateColumns.split(' ').length"
        )
        assert mobile_columns == 2
        mobile.get_by_text("Filters", exact=True).click()
        mobile_panel = mobile.locator(".minimal-filter-panels")
        expect(mobile_panel).to_be_visible()
        assert mobile_panel.evaluate(
            "element => element.getBoundingClientRect().right <= window.innerWidth"
        )
        mobile_slider = mobile.get_by_role("slider", name="Start time")
        mobile_slider.scroll_into_view_if_needed()
        slider_bounds = mobile_slider.bounding_box()
        assert slider_bounds is not None
        session = mobile.context.new_cdp_session(mobile)
        y = slider_bounds["y"] + slider_bounds["height"] / 2
        session.send(
            "Input.dispatchTouchEvent",
            {
                "type": "touchStart",
                "touchPoints": [{"x": slider_bounds["x"] + 8, "y": y, "id": 1}],
            },
        )
        session.send(
            "Input.dispatchTouchEvent",
            {
                "type": "touchMove",
                "touchPoints": [
                    {
                        "x": slider_bounds["x"] + slider_bounds["width"] / 2,
                        "y": y,
                        "id": 1,
                    }
                ],
            },
        )
        session.send(
            "Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}
        )
        expect(mobile_slider).to_have_value("12")
        mobile_end = mobile.get_by_role("slider", name="End time")
        slider_bounds = mobile_end.bounding_box()
        assert slider_bounds is not None
        y = slider_bounds["y"] + slider_bounds["height"] / 2
        session.send(
            "Input.dispatchTouchEvent",
            {
                "type": "touchStart",
                "touchPoints": [
                    {
                        "x": slider_bounds["x"] + slider_bounds["width"] - 8,
                        "y": y,
                        "id": 1,
                    }
                ],
            },
        )
        session.send(
            "Input.dispatchTouchEvent",
            {
                "type": "touchMove",
                "touchPoints": [
                    {
                        "x": slider_bounds["x"]
                        + 8
                        + (slider_bounds["width"] - 16) * 18 / 24,
                        "y": y,
                        "id": 1,
                    }
                ],
            },
        )
        session.send(
            "Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}
        )
        expect(mobile_end).to_have_value("18")
        mobile.close()
        browser.close()
    print(
        json.dumps(
            {
                "catalogue_movies": catalogue["total"],
                "catalogue_posters_loaded": sum(loaded_posters),
                "eligible_today": first["total"],
                "dense_screenings": len(items),
                "dense_days": 14,
                "cinemas": 7,
                "screening_pages": dense["pages"],
                "browser_api_requests": len(api_urls),
                "result": "PASS",
            }
        )
    )


if __name__ == "__main__":
    verify()
