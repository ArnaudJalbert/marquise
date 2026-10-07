"""Screening writes through HTTP, with injected collaborators and no external I/O."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import asdict, fields
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from marquise import (
    ApplicationError,
    AuthenticationError,
    AuthenticationServiceUnavailableError,
    CinemaNotFoundError,
    CreateScreeningUseCase,
    DeleteScreeningUseCase,
    GetCinemaMoviesUseCase,
    GetCinemaScreeningsQuery,
    GetCinemaUseCase,
    GetMovieScreeningsQuery,
    GetMovieUseCase,
    GetScreeningQuery,
    ListCinemasUseCase,
    ListMoviesUseCase,
    MarquiseFactory,
    MovieNotFoundError,
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
    ScreeningIdempotencyConflictError,
    ScreeningNotFoundError,
    ScreeningWriteBusyError,
    SearchScreeningsQuery,
    UpdateScreeningUseCase,
    VerifyAccessTokenQuery,
    WriteScreeningUseCase,
)
from marquise_api.app import CACHE_PREFIX, create_app
from marquise_api.logging_middleware import JsonFormatter

SHOWTIME = datetime.fromisoformat("2026-10-06T19:30:00+00:00")
CREATE = {
    "movie_id": "mov-1",
    "cinema_id": "cin-1",
    "showtime": "2026-10-06T19:30:00Z",
}
PERSISTED = {
    "id": "persisted-id",
    "movie_id": "mov-1",
    "movie_title": "The Odyssey",
    "cinema_id": "cin-1",
    "cinema_name": "Cinema One",
    "showtime": SHOWTIME,
    "ticket_url": "https://tickets.example/saved",
    "room": "Persisted room",
    "language": "V.O.",
}
EXPECTED = {**PERSISTED, "showtime": "2026-10-06T19:30:00Z"}
INTENT_HEADERS = {"Idempotency-Key": "write-1", "X-Change-Reason": "Correct listings"}


@pytest.fixture(autouse=True)
def clear_cache() -> Iterator[None]:
    """Keep the existing process-wide in-memory backend isolated between tests."""
    yield
    asyncio.run(InMemoryBackend().clear(namespace=CACHE_PREFIX))


@pytest.fixture
def factory() -> MagicMock:
    """Provide the approved factory/use-case seam without opening external services."""
    fake = create_autospec(MarquiseFactory, instance=True)
    for name, kind in (
        ("create_screening_use_case", CreateScreeningUseCase),
        ("update_screening_use_case", UpdateScreeningUseCase),
        ("delete_screening_use_case", DeleteScreeningUseCase),
        ("get_screening_query", GetScreeningQuery),
        ("get_cinema_movies_use_case", GetCinemaMoviesUseCase),
        ("get_cinema_screenings_query", GetCinemaScreeningsQuery),
        ("get_cinema_use_case", GetCinemaUseCase),
        ("get_movie_screenings_query", GetMovieScreeningsQuery),
        ("get_movie_use_case", GetMovieUseCase),
        ("list_cinemas_use_case", ListCinemasUseCase),
        ("list_movies_use_case", ListMoviesUseCase),
        ("search_screenings_query", SearchScreeningsQuery),
        ("verify_access_token_query", VerifyAccessTokenQuery),
    ):
        setattr(fake, name, create_autospec(kind, instance=True))
    fake.verify_access_token_query.InputData = VerifyAccessTokenQuery.InputData
    fake.verify_access_token_query.execute.return_value = (
        VerifyAccessTokenQuery.OutputData(
            subject="editor-id", can_edit=True, can_administer=False
        )
    )
    fake.create_screening_use_case.execute.return_value = (
        CreateScreeningUseCase.OutputData(**PERSISTED)
    )
    fake.update_screening_use_case.execute.return_value = (
        UpdateScreeningUseCase.OutputData(**PERSISTED)
    )
    fake.delete_screening_use_case.execute.return_value = (
        DeleteScreeningUseCase.OutputData(screening_id="scr-1")
    )
    fake.get_screening_query.execute.return_value = GetScreeningQuery.OutputData(
        **PERSISTED
    )
    fake.write_screening_use_case = create_autospec(
        WriteScreeningUseCase, instance=True
    )

    async def write(
        request: WriteScreeningUseCase.InputData,
    ) -> WriteScreeningUseCase.OutputData:
        """Keep existing DTO/error regression checks through the new configured seam."""
        mutation = request.mutation
        if isinstance(mutation, CreateScreeningUseCase.InputData):
            output = await fake.create_screening_use_case.execute(mutation)
            return WriteScreeningUseCase.OutputData(
                screening_id=output.id, changed=True, screening=output
            )
        if isinstance(mutation, UpdateScreeningUseCase.InputData):
            output = await fake.update_screening_use_case.execute(mutation)
            changed = any(
                field.name != "screening_id"
                and getattr(mutation, field.name) is not field.default
                for field in fields(mutation)
            )
            return WriteScreeningUseCase.OutputData(
                screening_id=output.id,
                changed=changed,
                screening=CreateScreeningUseCase.OutputData(**asdict(output)),
            )
        output = await fake.delete_screening_use_case.execute(mutation)
        return WriteScreeningUseCase.OutputData(
            screening_id=output.screening_id, changed=True
        )

    fake.write_screening_use_case.execute.side_effect = write
    return fake


@pytest.fixture
def client(factory: MagicMock) -> TestClient:
    """Use actual routing, validation, auth, middleware, and response serialization."""
    return TestClient(create_app(factory=factory), headers=INTENT_HEADERS)


def test_editor_creates_persisted_screening(
    client: TestClient, factory: MagicMock
) -> None:
    """POST accepts all metadata and returns saved data and its canonical Location."""
    response = client.post(
        "/v1/screenings",
        headers={"Authorization": "Bearer editor"},
        json={
            **CREATE,
            "ticket_url": "https://tickets.example/input",
            "room": "Input room",
            "language": "V.F.",
            "external_id": "ext-1",
        },
    )
    assert response.status_code == 201
    assert response.json() == EXPECTED
    assert response.headers["location"] == "/v1/screenings/persisted-id"
    factory.create_screening_use_case.execute.assert_awaited_once_with(
        CreateScreeningUseCase.InputData(
            movie_id="mov-1",
            cinema_id="cin-1",
            showtime=SHOWTIME,
            ticket_url="https://tickets.example/input",
            room="Input room",
            language="V.F.",
            external_id="ext-1",
        )
    )


@pytest.mark.parametrize(
    "fields",
    [
        {"room": "Salle 2"},
        {"ticket_url": None, "room": None, "language": None, "external_id": None},
        {
            "movie_id": "mov-2",
            "cinema_id": "cin-2",
            "showtime": "2026-10-07T20:00:00-04:00",
            "external_id": "ext-2",
        },
        {},
    ],
)
def test_editor_patches_only_supplied_fields(
    client: TestClient,
    factory: MagicMock,
    fields: dict,
) -> None:
    """PATCH forwards identity edits/explicit clears but preserves omitted fields."""
    response = client.patch(
        "/v1/screenings/scr-1",
        json=fields,
        headers={"Authorization": "Bearer editor"},
    )
    assert response.status_code == 200
    assert response.json() == EXPECTED
    expected_fields = fields.copy()
    if "showtime" in expected_fields:
        expected_fields["showtime"] = datetime.fromisoformat(
            expected_fields["showtime"]
        )
    factory.update_screening_use_case.execute.assert_awaited_once_with(
        UpdateScreeningUseCase.InputData(screening_id="scr-1", **expected_fields)
    )


def test_editor_permanently_deletes_screening(
    client: TestClient,
    factory: MagicMock,
) -> None:
    """DELETE delegates permanent deletion/orphan cleanup and returns no body."""
    response = client.delete(
        "/v1/screenings/scr-1",
        headers={"Authorization": "Bearer editor"},
    )
    assert response.status_code == 204
    assert response.content == b""
    factory.delete_screening_use_case.execute.assert_awaited_once_with(
        DeleteScreeningUseCase.InputData(screening_id="scr-1")
    )


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/v1/screenings", {**CREATE, "unknown": "bad"}),
        ("PATCH", "/v1/screenings/scr-1", {"unknown": "bad"}),
        ("PATCH", "/v1/screenings/scr-1", {"movie_id": None}),
        ("PATCH", "/v1/screenings/scr-1", {"showtime": None}),
        ("POST", "/v1/screenings", {**CREATE, "ticket_url": "/tickets"}),
        *[
            ("POST", "/v1/screenings", {k: v for k, v in CREATE.items() if k != field})
            for field in ("movie_id", "cinema_id", "showtime")
        ],
        *[
            (method, path, {**base, field: value})
            for method, path, base in (
                ("POST", "/v1/screenings", CREATE),
                ("PATCH", "/v1/screenings/scr-1", {}),
            )
            for field, value in (
                ("movie_id", None),
                ("cinema_id", None),
                ("showtime", None),
                ("movie_id", ""),
                ("cinema_id", "  "),
                ("movie_id", 42),
                ("showtime", "2026-10-06T19:30:00"),
                ("showtime", "bad"),
                ("ticket_url", " "),
                ("room", ""),
                ("language", "  "),
                ("external_id", "\t"),
                ("room", []),
                ("ticket_url", "ftp://tickets.example/t"),
                ("ticket_url", "mailto:user@example.com"),
                ("ticket_url", "https:///"),
                ("ticket_url", "//tickets.example/t"),
            )
        ],
    ],
)
def test_invalid_input_rejected_before_execution(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict,
) -> None:
    """Invalid bodies receive the standard 422 envelope without executing mutations."""
    response = client.request(
        method, path, json=body, headers={"Authorization": "Bearer editor"}
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_input"
    assert isinstance(response.json()["detail"], str)
    assert response.json()["request_id"] == response.headers["x-request-id"]
    factory.create_screening_use_case.execute.assert_not_awaited()
    factory.update_screening_use_case.execute.assert_not_awaited()
    factory.delete_screening_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "optional",
    [
        {},
        {
            "ticket_url": None,
            "room": None,
            "language": None,
            "external_id": None,
        },
    ],
)
def test_create_optional_omission_and_null(
    client: TestClient,
    factory: MagicMock,
    optional: dict,
) -> None:
    """Omitted and null create metadata both map to no value."""
    response = client.post(
        "/v1/screenings",
        json={**CREATE, **optional},
        headers={"Authorization": "Bearer editor"},
    )
    assert response.status_code == 201
    factory.create_screening_use_case.execute.assert_awaited_once_with(
        CreateScreeningUseCase.InputData(
            movie_id="mov-1", cinema_id="cin-1", showtime=SHOWTIME
        )
    )


@pytest.mark.parametrize("url", ["http://tickets.example/t", "https://tickets.example"])
@pytest.mark.parametrize(
    "method,path,base",
    [
        ("POST", "/v1/screenings", CREATE),
        ("PATCH", "/v1/screenings/scr-1", {}),
    ],
)
def test_ticket_urls_are_validated_without_normalization(
    client: TestClient,
    factory: MagicMock,
    url: str,
    method: str,
    path: str,
    base: dict,
) -> None:
    """Absolute HTTP(S) URLs pass unchanged, without reachability checks."""
    response = client.request(
        method,
        path,
        json={**base, "ticket_url": url},
        headers={"Authorization": "Bearer editor"},
    )
    assert response.status_code in {200, 201}
    use_case = (
        factory.create_screening_use_case
        if method == "POST"
        else factory.update_screening_use_case
    )
    assert use_case.execute.await_args.args[0].ticket_url == url


OPERATIONS = [
    ("POST", "/v1/screenings", CREATE, "create_screening_use_case", 201),
    (
        "PATCH",
        "/v1/screenings/scr-1",
        {"room": "New room"},
        "update_screening_use_case",
        200,
    ),
    ("DELETE", "/v1/screenings/scr-1", None, "delete_screening_use_case", 204),
]


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
@pytest.mark.parametrize("role", ["editor", "administrator"])
def test_canonical_roles_can_mutate_any_screening(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
    role: str,
) -> None:
    """Both canonical roles have identical global write and permanent-delete access."""
    factory.verify_access_token_query.execute.return_value = (
        VerifyAccessTokenQuery.OutputData(
            subject="unrelated-account",
            can_edit=True,
            can_administer=role == "administrator",
        )
    )
    response = client.request(
        method, path, json=body, headers={"Authorization": f"Bearer {role}"}
    )
    assert response.status_code == status
    factory.verify_access_token_query.execute.assert_awaited_once_with(
        VerifyAccessTokenQuery.InputData(token=role)
    )
    getattr(factory, name).execute.assert_awaited_once()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
@pytest.mark.parametrize(
    "token,expected_status,code",
    [
        (None, 401, "authentication_error"),
        ("malformed", 401, "authentication_error"),
        ("invalid-signature", 401, "authentication_error"),
        ("expired", 401, "authentication_error"),
        ("wrong-issuer", 401, "authentication_error"),
        ("wrong-audience", 401, "authentication_error"),
        ("missing-role", 401, "authentication_error"),
        ("member", 403, "authorization_error"),
        ("other-role", 403, "authorization_error"),
        ("unavailable", 503, "service_unavailable"),
        ("unconfigured", 503, "service_unavailable"),
    ],
)
def test_rejected_auth_never_executes_mutations(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
    token: str | None,
    expected_status: int,
    code: str,
) -> None:
    """Credential, role, verifier, and configuration failures prevent mutations."""
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    if token == "malformed":
        headers = {"Authorization": "Basic malformed"}
    elif token in {"member", "other-role"}:
        factory.verify_access_token_query.execute.return_value = (
            VerifyAccessTokenQuery.OutputData(
                subject="reader-id",
                can_edit=False,
                can_administer=False,
            )
        )
    elif token == "unavailable":
        factory.verify_access_token_query.execute.side_effect = (
            AuthenticationServiceUnavailableError("secret")
        )
    elif token == "unconfigured":
        factory.verify_access_token_query = None
    elif token is not None:
        factory.verify_access_token_query.execute.side_effect = AuthenticationError(
            "secret"
        )
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code == expected_status
    assert response.json()["error_code"] == code
    assert response.json()["request_id"] == response.headers["x-request-id"]
    if expected_status == 401:
        assert response.headers["www-authenticate"] == "Bearer"
    assert "secret" not in response.text
    factory.create_screening_use_case.execute.assert_not_awaited()
    factory.update_screening_use_case.execute.assert_not_awaited()
    factory.delete_screening_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS[:2])
@pytest.mark.parametrize(
    "error,expected_status,code",
    [
        (MovieNotFoundError, 404, "not_found"),
        (CinemaNotFoundError, 404, "not_found"),
        (ScreeningAlreadyExistsError, 409, "conflict"),
        (ScreeningExternalIdConflictError, 409, "conflict"),
        (ValueError, 422, "invalid_input"),
    ],
)
def test_mutation_resource_and_collision_errors(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict,
    name: str,
    status: int,
    error: type[ApplicationError] | type[ValueError],
    expected_status: int,
    code: str,
) -> None:
    """Missing parents and both collision kinds retain consistent error contracts."""
    getattr(factory, name).execute.side_effect = error("Rejected mutation")
    response = client.request(
        method, path, json=body, headers={"Authorization": "Bearer editor"}
    )
    assert response.status_code == expected_status
    assert response.json() == {
        "detail": "Rejected mutation",
        "error_code": code,
        "request_id": response.headers["x-request-id"],
    }


@pytest.mark.parametrize(
    "method,body,name",
    [
        ("PATCH", {}, "update_screening_use_case"),
        ("PATCH", {"room": "New"}, "update_screening_use_case"),
        ("DELETE", None, "delete_screening_use_case"),
    ],
)
def test_missing_screening_is_not_success(
    client: TestClient,
    factory: MagicMock,
    method: str,
    body: dict | None,
    name: str,
) -> None:
    """Empty and nonempty PATCH and DELETE return 404 for a missing screening."""
    getattr(factory, name).execute.side_effect = ScreeningNotFoundError(
        "Missing screening"
    )
    response = client.request(
        method,
        "/v1/screenings/missing",
        json=body,
        headers={"Authorization": "Bearer editor"},
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "not_found"


PUBLIC_PATHS = [
    "/v1/screenings",
    "/v1/screenings/persisted-id",
    "/v1/movies",
    "/v1/movies/mov-1",
    "/v1/movies/mov-1/screenings",
    "/v1/cinemas",
    "/v1/cinemas/cin-1",
    "/v1/cinemas/cin-1/screenings",
    "/v1/cinemas/cin-1/movies",
]


def configure_public_reads(factory: MagicMock) -> None:
    """Stub each public reader at the already-approved injected use-case boundary."""
    factory.search_screenings_query.execute.return_value = SimpleNamespace(
        screenings=[],
        total=0,
    )
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    factory.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[], total=0
    )
    factory.get_cinema_use_case.execute.return_value = SimpleNamespace(
        id="cin-1",
        name="Cinema One",
        address=None,
        city=None,
        website=None,
    )
    factory.get_movie_use_case.execute.return_value = SimpleNamespace(
        id="mov-1",
        title="The Odyssey",
        release_year=None,
        directors=None,
        cast=None,
        duration_minutes=None,
        description=None,
        poster_url=None,
        trailer_url=None,
        genres=None,
        original_title=None,
        rating=None,
        origin_countries=None,
    )
    factory.get_cinema_screenings_query.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )
    factory.get_movie_screenings_query.execute.return_value = SimpleNamespace(
        movie_id="mov-1",
        movie_title="The Odyssey",
        screenings=[],
        total=0,
    )
    factory.get_cinema_movies_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        movies=[],
        total=0,
    )


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_committed_writes_refresh_full_public_namespace(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Each write clears every public cache entry, including orphan movie reads."""
    configure_public_reads(factory)
    for public_path in PUBLIC_PATHS:
        assert client.get(public_path).headers["x-fastapi-cache"] == "MISS"
        assert client.get(public_path).headers["x-fastapi-cache"] == "HIT"
    factory.get_screening_query.execute.return_value = GetScreeningQuery.OutputData(
        **{**PERSISTED, "movie_title": "Fresh title"},
    )
    if method == "DELETE":
        factory.get_movie_use_case.execute.side_effect = MovieNotFoundError(
            "Orphan removed"
        )
    response = client.request(
        method, path, json=body, headers={"Authorization": "Bearer editor"}
    )
    assert response.status_code == status
    for public_path in PUBLIC_PATHS:
        fresh = client.get(public_path)
        if method == "DELETE" and public_path == "/v1/movies/mov-1":
            assert fresh.status_code == 404
        else:
            assert fresh.status_code == 200
            assert fresh.headers["x-fastapi-cache"] == "MISS"
        if public_path == "/v1/screenings/persisted-id":
            assert fresh.json()["movie_title"] == "Fresh title"


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_cache_failure_after_commit_keeps_success_and_sanitizes_log(
    client: TestClient,
    factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Postcommit clear failure never retries or rolls back and never logs secrets."""
    assert client.get("/v1/screenings/persisted-id").status_code == 200
    if body is not None:
        body = {**body, "room": "body-secret"}
    backend = FastAPICache.get_backend()
    clear = create_autospec(
        backend.clear, side_effect=RuntimeError("Bearer token-secret body-secret")
    )
    monkeypatch.setattr(backend, "clear", clear)
    response = client.request(
        method,
        path,
        json=body,
        headers={"Authorization": "Bearer token-secret", "X-Request-ID": "trace-257"},
    )
    assert response.status_code == status
    if method == "DELETE":
        assert response.content == b""
    else:
        assert response.json() == EXPECTED
    if method == "POST":
        assert response.headers["Location"] == "/v1/screenings/persisted-id"
    getattr(factory, name).execute.assert_awaited_once()
    clear.assert_awaited_once()
    failure = next(
        record
        for record in caplog.records
        if record.getMessage() == "Public response cache invalidation failed"
    )
    assert failure.method == method
    assert failure.path == (
        "/screenings" if method == "POST" else "/screenings/{screening_id}"
    )
    logs = "\n".join(JsonFormatter().format(record) for record in caplog.records)
    assert "Public response cache invalidation failed" in logs
    assert "trace-257" in logs
    assert "token-secret" not in logs
    assert "body-secret" not in logs
    assert "exc_info" not in logs
    assert "Traceback" not in logs


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_mutation_responses_are_not_cached(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Identical writes execute again and never emit public-cache response headers."""
    for _ in range(2):
        response = client.request(
            method, path, json=body, headers={"Authorization": "Bearer editor"}
        )
        assert response.status_code == status
        assert "x-fastapi-cache" not in response.headers
        assert "cache-control" not in response.headers
        assert "etag" not in response.headers
    assert getattr(factory, name).execute.await_count == 2


@pytest.mark.parametrize(
    "method,path,body,name,status,failure",
    [
        ("PATCH", "/v1/screenings/scr-1", {}, "update_screening_use_case", 200, None),
        *[
            (method, path, body, name, status, failure)
            for method, path, body, name, status in [
                *OPERATIONS,
                ("PATCH", "/v1/screenings/scr-1", {}, "update_screening_use_case", 200),
            ]
            for failure in ("missing", "conflict")
        ],
    ],
)
def test_empty_or_failed_mutations_do_not_clear_cache(
    client: TestClient,
    factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
    failure: str | None,
) -> None:
    """Failed mutations and empty edits leave reads cached."""
    assert (
        client.get("/v1/screenings/persisted-id").headers["x-fastapi-cache"] == "MISS"
    )
    if failure:
        error = (
            ScreeningNotFoundError
            if failure == "missing"
            else ScreeningAlreadyExistsError
        )
        getattr(factory, name).execute.side_effect = error("Rejected")
    backend = FastAPICache.get_backend()
    clear = create_autospec(backend.clear)
    monkeypatch.setattr(backend, "clear", clear)
    response = client.request(
        method, path, json=body, headers={"Authorization": "Bearer editor"}
    )
    assert response.status_code == (
        status if failure is None else 404 if failure == "missing" else 409
    )
    clear.assert_not_awaited()
    assert client.get("/v1/screenings/persisted-id").headers["x-fastapi-cache"] == "HIT"


def test_all_reads_and_probes_remain_public(
    client: TestClient,
    factory: MagicMock,
) -> None:
    """No public GET, health, or readiness request calls authentication."""
    configure_public_reads(factory)
    factory.check_database_health.return_value = True
    for path in [*PUBLIC_PATHS, "/health", "/ready"]:
        assert client.get(path).status_code == 200
    factory.verify_access_token_query.execute.assert_not_awaited()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_writes_obey_configured_per_ip_rate_limit(
    factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Each write consumes one slot; throttled requests skip auth and mutation."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "2/minute")
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "https://editor.example")
    client = TestClient(create_app(factory=factory), headers=INTENT_HEADERS)
    responses = [
        client.request(
            method,
            path,
            json=body,
            headers={
                "Authorization": "Bearer editor",
                "Origin": "https://editor.example",
            },
        )
        for _ in range(3)
    ]
    assert [response.status_code for response in responses] == [status, status, 429]
    for response, remaining in zip(responses[:2], ["1", "0"], strict=True):
        assert response.headers.get_list("x-ratelimit-limit") == ["2"]
        assert response.headers.get_list("x-ratelimit-remaining") == [remaining]
    throttled = responses[-1]
    assert "retry-after" in throttled.headers
    assert throttled.headers["access-control-allow-origin"] == "https://editor.example"
    assert throttled.json()["error_code"] == "rate_limit_exceeded"
    assert isinstance(throttled.json()["detail"], str)
    assert factory.verify_access_token_query.execute.await_count == 2
    assert getattr(factory, name).execute.await_count == 2


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
@pytest.mark.parametrize(
    "failure,rejection",
    [("invalid", 401), ("missing", 401), ("forbidden", 403), ("unavailable", 503)],
)
def test_rejected_authentication_consumes_request_limit(
    factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
    failure: str,
    rejection: int,
) -> None:
    """Rejected auth consumes the limit; later requests never retry verification."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    query = factory.verify_access_token_query
    headers = {"Authorization": "Bearer rejected"}
    if failure == "missing":
        headers = {}
    elif failure == "invalid":
        query.execute.side_effect = AuthenticationError("Invalid token")
    elif failure == "unavailable":
        query.execute.side_effect = AuthenticationServiceUnavailableError("Unavailable")
    else:
        query.execute.return_value = VerifyAccessTokenQuery.OutputData(
            subject="reader-id", can_edit=False, can_administer=False
        )
    client = TestClient(create_app(factory=factory), headers=INTENT_HEADERS)
    responses = [
        client.request(method, path, json=body, headers=headers) for _ in range(3)
    ]
    assert [response.status_code for response in responses] == [rejection, 429, 429]
    if failure == "missing":
        query.execute.assert_not_awaited()
    else:
        query.execute.assert_awaited_once()
    getattr(factory, name).execute.assert_not_awaited()
    # Switching to a valid credential cannot reset this client's exhausted budget.
    query.execute.side_effect = None
    query.execute.return_value = VerifyAccessTokenQuery.OutputData(
        subject="editor-id", can_edit=True, can_administer=False
    )
    query.execute.reset_mock()
    assert (
        client.request(
            method, path, json=body, headers={"Authorization": "Bearer editor"}
        ).status_code
        == 429
    )
    query.execute.assert_not_awaited()
    getattr(factory, name).execute.assert_not_awaited()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_write_rate_limit_is_per_ip_and_keeps_probes_exempt(
    factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """One client's exhausted budget leaves other IPs and public probes usable."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    factory.check_database_health.return_value = True
    app = create_app(factory=factory)
    first = TestClient(app, client=("192.0.2.1", 50000), headers=INTENT_HEADERS)
    second = TestClient(app, client=("192.0.2.2", 50000), headers=INTENT_HEADERS)
    headers = {"Authorization": "Bearer editor"}
    assert first.request(method, path, json=body, headers=headers).status_code == status
    assert first.request(method, path, json=body, headers=headers).status_code == 429
    assert (
        second.request(method, path, json=body, headers=headers).status_code == status
    )
    assert factory.verify_access_token_query.execute.await_count == 2
    assert getattr(factory, name).execute.await_count == 2
    for _ in range(3):
        assert first.get("/health").status_code == 200
        assert first.get("/ready").status_code == 200
    assert factory.verify_access_token_query.execute.await_count == 2


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_allowed_origins_support_bearer_write_preflight(
    factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Only configured origins get mutation and Authorization preflight support."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "https://editor.example")
    client = TestClient(create_app(factory=factory))
    for origin in ["https://editor.example", "https://untrusted.example"]:
        response = client.options(
            path,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        if origin == "https://editor.example":
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
            assert method in response.headers["access-control-allow-methods"]
            assert (
                "authorization"
                in response.headers["access-control-allow-headers"].lower()
            )
        else:
            assert response.status_code == 400
            assert "access-control-allow-origin" not in response.headers
    factory.verify_access_token_query.execute.assert_not_awaited()
    getattr(factory, name).execute.assert_not_awaited()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_openapi_protects_writes_and_documents_contracts(
    client: TestClient,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """OpenAPI publishes bearer security, errors, DTOs, and success contracts."""
    schema = client.get("/openapi.json").json()
    route_path = (
        "/v1/screenings" if method == "POST" else "/v1/screenings/{screening_id}"
    )
    operation = schema["paths"][route_path][method.lower()]
    assert operation["security"] == [{"HTTPBearer": []}]
    errors = {"401", "403", "404", "422", "429", "503"}
    if method != "DELETE":
        errors.add("409")
    assert errors <= operation["responses"].keys()
    for error in errors:
        assert operation["responses"][error]["content"]["application/json"][
            "schema"
        ] == {
            "$ref": "#/components/schemas/ErrorResponse",
        }
    success = operation["responses"][str(status)]
    if method == "DELETE":
        assert "content" not in success
        assert "atomically" in operation["description"]
    else:
        assert success["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ScreeningResponse",
        }
    if method == "POST":
        assert "Location" in success["headers"]
    assert "put" not in schema["paths"]["/v1/screenings/{screening_id}"]
    for public_path in [*PUBLIC_PATHS, "/health", "/ready"]:
        # Substitute known detail IDs to their OpenAPI placeholders.
        openapi_path = (
            public_path.replace("persisted-id", "{screening_id}")
            .replace("mov-1", "{movie_id}")
            .replace("cin-1", "{cinema_id}")
        )
        assert "security" not in schema["paths"][openapi_path]["get"]
    descriptions = schema["info"]["description"].lower()
    for phrase in (
        "editor",
        "administrator",
        "instance-local",
        "best-effort",
        "expiry",
        "uncached",
        "post",
        "patch",
        "delete",
    ):
        assert phrase in descriptions
    request_schemas = schema["components"]["schemas"]
    create = request_schemas["CreateScreeningRequest"]
    update = request_schemas["UpdateScreeningRequest"]
    assert set(create["required"]) == {"movie_id", "cinema_id", "showtime"}
    assert create["additionalProperties"] is False
    assert update["additionalProperties"] is False
    assert not update.get("required")
    for identity in ("movie_id", "cinema_id", "showtime"):
        assert "anyOf" not in update["properties"][identity]
    assert "external_id" not in request_schemas["ScreeningResponse"]["properties"]


@pytest.mark.parametrize(
    "url", ["https:tickets.example", "http:/tickets.example", "http:relative"]
)
@pytest.mark.parametrize(
    "method,path,base",
    [
        ("POST", "/v1/screenings", CREATE),
        ("PATCH", "/v1/screenings/scr-1", {}),
    ],
)
def test_ticket_url_requires_an_absolute_source_value(
    client: TestClient,
    factory: MagicMock,
    url: str,
    method: str,
    path: str,
    base: dict,
) -> None:
    """Parser repairs must not turn relative inputs into absolute URLs."""
    response = client.request(
        method,
        path,
        json={**base, "ticket_url": url},
        headers={"Authorization": "Bearer editor"},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_input"
    factory.create_screening_use_case.execute.assert_not_awaited()
    factory.update_screening_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("content", ["{", "null", "[]"])
def test_malformed_or_nonobject_bodies_use_standard_error(
    client: TestClient,
    factory: MagicMock,
    method: str,
    content: str,
) -> None:
    """Malformed JSON and non-object bodies fail without executing writes."""
    path = "/v1/screenings" if method == "POST" else "/v1/screenings/scr-1"
    response = client.request(
        method,
        path,
        content=content,
        headers={
            "Authorization": "Bearer editor",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_input"
    factory.create_screening_use_case.execute.assert_not_awaited()
    factory.update_screening_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("method,body", [("PATCH", {}), ("DELETE", None)])
def test_blank_screening_path_is_invalid(
    client: TestClient,
    factory: MagicMock,
    method: str,
    body: dict | None,
) -> None:
    """Blank path identifiers are rejected before mutation execution."""
    response = client.request(
        method,
        "/v1/screenings/%20",
        json=body,
        headers={"Authorization": "Bearer editor"},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_input"
    factory.update_screening_use_case.execute.assert_not_awaited()
    factory.delete_screening_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_cors_default_stays_disabled_for_writes(
    factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Mutation preflight grants no origins unless explicitly configured."""
    monkeypatch.delenv("MARQUISE_API_CORS_ORIGINS", raising=False)
    client = TestClient(create_app(factory=factory))
    response = client.options(
        path,
        headers={
            "Origin": "https://editor.example",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert "access-control-allow-origin" not in response.headers
    getattr(factory, name).execute.assert_not_awaited()


def test_put_is_not_a_supported_replacement(
    client: TestClient,
    factory: MagicMock,
) -> None:
    """PUT stays unsupported rather than introducing a replacement contract."""
    response = client.put(
        "/v1/screenings/scr-1", json=CREATE, headers={"Authorization": "Bearer editor"}
    )
    assert response.status_code == 405
    assert response.json()["error_code"] == "method_not_allowed"
    factory.create_screening_use_case.execute.assert_not_awaited()
    factory.update_screening_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("header", ["Idempotency-Key", "X-Change-Reason"])
@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_write_headers_are_mandatory(
    client: TestClient,
    factory: MagicMock,
    header: str,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """A verified Editor cannot write without both intent headers."""
    headers = {
        "Authorization": "Bearer editor",
        "Idempotency-Key": "write-1",
        "X-Change-Reason": "Publish",
    }
    headers.pop(header)
    client.headers.pop(header, None)
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code == 422
    factory.write_screening_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_write_context_uses_verified_account(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Delivery supplies verified identity and validated intent to the audited seam."""
    response = client.request(
        method, path, json=body, headers={"Authorization": "Bearer editor"}
    )
    assert response.status_code == status
    context = factory.write_screening_use_case.execute.await_args.args[0].context
    assert (context.account, context.key, context.reason) == (
        "editor-id",
        "write-1",
        "Correct listings",
    )


@pytest.mark.parametrize(
    "header,value",
    [
        ("Idempotency-Key", ""),
        ("Idempotency-Key", "a" * 129),
        ("Idempotency-Key", "has space"),
        ("X-Change-Reason", " "),
        ("X-Change-Reason", "r" * 501),
        ("X-Change-Reason", "hidden\x7f"),
    ],
)
@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_invalid_write_intent_never_executes(
    client: TestClient,
    factory: MagicMock,
    header: str,
    value: str,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Every mutation rejects invalid headers before audited execution."""
    response = client.request(
        method,
        path,
        json=body,
        headers={"Authorization": "Bearer editor", header: value},
    )
    assert response.status_code == 422
    factory.write_screening_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
@pytest.mark.parametrize(
    "error,expected",
    [(ScreeningIdempotencyConflictError, 409), (ScreeningWriteBusyError, 503)],
)
def test_replay_errors_have_http_contract(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
    error: type[ApplicationError],
    expected: int,
) -> None:
    """Conflicting intent and bounded wait failure map to documented retry behavior."""
    factory.write_screening_use_case.execute.side_effect = error("Write rejected")
    response = client.request(
        method, path, json=body, headers={"Authorization": "Bearer editor"}
    )
    assert response.status_code == expected
    assert response.json()["error_code"] == (
        "idempotency_conflict" if expected == 409 else "service_unavailable"
    )
    if expected == 503:
        assert response.headers["Retry-After"] == "1"


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_saved_success_replays_uncached_and_invalidates_again(
    client: TestClient,
    factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Saved success retries invalidation on every replay without another mutation."""
    from unittest.mock import AsyncMock

    from marquise_api.routers import screenings

    invalidate = AsyncMock()
    monkeypatch.setattr(screenings, "invalidate_public_cache", invalidate)
    factory.write_screening_use_case.execute.side_effect = None
    factory.write_screening_use_case.execute.return_value = (
        WriteScreeningUseCase.OutputData(
            screening_id="persisted-id",
            changed=True,
            screening=None
            if method == "DELETE"
            else CreateScreeningUseCase.OutputData(**PERSISTED),
        )
    )
    responses = [
        client.request(
            method, path, json=body, headers={"Authorization": "Bearer editor"}
        )
        for _ in range(2)
    ]
    assert [response.status_code for response in responses] == [status, status]
    assert responses[0].content == responses[1].content
    assert invalidate.await_count == 2
    if method == "POST":
        assert responses[1].headers["Location"] == "/v1/screenings/persisted-id"
    assert "x-fastapi-cache" not in responses[1].headers
    getattr(factory, name).execute.assert_not_awaited()


@pytest.mark.parametrize("method,path,body,name,status", OPERATIONS)
def test_saved_success_still_requires_authorization(
    client: TestClient,
    factory: MagicMock,
    method: str,
    path: str,
    body: dict | None,
    name: str,
    status: int,
) -> None:
    """Having a previously successful key never bypasses current permission checks."""
    factory.write_screening_use_case.execute.side_effect = None
    factory.write_screening_use_case.execute.return_value = (
        WriteScreeningUseCase.OutputData(screening_id="persisted-id", changed=True)
    )
    factory.verify_access_token_query.execute.return_value = (
        VerifyAccessTokenQuery.OutputData(
            subject="editor-id", can_edit=False, can_administer=False
        )
    )
    response = client.request(
        method, path, json=body, headers={"Authorization": "Bearer revoked"}
    )
    assert response.status_code == 403
    factory.write_screening_use_case.execute.assert_not_awaited()
