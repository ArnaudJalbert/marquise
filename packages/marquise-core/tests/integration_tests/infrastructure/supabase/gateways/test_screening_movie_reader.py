"""Movie-first pagination against a disposable PostgreSQL database."""

from datetime import UTC, datetime, timedelta

import asyncpg
import pytest

from marquise.infrastructure.supabase.gateways.screening_movie_reader import (
    SupabaseScreeningMovieReadGateway,
)
from marquise.interface_adapters.readers.screening_movie_reader import (
    SupabaseScreeningMovieReader,
)


@pytest.mark.asyncio
async def test_distinct_movie_pages_previews_and_end_metadata(
    db_pool: asyncpg.Pool,
) -> None:
    """Many shows cannot consume a movie page; preview selection precedes grouping."""
    async with db_pool.acquire() as conn:
        await conn.execute("""INSERT INTO "marquise-test".cinemas(id,name)
                              VALUES ('c1','Cinema One'),('c2','Cinema Two')""")
        await conn.executemany(
            'INSERT INTO "marquise-test".movies(id,title,directors) VALUES($1,$2,$3)',
            [(f"m{i:02}", f"Film {i}", "Director One,Director Two") for i in range(27)],
        )
        await conn.execute(
            """UPDATE "marquise-test".movies SET tmdb_rating = 8.1,
               tmdb_vote_count = 1234 WHERE id = 'm00' """
        )
        # All movies tie on their first show. One has more than an old 100-show page.
        start = datetime(2026, 11, 1, 4, tzinfo=UTC)
        shows = [
            (
                f"s{i:02}-{j:03}",
                f"m{i:02}",
                "c1" if j % 2 == 0 else "c2",
                (start + timedelta(hours=1, minutes=j)).replace(tzinfo=None),
                "VO" if j % 2 == 0 else "VOSTF",
                "https://tickets.example/real" if j else None,
            )
            for i in range(27)
            for j in range(120 if i == 0 else 1)
        ]
        # Already-started and out-of-window films must not become eligible.
        await conn.execute("""INSERT INTO "marquise-test".movies(id,title)
                              VALUES ('past','Past'),('future','Future')""")
        shows.extend(
            [
                ("started", "past", "c1", start.replace(tzinfo=None), "VF", None),
                ("outside", "future", "c1", datetime(2026, 11, 2, 5), "VF", None),
            ]
        )
        await conn.executemany(
            """INSERT INTO "marquise-test".screenings
            (id,movie_id,cinema_id,showtime,language,ticket_url)
            VALUES($1,$2,$3,$4,$5,$6)""",
            shows,
        )
    reader = SupabaseScreeningMovieReader(
        SupabaseScreeningMovieReadGateway(db_pool, "marquise-test")
    )
    end = datetime(2026, 11, 2, 4, 59, 59, 999999, tzinfo=UTC)
    first = await reader.search(start, end, start, 1)
    second = await reader.search(start, end, start, 2)
    beyond = await reader.search(start, end, start, 3)
    assert [m.id for m in first.items] == [f"m{i:02}" for i in range(24)]
    assert [m.id for m in second.items] == ["m24", "m25", "m26"]
    assert first.total == second.total == beyond.total == 27
    assert beyond.items == []
    preview = first.items[0]
    assert preview.directors == ("Director One", "Director Two")
    assert (preview.tmdb_rating, preview.tmdb_vote_count) == (8.1, 1234)
    assert second.items[0].tmdb_rating is None
    assert [s.id for s in preview.screenings] == ["s00-000", "s00-001", "s00-002"]
    assert [s.cinema_name for s in preview.screenings] == [
        "Cinema One",
        "Cinema Two",
        "Cinema One",
    ]
    assert preview.screenings[0].ticket_url is None
    assert preview.screenings[1].ticket_url == "https://tickets.example/real"
    assert all(s.showtime.tzinfo is not None for s in preview.screenings)
    empty = await reader.search(
        end + timedelta(days=1), end + timedelta(days=2), start, 1
    )
    assert empty.items == [] and empty.total == 0


@pytest.mark.asyncio
async def test_inclusive_dst_bounds_ordering_and_started_previews(
    db_pool: asyncpg.Pool,
) -> None:
    """Both repeated autumn hours and the last local instant qualify before paging."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO "marquise-test".cinemas(id,name) VALUES('c1','Cinema')"""
        )
        await conn.execute("""INSERT INTO "marquise-test".movies(id,title)
                              VALUES ('a','A'),('z','Z'),('outside','Outside')""")
        await conn.executemany(
            """INSERT INTO "marquise-test".screenings
            (id,movie_id,cinema_id,showtime) VALUES($1,$2,'c1',$3)""",
            [
                ("started", "a", datetime(2026, 11, 1, 4)),
                ("first-repeated-hour", "z", datetime(2026, 11, 1, 5, 30)),
                ("second-repeated-hour", "a", datetime(2026, 11, 1, 6, 30)),
                ("last-local-instant", "a", datetime(2026, 11, 2, 4, 59, 59, 999999)),
                ("next-local-midnight", "outside", datetime(2026, 11, 2, 5)),
            ],
        )
    gateway = SupabaseScreeningMovieReadGateway(db_pool, "marquise-test")
    start = datetime(2026, 11, 1, 4, tzinfo=UTC)
    end = datetime(2026, 11, 2, 4, 59, 59, 999999, tzinfo=UTC)
    result = await gateway.search(start, end, start, 1)
    assert [m["id"] for m in result.rows] == ["z", "a"]
    assert result.total == 2
    assert [s["id"] for s in result.rows[1]["screenings"]] == [
        "second-repeated-hour",
        "last-local-instant",
    ]


@pytest.mark.asyncio
async def test_filters_apply_to_qualifying_screenings_before_preview_selection(
    db_pool: asyncpg.Pool,
) -> None:
    """Combined filters exclude unrelated screenings from eligibility and previews."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO "marquise-test".cinemas(id,name)
               VALUES ('c1','Cinema One'),('c2','Cinema Two')"""
        )
        await conn.execute(
            """INSERT INTO "marquise-test".movies(id,title)
               VALUES ('match','Dune'),('other','Other Film')"""
        )
        await conn.executemany(
            """INSERT INTO "marquise-test".screenings
               (id,movie_id,cinema_id,showtime,language)
               VALUES($1,$2,$3,$4,$5)""",
            [
                ("correct", "match", "c2", datetime(2026, 11, 4, 0, 30), "VOSTF"),
                ("cinema", "match", "c1", datetime(2026, 11, 4, 0, 45), "VOSTF"),
                ("language", "match", "c2", datetime(2026, 11, 4, 1), "VO"),
                ("hour", "match", "c2", datetime(2026, 11, 4, 1, 30), "VOSTF"),
                ("title", "other", "c2", datetime(2026, 11, 4, 1, 45), "VOSTF"),
            ],
        )
    gateway = SupabaseScreeningMovieReadGateway(db_pool, "marquise-test")
    result = await gateway.search(
        datetime(2026, 11, 3, 5, tzinfo=UTC),
        datetime(2026, 11, 4, 4, 59, tzinfo=UTC),
        datetime(2026, 11, 3, 5, tzinfo=UTC),
        1,
        "Dune",
        ("c2",),
        ("VOSTF",),
        ((18, 20),),
    )
    assert result.total == 1
    assert [movie["id"] for movie in result.rows] == ["match"]
    assert [screening["id"] for screening in result.rows[0]["screenings"]] == [
        "correct"
    ]


@pytest.mark.asyncio
async def test_hour_ranges_match_with_or_in_montreal_time_and_cinemas_are_excluded(
    db_pool: asyncpg.Pool,
) -> None:
    """Non-adjacent half-open local hour ranges match; excluded cinemas never do."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO "marquise-test".cinemas(id,name)
               VALUES ('c1','Cinema One'),('c2','Cinema Two')"""
        )
        await conn.execute(
            """INSERT INTO "marquise-test".movies(id,title)
               VALUES ('morning','M'),('boundary','B'),('evening','E'),
                      ('late','L'),('excluded','X')"""
        )
        # 2026-11-05 is UTC-5 in Montreal: 15:00 UTC is 10:00 local.
        await conn.executemany(
            """INSERT INTO "marquise-test".screenings
               (id,movie_id,cinema_id,showtime) VALUES($1,$2,$3,$4)""",
            [
                ("10h", "morning", "c1", datetime(2026, 11, 5, 15)),
                ("17h", "boundary", "c1", datetime(2026, 11, 5, 22)),
                ("18h", "evening", "c1", datetime(2026, 11, 5, 23)),
                ("23h59", "late", "c1", datetime(2026, 11, 6, 4, 59)),
                ("11h-c2", "excluded", "c2", datetime(2026, 11, 5, 16)),
            ],
        )
    gateway = SupabaseScreeningMovieReadGateway(db_pool, "marquise-test")
    now = datetime(2026, 11, 5, 5, tzinfo=UTC)
    result = await gateway.search(
        now,
        datetime(2026, 11, 6, 4, 59, 59, tzinfo=UTC),
        now,
        1,
        hours=((0, 17), (21, 24)),
        excluded_cinemas=("c2",),
    )
    assert [movie["id"] for movie in result.rows] == ["morning", "late"]
    assert result.total == 2
    unfiltered = await gateway.search(
        now, datetime(2026, 11, 6, 4, 59, 59, tzinfo=UTC), now, 1
    )
    assert unfiltered.total == 5
