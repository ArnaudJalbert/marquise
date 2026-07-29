"""Response DTOs for the screening import workflow.

The import workflow is orchestrated by the controller
(``infrastructure/controllers/source_controller.py``), which sequences the
``FetchShowtimesFromSourceQuery``, ``EnsureMoviesExistCommand``, and
``UpsertScreeningsCommand`` use cases. These dataclasses are the shared response
contract that workflow returns to the delivery layer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportedScreeningData:
    """Summary of a single imported or already-existing screening.

    Attributes:
        movie_title: The title of the movie.
        showtime: The showtime in ISO format.
        imported: True if newly created, False if already existed and updated in place.
    """

    movie_title: str
    showtime: str
    imported: bool

    def __post_init__(self) -> None:
        if not self.movie_title.strip():
            raise ValueError("movie_title must not be empty")
        if not self.showtime.strip():
            raise ValueError("showtime must not be empty")


@dataclass(frozen=True, slots=True)
class ImportScreeningsSummary:
    """Summary returned after importing a cinema's screenings.

    Attributes:
        cinema_id: The ID of the cinema.
        cinema_name: The display name of the cinema.
        source_name: The name of the source used.
        screenings: List of imported/existing screening summaries.
        total_count: Total number of screenings processed.
        imported_count: Number of new screenings created.
        updated_count: Number of existing screenings found and updated in place.
        skipped_count: Number of screenings skipped because their external_id
            collided with a different existing screening.
    """

    cinema_id: str
    cinema_name: str
    source_name: str
    screenings: tuple[ImportedScreeningData, ...]
    total_count: int
    imported_count: int
    updated_count: int
    skipped_count: int = 0

    def __post_init__(self) -> None:
        if self.total_count < 0:
            raise ValueError("total_count must not be negative")
        if self.imported_count < 0:
            raise ValueError("imported_count must not be negative")
        if self.updated_count < 0:
            raise ValueError("updated_count must not be negative")
        if self.skipped_count < 0:
            raise ValueError("skipped_count must not be negative")
