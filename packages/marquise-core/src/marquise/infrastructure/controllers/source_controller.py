"""Controller for source management operations."""

from __future__ import annotations

from datetime import date

from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import (
    CreateScreeningsCommand,
    ImportScreeningsSummary,
)
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.infrastructure.controllers.auth_controller import AuthController


class SourceController:
    """Handles source creation, listing, deletion, and assignment flows.

    All dependencies are injected — no settings, database, or use case wiring
    lives here.
    """

    def __init__(
        self,
        auth_controller: AuthController,
        create_source_use_case: CreateSourceUseCase,
        list_sources_use_case: ListSourcesUseCase,
        delete_source_use_case: DeleteSourceUseCase,
        assign_source_use_case: AssignSourceUseCase,
        unassign_source_use_case: UnassignSourceUseCase,
        get_cinema_source_use_case: GetCinemaSourceUseCase,
        list_registry_sources_use_case: ListRegistrySourcesUseCase,
        fetch_screenings_use_case: FetchScreeningsFromSourceQuery,
        create_movies_use_case: CreateMissingMoviesCommand,
        create_screenings_use_case: CreateScreeningsCommand,
    ) -> None:
        self._auth = auth_controller
        self._create_use_case = create_source_use_case
        self._list_use_case = list_sources_use_case
        self._delete_use_case = delete_source_use_case
        self._assign_use_case = assign_source_use_case
        self._unassign_use_case = unassign_source_use_case
        self._get_source_use_case = get_cinema_source_use_case
        self._list_registry_use_case = list_registry_sources_use_case
        self._fetch_screenings_use_case = fetch_screenings_use_case
        self._create_movies_use_case = create_movies_use_case
        self._create_screenings_use_case = create_screenings_use_case

    async def create_source(
        self,
        name: str,
        display_name: str,
        description: str | None = None,
    ) -> CreateSourceUseCase.OutputData:
        """Register a new showtime source.

        Args:
            name: Unique machine name.
            display_name: Human-readable label.
            description: Optional longer description.

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
            SourceAlreadyExistsError: If a source with that name already exists.
        """
        self._auth.validate_admin()

        request = CreateSourceUseCase.InputData(
            name=name,
            display_name=display_name,
            description=description,
        )
        return await self._create_use_case.execute(request)

    async def list_sources(self) -> ListSourcesUseCase.OutputData:
        """List all registered showtime sources.

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
        """
        self._auth.validate_admin()

        request = ListSourcesUseCase.InputData()
        return await self._list_use_case.execute(request)

    async def delete_source(self, source_name: str) -> DeleteSourceUseCase.OutputData:
        """Delete a registered showtime source.

        Args:
            source_name: The machine name of the source to delete.

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
            SourceNotFoundError: If no source with the given name exists.
        """
        self._auth.validate_admin()

        request = DeleteSourceUseCase.InputData(source_name=source_name)
        return await self._delete_use_case.execute(request)

    async def assign_source(
        self,
        cinema_id: str,
        source_name: str,
    ) -> AssignSourceUseCase.OutputData:
        """Assign a source to a cinema.

        Args:
            cinema_id: The ID of the cinema.
            source_name: The machine name of the source.

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
            CinemaNotFoundError: If the cinema does not exist.
            SourceNotFoundError: If the source does not exist.
            CinemaSourceAssignmentAlreadyExistsError: If already assigned.
        """
        self._auth.validate_admin()

        request = AssignSourceUseCase.InputData(
            cinema_id=cinema_id,
            source_name=source_name,
        )
        return await self._assign_use_case.execute(request)

    async def unassign_source(
        self,
        cinema_id: str,
    ) -> UnassignSourceUseCase.OutputData:
        """Remove the source assignment from a cinema.

        Args:
            cinema_id: The ID of the cinema.

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
            CinemaSourceAssignmentNotFoundError: If no assignment exists.
        """
        self._auth.validate_admin()

        request = UnassignSourceUseCase.InputData(cinema_id=cinema_id)
        return await self._unassign_use_case.execute(request)

    async def get_cinema_source(
        self,
        cinema_id: str,
    ) -> GetCinemaSourceUseCase.OutputData:
        """Get the source assigned to a cinema.

        Public operation — no authentication required.

        Args:
            cinema_id: The ID of the cinema.

        Returns:
            The output data with the assigned source details.

        Raises:
            CinemaSourceAssignmentNotFoundError: If no assignment exists.
        """
        request = GetCinemaSourceUseCase.InputData(cinema_id=cinema_id)
        return await self._get_source_use_case.execute(request)

    @property
    def auth_controller(self) -> AuthController:
        """Expose the auth controller for use by callers (e.g. CLI)."""
        return self._auth

    async def list_registry_sources(
        self,
    ) -> ListRegistrySourcesUseCase.OutputData:
        """List showtime sources available in the code-level registry.

        Public operation — no authentication required.  Each entry includes
        auto-discovered ``fetch_showtimes`` parameter definitions.

        Returns:
            The output data with registry source entries.
        """
        request = ListRegistrySourcesUseCase.InputData()
        return await self._list_registry_use_case.execute(request)

    async def import_screenings(
        self,
        cinema_id: str,
        start_date: date,
        end_date: date,
    ) -> ImportScreeningsSummary:
        """Import screenings from a cinema's showtime source.

        Sequences the three focused use cases that make up the import
        workflow: fetch the cinema's raw showtimes, ensure every movie
        exists (creating and enriching as needed), then upsert the
        screenings. The counts and skip-on-collision handling live inside
        ``UpsertScreeningsCommand``; this method only wires their outputs
        into the response summary.

        Args:
            cinema_id: The ID of the cinema.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            The import summary.

        Raises:
            ValueError: If the caller is not authenticated as admin.
            CinemaNotFoundError: If the cinema does not exist.
            CinemaSourceAssignmentNotFoundError: If no source assigned.
        """
        self._auth.validate_admin()

        fetched = await self._fetch_screenings_use_case.execute(
            FetchScreeningsFromSourceQuery.InputData(
                cinema_id=cinema_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

        movies = await self._create_movies_use_case.execute(
            CreateMissingMoviesCommand.InputData(
                movies=tuple(
                    CreateMissingMoviesCommand.MovieInput(
                        title=m.title,
                        description=m.description,
                        directors=m.directors,
                        cast=m.cast,
                        duration_minutes=m.duration_minutes,
                        release_year=m.release_year,
                        poster_url=m.poster_url,
                        trailer_url=m.trailer_url,
                        genres=m.genres,
                        original_title=m.original_title,
                        rating=m.rating,
                        origin_countries=m.origin_countries,
                    )
                    for m in fetched.movies
                )
            )
        )

        title_to_id = movies.movie_lookup
        screening_inputs = [
            CreateScreeningsCommand.ScreeningInput(
                movie_id=title_to_id[_normalize_title(s.movie_title)],
                movie_title=s.movie_title,
                cinema_id=fetched.cinema_id,
                cinema_name=fetched.cinema_name,
                showtime=s.showtime,
                external_id=s.external_id,
                ticket_url=s.ticket_url,
                room=s.room,
                language=s.language,
            )
            for s in fetched.screenings
        ]

        screenings = await self._create_screenings_use_case.execute(
            CreateScreeningsCommand.InputData(
                screenings=tuple(screening_inputs),
            )
        )

        return ImportScreeningsSummary(
            cinema_id=fetched.cinema_id,
            cinema_name=fetched.cinema_name,
            source_name=fetched.source_name,
            screenings=screenings.screenings,
            total_count=screenings.total_count,
            imported_count=screenings.imported_count,
            updated_count=screenings.updated_count,
            skipped_count=screenings.skipped_count,
        )


def _normalize_title(title: str) -> str:
    """Strip and collapse internal whitespace in a scraped movie title."""
    return " ".join(title.strip().split())
