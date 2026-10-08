"""Supabase Bot HTTP requests with an injected mock transport."""

import json
import urllib.request
from unittest.mock import create_autospec, patch

import pytest

from marquise.infrastructure.auth.gotrue import GoTrueAuthGateway


@pytest.mark.asyncio
async def test_bot_lookup_searches_all_pages_and_roles() -> None:
    """A duplicate on a later page conflicts even on a Member account."""
    opener = create_autospec(urllib.request.OpenerDirector, instance=True)
    opener.open.return_value.__enter__.return_value.read.side_effect = [
        json.dumps({"users": [{"app_metadata": {}}] * 50}).encode(),
        json.dumps(
            {
                "users": [
                    {
                        "app_metadata": {
                            "marquise_bot_id": "pi",
                            "marquise_role": "member",
                        }
                    }
                ]
            }
        ).encode(),
    ]
    with patch("urllib.request.build_opener", return_value=opener):
        gateway = GoTrueAuthGateway(
            "https://project.supabase.co/auth/v1", "public", "privileged"
        )
        assert await gateway.identifier_exists("pi") is True
    requests = [call.args[0] for call in opener.open.call_args_list]
    assert "page=1" in requests[0].full_url
    assert "page=2" in requests[1].full_url
    assert all("filter=" not in request.full_url for request in requests)


@pytest.mark.asyncio
async def test_bot_creation_metadata_and_cleanup_requests() -> None:
    """Only signup uses the publishable key; metadata and deletion use the local key."""
    opener = create_autospec(urllib.request.OpenerDirector, instance=True)
    opener.open.return_value.__enter__.return_value.read.side_effect = [
        b'{"user":{"id":"bot-id"},"refresh_token":"bot-secret"}',
        b"{}",
        b"{}",
    ]
    with patch("urllib.request.build_opener", return_value=opener):
        gateway = GoTrueAuthGateway(
            "https://project.supabase.co/auth/v1", "public", "privileged"
        )
        session = await gateway.create_anonymous()
        assert session["refresh_token"] == "bot-secret"
        await gateway.assign_editor("bot-id", "pi.worker_2")
        await gateway.delete("bot-id")
    signup, metadata, deletion = [call.args[0] for call in opener.open.call_args_list]
    assert signup.method == "POST"
    assert signup.full_url.endswith("/signup")
    assert json.loads(signup.data) == {}
    assert signup.get_header("Apikey") == "public"
    assert signup.get_header("Authorization") is None
    assert metadata.method == "PUT"
    assert json.loads(metadata.data) == {
        "app_metadata": {"marquise_role": "editor", "marquise_bot_id": "pi.worker_2"}
    }
    assert metadata.get_header("Authorization") == "Bearer privileged"
    assert deletion.method == "DELETE"
    assert deletion.full_url.endswith("/admin/users/bot-id")
