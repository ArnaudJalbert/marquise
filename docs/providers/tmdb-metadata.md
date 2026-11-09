# TMDB metadata retrieval

Issue #350 consumes the application-owned contracts from #358. Parent #349 owns
policy. Imports, refresh and merge use this path; the older TmdbSearchAdapter and
TmdbSource are unreferenced (#457).

Construct TmdbMetadataHttpSource with a key and inject it into TmdbMetadataAdapter.
The adapter implements MetadataRepository; neither class selects a match or
replaces persisted movie fields. `infrastructure/di/import_use_cases.py` builds both.

## Retrieval and completeness

The HTTP source retrieves all search pages in provider order. Page/count drift,
malformed envelopes, and failed pages produce incomplete batches, retaining prior
rows. The adapter hydrates each movie candidate in that order with detail,
alternative titles, translations, images, credits, people, videos and release
certifications. Person search hydrates all returned people without choosing one.
Directed discovery uses only crew entries whose TMDB job is Director, retaining
credit order. Movie candidate deduplication and discovery sequencing remain the
use case's responsibility.

A failed detail section retains facts mapped before it and stops that detail
retrieval. Other candidate details are still inspected. A missing detail is a
not_found failure, never a complete empty result. Missing optional values remain
None or empty tuples; zero runtime is preserved for use cases to assess.
HTTP 429 and server/network failures are retryable facts; transport performs no
retry. Credentials and provider error bodies never appear in failure messages or
exception contexts. Redirects are rejected so keys cannot be forwarded.

Every invalid_data failure names the check that rejected the response in its
`reason`, a stable name from a fixed list: `pagination`, `malformed_json`,
`endpoint_check` or `detail_mapping`. When the record is known, the failure's
`identity` carries its TMDB ID and the message ends with it, such as
`Invalid TMDB response: detail_mapping for tmdb 42`. Messages never contain the
endpoint path, the URL, the API key or the response body.

## Locale and media provenance

Canonical detail is requested as en-US. Translation title and synopsis come only
from the translation row carrying that locale. A blank fr-CA translation stays
blank, even when TMDB detail has an English or original-language fallback value.
All translation locales remain visible as facts; there is no fr-FR fallback.

Images have language-level provenance, not a country. Each poster is a separate
LocalizedMovieMetadata item tagged with its reported language, such as fr or en;
language-neutral images use und. No poster is silently promoted to fr-CA or
chosen ahead of another. Consumers must consider language-level poster facts
separately from territory-level text when selecting a patch in #353/#355.

Videos are requested for English, the original language, and each translation
locale, including locales with blank text. Results are joined in that request
order, retaining first occurrence of each provider video ID. YouTube and Vimeo
URLs are resolved; an unsupported host reports invalid_data rather than inventing
a URL. Trailer, teaser and other videos retain language and official flags.
Certifications retain country and release-entry order without choosing Canada.
Cast names come from person-labelled cast credits; verified director and searched
person aliases come from that person's detail, never a spelling heuristic.

## Provider references

- [Movie translations](https://developer.themoviedb.org/reference/movie-translations)
- [Movie images](https://developer.themoviedb.org/reference/movie-images)
- [Movie videos](https://developer.themoviedb.org/reference/movie-videos)
- [Person movie credits](https://developer.themoviedb.org/reference/person-movie-credits)

Synthetic response fixtures and fake-transport tests cover these boundaries.
No live-provider accuracy or production data change is implied by those tests.
