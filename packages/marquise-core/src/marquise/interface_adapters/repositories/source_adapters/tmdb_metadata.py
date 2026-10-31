"""Translate TMDB JSON into ordered, unselected metadata facts."""

from dataclasses import replace
from datetime import date
from typing import Literal
from urllib.parse import quote

from marquise.application.metadata import (
    LocalizedMovieMetadata,
    MetadataBatch,
    MetadataFailure,
    MetadataMovie,
    MetadataRepository,
    MovieCertification,
    MovieMedia,
    PersonFact,
    ProviderIdentity,
    TitleFact,
)
from marquise.interface_adapters.repositories.protocols.tmdb_metadata_source import (
    TmdbMetadataError,
    TmdbMetadataSource,
)


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid text")
    return value if value.strip() else None


def _rows(data: dict, key: str) -> list[dict]:
    value = data[key]
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError("invalid rows")
    return value


def _id(value: int) -> ProviderIdentity:
    if type(value) is not int or value <= 0:
        raise ValueError("invalid identity")
    return ProviderIdentity("tmdb", str(value))


def _path(identity: ProviderIdentity, resource: str) -> str:
    if (
        identity.provider != "tmdb"
        or not identity.id.isascii()
        or (not identity.id.isdecimal() or int(identity.id) <= 0)
    ):
        raise ValueError("invalid TMDB identity")
    return f"{resource}/{identity.id}"


def _base(row: dict) -> MetadataMovie:
    title = _text(row["title"])
    if title is None:
        raise ValueError("missing title")
    original = _text(row.get("original_title"))
    language = _text(row.get("original_language"))
    titles = [TitleFact(title, "canonical", "en-US")]
    if original:
        titles.append(TitleFact(original, "original", language))
    released = _text(row.get("release_date"))
    runtime = row.get("runtime")
    if runtime is not None and (type(runtime) is not int or runtime < 0):
        raise ValueError("invalid runtime")
    return MetadataMovie(
        identity=_id(row["id"]),
        titles=tuple(titles),
        release_year=date.fromisoformat(released).year if released else None,
        duration_minutes=runtime,
        original_title=original,
    )


def _invalid() -> MetadataFailure:
    return MetadataFailure("invalid_data", "Invalid TMDB metadata")


class TmdbMetadataAdapter(MetadataRepository):
    """Map facts through an injected source without choosing matches or fields."""

    def __init__(self, source: TmdbMetadataSource) -> None:
        self._source = source

    async def search_movies(
        self, title: str, year: int | None = None
    ) -> MetadataBatch[MetadataMovie]:
        """Return ordered candidate facts without fetching full movie details."""
        params = {"query": title, "language": "en-US"}
        if year is not None:
            params["primary_release_year"] = str(year)
        batch = await self._source.pages("search/movie", params)
        return self._movie_summaries(batch)

    async def search_people(self, name: str) -> MetadataBatch[PersonFact]:
        """Return every person with aliases from that person's detail record."""
        batch = await self._source.pages("search/person", {"query": name})
        people: list[PersonFact] = []
        failure = batch.failure
        for row in batch.items:
            try:
                people.append(await self._person(row))
            except TmdbMetadataError as error:
                failure = failure or error.failure
            except (KeyError, TypeError, ValueError, AttributeError):
                failure = failure or _invalid()
        return MetadataBatch(tuple(people), batch.complete and failure is None, failure)

    async def directed_movies(
        self, person: ProviderIdentity
    ) -> MetadataBatch[MetadataMovie]:
        """Retrieve Director crew credits without resolving person ambiguity."""
        try:
            data = await self._source.get(_path(person, "person") + "/movie_credits")
            rows = _rows(data, "crew")
            directed = tuple(row for row in rows if row["job"] == "Director")
        except TmdbMetadataError as error:
            return MetadataBatch((), False, error.failure)
        except (KeyError, TypeError, ValueError, AttributeError):
            return MetadataBatch((), False, _invalid())
        return self._movie_summaries(MetadataBatch(directed))

    @staticmethod
    def _movie_summaries(
        batch: MetadataBatch[dict],
    ) -> MetadataBatch[MetadataMovie]:
        """Map search and credit rows without hydrating enrichment fields."""
        movies: list[MetadataMovie] = []
        failure = batch.failure
        for row in batch.items:
            try:
                movies.append(_base(row))
            except (KeyError, TypeError, ValueError, AttributeError):
                failure = failure or _invalid()
        return MetadataBatch(tuple(movies), batch.complete and failure is None, failure)

    async def _person(self, row: dict) -> PersonFact:
        identity = _id(row["id"])
        data = await self._source.get(_path(identity, "person"))
        if _id(data["id"]) != identity:
            raise ValueError("person identity mismatch")
        name = _text(data["name"])
        aliases = data["also_known_as"]
        if name is None or not isinstance(aliases, list):
            raise ValueError("invalid person")
        verified: list[str] = []
        for alias in aliases:
            if text := _text(alias):
                verified.append(text)
        return PersonFact(identity, name, tuple(verified))

    async def movie_details(
        self, identity: ProviderIdentity
    ) -> MetadataBatch[MetadataMovie]:
        """Return one movie with explicitly incomplete facts on a partial failure."""
        movie: MetadataMovie | None = None
        try:
            path = _path(identity, "movie")
            data = await self._source.get(path, {"language": "en-US"})
            movie = _base(data)
            if movie.identity != identity:
                movie = None
                raise ValueError("movie identity mismatch")
            movie = replace(
                movie,
                genres=tuple(
                    row["name"] for row in _rows(data, "genres") if _text(row["name"])
                ),
                origin_countries=tuple(
                    row["iso_3166_1"]
                    for row in _rows(data, "production_countries")
                    if _text(row["iso_3166_1"])
                ),
            )
            alternative = await self._source.get(path + "/alternative_titles")
            titles = list(movie.titles)
            for row in _rows(alternative, "titles"):
                title = _text(row["title"])
                if title:
                    titles.append(
                        TitleFact(title, "alternative", _text(row.get("iso_3166_1")))
                    )
            movie = replace(movie, titles=tuple(titles))
            translations = await self._source.get(path + "/translations")
            localized: list[LocalizedMovieMetadata] = []
            video_languages = ["en-US"]
            original_language = _text(data.get("original_language"))
            if original_language:
                video_languages.append(original_language)
            for row in _rows(translations, "translations"):
                language = _text(row["iso_639_1"])
                country = _text(row["iso_3166_1"])
                if not language:
                    raise ValueError("missing translation language")
                locale = f"{language}-{country}" if country else language
                video_languages.append(locale)
                text = row["data"]
                title = _text(text.get("title"))
                synopsis = _text(text.get("overview"))
                if title:
                    titles.append(TitleFact(title, "translation", locale))
                localized.append(LocalizedMovieMetadata(locale, title, synopsis))
            movie = replace(movie, titles=tuple(titles), localized=tuple(localized))
            # Images carry a language, not a territory. Keep that provenance instead
            # of labelling TMDB's fallback poster as a French Canadian poster.
            images = await self._source.get(path + "/images")
            for row in _rows(images, "posters"):
                language = _text(row["iso_639_1"])
                image = _text(row["file_path"])
                if image:
                    localized.append(
                        LocalizedMovieMetadata(
                            language or "und",
                            poster_url="https://image.tmdb.org/t/p/original"
                            + quote(image, safe="/"),
                        )
                    )
            movie = replace(movie, localized=tuple(localized))
            credits = await self._source.get(path + "/credits")
            directors = tuple(
                [
                    await self._person(row)
                    for row in _rows(credits, "crew")
                    if row["job"] == "Director"
                ]
            )
            movie = replace(movie, directors=directors)
            cast = tuple(self._cast_member(row) for row in _rows(credits, "cast"))
            movie = replace(movie, cast=cast)
            # TMDB defaults videos to English. Request each translated language so
            # French media cannot disappear behind that transport default.
            languages = dict.fromkeys(video_languages)
            media: list[MovieMedia] = []
            seen: set[str] = set()
            for language in languages:
                videos = await self._source.get(
                    path + "/videos", {"language": language}
                )
                for row in _rows(videos, "results"):
                    video_id = str(row["id"])
                    if video_id not in seen:
                        media.append(self._media(row))
                        seen.add(video_id)
                movie = replace(movie, media=tuple(media))
            releases = await self._source.get(path + "/release_dates")
            certifications: list[MovieCertification] = []
            for row in _rows(releases, "results"):
                country = _text(row["iso_3166_1"])
                if not country:
                    raise ValueError("missing certification country")
                for release in _rows(row, "release_dates"):
                    rating = _text(release["certification"])
                    if rating:
                        certifications.append(MovieCertification(country, rating))
            movie = replace(movie, certifications=tuple(certifications))
            return MetadataBatch((movie,))
        except TmdbMetadataError as error:
            failure = error.failure
        except (KeyError, TypeError, ValueError, AttributeError):
            failure = _invalid()
        return MetadataBatch((movie,) if movie else (), False, failure)

    @staticmethod
    def _cast_member(row: dict) -> PersonFact:
        name = _text(row["name"])
        if name is None:
            raise ValueError("missing cast name")
        return PersonFact(_id(row["id"]), name)

    @staticmethod
    def _media(row: dict) -> MovieMedia:
        site = row["site"]
        key = _text(row["key"])
        if not key or type(row["official"]) is not bool:
            raise ValueError("invalid video")
        if site == "YouTube":
            url = "https://www.youtube.com/watch?v=" + quote(key, safe="")
        elif site == "Vimeo":
            url = "https://vimeo.com/" + quote(key, safe="")
        else:
            raise ValueError("unsupported video host")
        kind: Literal["trailer", "teaser", "other"] = (
            "trailer"
            if row["type"] == "Trailer"
            else "teaser"
            if row["type"] == "Teaser"
            else "other"
        )
        return MovieMedia(url, _text(row["iso_639_1"]), kind, row["official"])
