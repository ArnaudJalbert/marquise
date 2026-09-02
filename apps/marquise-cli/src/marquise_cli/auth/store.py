"""PostgreSQL store for roles and user search."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

import asyncpg

_ROLE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


@dataclass(frozen=True, slots=True)
class RoleRecord:
    """Role stored in the database."""

    name: str
    description: str | None


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Auth user joined with optional role assignment."""

    id: str
    email: str | None
    created_at: str | None
    role_name: str | None


def validate_role_name(name: str) -> str:
    """Validate and normalize a role slug."""
    normalized = name.strip().lower()
    if not _ROLE_NAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Role name must start with a letter and contain only lowercase "
            "letters, digits, hyphens, or underscores (max 64 characters)."
        )
    return normalized


def _sanitize_dsn(dsn: str) -> str:
    """Percent-encode password characters in a PostgreSQL DSN."""
    if "://" not in dsn or "@" not in dsn:
        return dsn
    scheme, remainder = dsn.split("://", 1)
    userinfo, hostpart = remainder.rsplit("@", 1)
    if ":" not in userinfo:
        return dsn
    user, password = userinfo.split(":", 1)
    safe_password = urllib.parse.quote(password, safe="")
    return f"{scheme}://{user}:{safe_password}@{hostpart}"


class RoleStore:
    """Read and write roles and user-role assignments."""

    def __init__(self, database_url: str, schema: str = "marquise") -> None:
        self._database_url = _sanitize_dsn(database_url)
        self._schema = schema
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            self._database_url,
            min_size=1,
            max_size=2,
        )

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self) -> RoleStore:
        await self.connect()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.disconnect()

    def _pool_or_raise(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("RoleStore not connected")
        return self._pool

    async def create_role(
        self,
        name: str,
        description: str | None = None,
    ) -> RoleRecord:
        role_name = validate_role_name(name)
        pool = self._pool_or_raise()
        try:
            row = await pool.fetchrow(
                f"""
                INSERT INTO "{self._schema}".roles (name, description)
                VALUES ($1, $2)
                RETURNING name, description
                """,
                role_name,
                description,
            )
        except asyncpg.UniqueViolationError as error:
            raise ValueError(f'Role "{role_name}" already exists') from error
        if row is None:
            raise RuntimeError("Failed to create role")
        return RoleRecord(name=row["name"], description=row["description"])

    async def list_roles(self) -> list[RoleRecord]:
        pool = self._pool_or_raise()
        rows = await pool.fetch(
            f"""
            SELECT name, description
            FROM "{self._schema}".roles
            ORDER BY name
            """
        )
        return [
            RoleRecord(name=row["name"], description=row["description"]) for row in rows
        ]

    async def role_exists(self, name: str) -> bool:
        role_name = validate_role_name(name)
        pool = self._pool_or_raise()
        value = await pool.fetchval(
            f'SELECT 1 FROM "{self._schema}".roles WHERE name = $1',
            role_name,
        )
        return value is not None

    async def assign_role(self, user_id: str, role_name: str) -> None:
        normalized_role = validate_role_name(role_name)
        if not await self.role_exists(normalized_role):
            raise ValueError(f'Role "{normalized_role}" does not exist')
        pool = self._pool_or_raise()
        await pool.execute(
            f"""
            INSERT INTO "{self._schema}".user_roles (user_id, role_name)
            VALUES ($1::uuid, $2)
            ON CONFLICT (user_id) DO UPDATE SET role_name = EXCLUDED.role_name
            """,
            user_id,
            normalized_role,
        )

    async def clear_role(self, user_id: str) -> None:
        pool = self._pool_or_raise()
        await pool.execute(
            f'DELETE FROM "{self._schema}".user_roles WHERE user_id = $1::uuid',
            user_id,
        )

    async def search_users(
        self,
        *,
        email: str | None = None,
        query: str | None = None,
    ) -> list[UserRecord]:
        pool = self._pool_or_raise()
        conditions: list[str] = []
        params: list[str] = []

        if email is not None:
            params.append(email.strip().lower())
            conditions.append(f"lower(u.email) = ${len(params)}")
        elif query is not None:
            params.append(f"%{query.strip().lower()}%")
            conditions.append(f"lower(u.email) LIKE ${len(params)}")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
                u.id::text AS id,
                u.email,
                u.created_at::text AS created_at,
                ur.role_name
            FROM auth.users u
            LEFT JOIN "{self._schema}".user_roles ur ON ur.user_id = u.id
            {where_clause}
            ORDER BY u.email NULLS LAST
        """
        rows = await pool.fetch(sql, *params)
        return [
            UserRecord(
                id=row["id"],
                email=row["email"],
                created_at=row["created_at"],
                role_name=row["role_name"],
            )
            for row in rows
        ]

    async def get_user_by_email(self, email: str) -> UserRecord | None:
        users = await self.search_users(email=email)
        return users[0] if users else None
