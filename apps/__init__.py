"""Workspace apps that consume the marquise-core public API.

Each app is a separate workspace member with its own ``pyproject.toml``.
Apps may only import from the top-level ``marquise`` package — never from
``marquise.domain``, ``marquise.application``,
``marquise.interface_adapters``, or ``marquise.infrastructure``.
"""
