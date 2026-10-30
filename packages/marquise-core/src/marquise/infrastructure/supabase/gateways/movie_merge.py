"""Isolated merge persistence. No identity discovery or canonical selection.

The caller validates eligibility through MergeMoviesUseCase. Whole-row snapshots
include every screening field and unknown movie columns. Revisions are opaque
canonical JSON so exact post-state retries need no new schema or replay table.
"""

import json
from datetime import datetime

import asyncpg

from marquise.application.movie_workflows import (
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MovieMetadataSnapshot,
    MovieMetadataValues,
)
from marquise.infrastructure.supabase.connection_pool import ConnectionPool


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _revision(
    movie: dict,
    screenings: list[dict],
    request: MergeMoviesInputData,
    identity_owners: list[dict],
) -> str:
    return json.dumps(
        [
            movie,
            screenings,
            request.survivor_id,
            sorted(request.duplicate_ids),
            identity_owners,
        ],
        sort_keys=True,
        separators=(",", ":"),
    )


def _snapshot(
    movie: dict,
    screenings: list[dict],
    refs: tuple[str, ...],
    request: MergeMoviesInputData,
    identity_owners: list[dict],
) -> MovieMetadataSnapshot:
    fields = dict(movie)
    for name, column in (
        ("directors", "directors"),
        ("cast", "cast_members"),
        ("genres", "genres"),
        ("origin_countries", "origin_countries"),
    ):
        value = movie.get(column)
        fields[name] = tuple(value.split(", ")) if value is not None else None
    values = MovieMetadataValues(
        **{name: fields.get(name) for name in MovieMetadataValues.__dataclass_fields__}
    )
    stamp = movie.get("metadata_enriched_at")
    return MovieMetadataSnapshot(
        movie["id"],
        _revision(movie, screenings, request, identity_owners),
        values,
        movie.get("tmdb_id"),
        datetime.fromisoformat(stamp) if stamp else None,
        tuple(row["id"] for row in screenings),
        refs,
    )


class SupabaseMovieMergeGateway:
    """Provide the merge method for the metadata repository's injected gateway.

    No schema is created here. #359 owns persistence composition and schema;
    #355 connects this method to MovieMetadataRepository.merge.
    """

    def __init__(self, pool: ConnectionPool, schema: str = "marquise") -> None:
        self._pool = pool
        self._schema = schema
        self._movies = f"{_quote(schema)}.movies"
        self._screenings = f"{_quote(schema)}.screenings"

    async def merge(self, request: MergeMoviesInputData) -> MergeMoviesOutputData:
        """Read a preview or atomically compare and move approved references."""
        try:
            async with self._pool.acquire() as conn, conn.transaction():
                await conn.execute("SET LOCAL lock_timeout = '5s'")
                await conn.execute("SET LOCAL statement_timeout = '60s'")
                if request.approved_snapshot is None:
                    await conn.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                    )
                else:
                    # Block concurrent catalog writes and new FK definitions.
                    await conn.execute(
                        f"LOCK TABLE {self._movies}, {self._screenings} "
                        "IN SHARE ROW EXCLUSIVE MODE"
                    )
                return await self._merge(conn, request)
        except (
            asyncpg.IntegrityConstraintViolationError,
            asyncpg.DeadlockDetectedError,
            asyncpg.LockNotAvailableError,
            asyncpg.QueryCanceledError,
        ):
            return MergeMoviesOutputData(
                "blocked",
                (),
                blockers=("Write/reference conflict; transaction rolled back",),
            )

    async def _merge(
        self, conn: asyncpg.Connection, request: MergeMoviesInputData
    ) -> MergeMoviesOutputData:
        ids = [request.survivor_id, *request.duplicate_ids]
        refs = await self._references(conn, ids, request.approved_snapshot is not None)
        movies = [
            json.loads(row["data"])
            for row in await conn.fetch(
                f"SELECT to_jsonb(m) AS data FROM {self._movies} m "
                "WHERE id = ANY($1::text[]) ORDER BY id",
                ids,
            )
        ]
        screenings = [
            json.loads(row["data"])
            for row in await conn.fetch(
                f"SELECT to_jsonb(s) AS data FROM {self._screenings} s "
                "WHERE movie_id = ANY($1::text[]) ORDER BY id",
                ids,
            )
        ]
        # Pin identity uniqueness outside the group too. An unrelated owner change
        # conservatively invalidates approval rather than racing canonical choice.
        identity_owners = [
            dict(row)
            for row in await conn.fetch(
                f"SELECT id, tmdb_id FROM {self._movies} "
                "WHERE tmdb_id IS NOT NULL ORDER BY id"
            )
        ]
        snapshots = tuple(
            _snapshot(
                movie,
                [s for s in screenings if s["movie_id"] == movie["id"]],
                refs,
                request,
                identity_owners,
            )
            for movie in movies
        )
        blockers = list(refs)
        if any(
            movie.get("tmdb_id")
            for movie in movies
            if movie["id"] != request.survivor_id
        ):
            blockers.append("Cannot delete a stored TMDB identity")
        if len(movies) != len(ids):
            if (
                request.approved_snapshot
                and not refs
                and self._is_retry(request, snapshots)
            ):
                moved = tuple(
                    sorted(
                        s
                        for snap in request.approved_snapshot
                        if snap.movie_id != request.survivor_id
                        for s in snap.screening_ids
                    )
                )
                return MergeMoviesOutputData("applied", snapshots, moved)
            blockers.append("Missing target movie IDs")
        collisions: dict[tuple[str, str], list[str]] = {}
        for row in screenings:
            collisions.setdefault((row["cinema_id"], row["showtime"]), []).append(
                row["id"]
            )
        for key, screening_ids in collisions.items():
            if len(screening_ids) > 1:
                blockers.append(f"Screening collision {key}: {','.join(screening_ids)}")
        if request.approved_snapshot is not None:
            approved = {s.movie_id: s for s in request.approved_snapshot}
            if len(approved) != len(ids) or approved != {
                s.movie_id: s for s in snapshots
            }:
                blockers.append("Stale or mismatched approved snapshot")
        if blockers:
            return MergeMoviesOutputData("blocked", snapshots, blockers=tuple(blockers))
        if request.approved_snapshot is None:
            return MergeMoviesOutputData("preview", snapshots)
        moved = tuple(
            row["id"] for row in screenings if row["movie_id"] != request.survivor_id
        )
        await conn.execute(
            f"UPDATE {self._screenings} SET movie_id = $1 "
            "WHERE movie_id = ANY($2::text[])",
            request.survivor_id,
            list(request.duplicate_ids),
        )
        await conn.execute(
            f"DELETE FROM {self._movies} WHERE id = ANY($1::text[])",
            list(request.duplicate_ids),
        )
        return MergeMoviesOutputData("applied", snapshots, moved)

    def _is_retry(
        self, request: MergeMoviesInputData, current: tuple[MovieMetadataSnapshot, ...]
    ) -> bool:
        if len(current) != 1 or current[0].movie_id != request.survivor_id:
            return False
        try:
            approved = request.approved_snapshot or ()
            if len(approved) != len(request.duplicate_ids) + 1:
                return False
            movie = None
            rows = []
            for snap in approved:
                original, screenings, survivor, duplicates, owners = json.loads(
                    snap.revision
                )
                if not isinstance(original, dict) or not isinstance(screenings, list):
                    return False
                if any(not isinstance(row, dict) for row in screenings):
                    return False
                if survivor != request.survivor_id or duplicates != sorted(
                    request.duplicate_ids
                ):
                    return False
                if _snapshot(original, screenings, (), request, owners) != snap:
                    return False
                if snap.movie_id == request.survivor_id:
                    movie = original
                rows.extend(
                    dict(row, movie_id=request.survivor_id) for row in screenings
                )
            rows.sort(key=lambda row: row["id"])
            return (
                movie is not None
                and _snapshot(movie, rows, (), request, owners) == current[0]
            )
        except (ValueError, TypeError, KeyError):
            return False

    async def _references(
        self, conn: asyncpg.Connection, ids: list[str], lock: bool
    ) -> tuple[str, ...]:
        # Inspect every inbound FK, including cascading and cross-schema tables.
        constraints = await conn.fetch(
            """
            SELECT n.nspname, c.relname, k.conname,
                   array_agg(a.attname ORDER BY u.ordinality) AS columns,
                   array_agg(b.attname ORDER BY u.ordinality) AS targets
            FROM pg_constraint k
            JOIN pg_class c ON c.oid = k.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            CROSS JOIN LATERAL unnest(k.conkey, k.confkey)
                WITH ORDINALITY u(src, dst, ordinality)
            JOIN pg_attribute a ON a.attrelid = k.conrelid AND a.attnum = u.src
            JOIN pg_attribute b ON b.attrelid = k.confrelid AND b.attnum = u.dst
            WHERE k.contype = 'f' AND k.confrelid = $1::regclass
            GROUP BY n.nspname, c.relname, k.conname
            ORDER BY n.nspname, c.relname, k.conname
        """,
            self._movies,
        )
        refs = []
        for fk in constraints:
            if (fk["nspname"], fk["relname"], fk["columns"], fk["targets"]) == (
                self._schema,
                "screenings",
                ["movie_id"],
                ["id"],
            ):
                continue
            table = f"{_quote(fk['nspname'])}.{_quote(fk['relname'])}"
            if lock:
                await conn.execute(f"LOCK TABLE {table} IN SHARE MODE")
            if fk["targets"] != ["id"]:
                refs.append(f"Unsupported reference {table}.{fk['conname']}")
                continue
            count = await conn.fetchval(
                f"SELECT count(*) FROM {table} "
                f"WHERE {_quote(fk['columns'][0])} = ANY($1::text[])",
                ids,
            )
            if count:
                refs.append(f"Unresolved reference {table}.{fk['conname']}: {count}")
        return tuple(refs)
