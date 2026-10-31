"""Validate targeted duplicate merges using the shared matching policy."""

from dataclasses import replace

from marquise.application.metadata import ProviderIdentity
from marquise.application.movie_workflows import (
    MatchMovieExecutor,
    MatchMovieInputData,
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MovieMetadataRepository,
    MovieMetadataSnapshot,
)


class MergeMoviesUseCase:
    """Keep eligibility in application and atomic state checks in persistence."""

    def __init__(
        self, repository: MovieMetadataRepository, matcher: MatchMovieExecutor
    ) -> None:
        self._repository = repository
        self._matcher = matcher

    async def execute(self, input_data: MergeMoviesInputData) -> MergeMoviesOutputData:
        """Preview without writes or apply exactly the approved evidence."""
        preview = await self._repository.merge(
            MergeMoviesInputData(input_data.survivor_id, input_data.duplicate_ids)
        )
        snapshots = input_data.approved_snapshot or preview.snapshots
        blockers, identity = await self._validate(input_data, snapshots)
        if input_data.approved_snapshot is not None and (
            input_data.approved_identity is None
            or input_data.approved_identity != identity
        ):
            blockers.append("Approved identity is missing or changed")
        if blockers:
            return MergeMoviesOutputData("blocked", snapshots, blockers=tuple(blockers))
        if input_data.approved_snapshot is None:
            return replace(preview, confirmed_identity=identity)
        # Persistence also recognizes an exact unchanged post-state on retry.
        return await self._repository.merge(input_data)

    async def _validate(
        self,
        request: MergeMoviesInputData,
        snapshots: tuple[MovieMetadataSnapshot, ...],
    ) -> tuple[list[str], ProviderIdentity | None]:
        ids = (request.survivor_id, *request.duplicate_ids)
        if len(snapshots) != len(ids) or {s.movie_id for s in snapshots} != set(ids):
            return ["Snapshots must cover each target exactly once"], None
        blockers = []
        identities = []
        for snapshot in snapshots:
            if snapshot.unresolved_references:
                blockers.append(f"Unresolved references: {snapshot.movie_id}")
            stored_id = snapshot.tmdb_id.strip() if snapshot.tmdb_id else ""
            if stored_id and snapshot.movie_id != request.survivor_id:
                blockers.append(f"Keep existing TMDB owner: {snapshot.movie_id}")
            values = snapshot.values
            if not values.title:
                blockers.append(f"Missing identity evidence: {snapshot.movie_id}")
                continue
            match = await self._matcher.execute(
                MatchMovieInputData(
                    values.title,
                    values.release_year,
                    values.directors or (),
                    values.duration_minutes,
                )
            )
            if match.status != "matched" or match.identity is None:
                blockers.append(f"Unconfirmed identity: {snapshot.movie_id}")
                continue
            identities.append(match.identity)
            if stored_id and (
                match.identity.provider != "tmdb" or match.identity.id != stored_id
            ):
                blockers.append(f"Conflicting known identity: {snapshot.movie_id}")
        if len(set(identities)) > 1:
            blockers.append("Targets do not share one confirmed identity")
        if identities and identities[0].provider == "tmdb":
            owner = await self._repository.find_by_tmdb_id(identities[0].id)
            if owner is not None and owner.movie_id != request.survivor_id:
                blockers.append(f"Keep existing TMDB owner: {owner.movie_id}")
        return blockers, identities[0] if identities else None
