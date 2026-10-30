"""Map a TMDB response to movie identity candidates."""

from __future__ import annotations

from marquise.application.repositories.movie_identity_search import (
    MovieIdentityCandidate,
    MovieIdentitySearch,
)
from marquise.interface_adapters.repositories.protocols.movie_search_source import (
    MovieSearchError,
    MovieSearchSource,
)


class TmdbSearchAdapter(MovieIdentitySearch):
    """Translate an injected TMDB source into provider-labelled candidates."""

    def __init__(self, source: MovieSearchSource) -> None:
        self._source = source

    async def search(
        self, title: str, year: int | None
    ) -> list[MovieIdentityCandidate]:
        """Return TMDB candidates without treating an incomplete page as a match."""
        data = await self._source.search(title, year)
        try:
            results = data["results"]
            if data["total_results"] > len(results) and len(results) == 1:
                raise MovieSearchError("incomplete TMDB search results")
            return [
                MovieIdentityCandidate(
                    provider="tmdb",
                    id=str(row["id"]),
                    title=row["title"],
                    release_year=int(row["release_date"][:4])
                    if row.get("release_date")
                    else None,
                )
                for row in results
            ]
        except MovieSearchError:
            raise
        except (ValueError, KeyError, TypeError):
            raise MovieSearchError("invalid TMDB search results") from None
