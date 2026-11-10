# Metadata workflow contracts

Issue #358 defines the shared seam for parent #349. Imports, movie refresh and
movie merge use these contracts: `infrastructure/di/import_use_cases.py` wires
TmdbMetadataAdapter, `MarquiseFactory` exposes `refresh_movies_use_case` and
`merge_movies_use_case`, and the CLI runs `movie refresh`, `movie merge-preview`
and `movie merge-apply`.

## Ownership and signatures

- `marquise.application.metadata` owns MetadataRepository and immutable facts.
  `search_movies(title, year=None)`, `search_people(name)`,
  `directed_movies(person)` and `movie_details(identity)` are async and return
  MetadataBatch. Adapters retrieve all relevant pages internally, preserve
  provider order and report incomplete retrieval. Details contain zero or one
  movie. Missing detail is an incomplete batch with a not_found failure.
- `marquise.application.movie_workflows` owns workflow InputData/OutputData at
  module level. These are allowlisted exceptions in
  `test_use_case_architecture.py`; new use cases nest their own DTOs. It also
  owns execution Protocols and the separate MovieMetadataRepository ABC. Every
  executor has async `execute(input_data)`. All names are public facade exports.
- The persistence port uses string movie IDs and immutable snapshots. It supports
  get, explicit TMDB lookup, stable ordered TMDB enumeration, atomic metadata
  patches and guarded merge requests. It does not extend the existing ABC.

ProviderIdentity scopes opaque IDs, including person IDs. Titles include verified
translations. Person aliases belong to the identified person. Tuple order always
preserves provider order. Use cases own discovery sequencing, deduplication,
eligibility, ranking and locale/media/certification selection. There is no
fr-FR fallback or documented-rerelease exception in this contract.

MetadataBatch completeness covers the requested operation, including its pages
and requested facts, not the provider's entire catalogue. Missing optional facts
are empty tuples or None. Unknown/zero runtime remains raw evidence for policy
to assess. Failed pages may retain partial facts but cannot claim completeness.
An empty complete batch is genuine absence. MetadataFailure subclasses distinguish
unavailable, request_refused, rate_limited, not_found and invalid_data. The use
case, not the failure, decides retryability: only outages and rate limits retry.

Match outcomes distinguish matched, unmatched, failed and incomplete. Only matched
carries an identity. No unmatched result authorizes metadata replacement. Source
metadata and the original screening mapping title remain available to callers.
Provider facts never imply permission to assign a non-TMDB ID to tmdb_id.

Movie.tmdb_id means confirmed TMDB identity. Movie.metadata_enriched_at is the
last successful enrichment timestamp, defaulting to None for existing callers.
A failed refresh preserves both existing values and the last successful stamp.
No per-field provenance or generic identity tables are introduced.

MovieMetadataValues is a selected patch, with None meaning preserve. Callers
select usable values before persistence. update_metadata atomically checks the
expected revision, updates stable-ID fields and records successful enrichment.
Stale/conflicting writes raise MovieWorkflowConflictError. Revisions must change
when metadata or references change. Missing get/identity lookup returns None.
Refresh selects one movie or all confirmed TMDB movies and returns ordered
per-movie outcomes. An unlinked or missing explicit target is an application
error, never a successful empty refresh.

MergeMoviesInputData without approved_snapshot is a dry run. Its snapshot must
include the survivor and every duplicate. Apply rechecks the approved state,
all references and screening collisions in one transaction. Preserve the linked
survivor and screening IDs, move all references, then delete unreferenced
movies. A missing/stale/conflicting target or unresolved reference returns blocked
with reasons and no writes. This contract grants no live merge approval.

## Verification

Imports, factory composition and CLI commands use these contracts. Offline tests
can copy the independent autospec examples in
`packages/marquise-core/tests/unit_tests/application/contracts/test_movie_workflows.py`.
No live provider or database is needed to exercise those seams.
