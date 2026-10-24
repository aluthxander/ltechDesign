"""Explicit, staged version-to-version migrations. There are no legacy paths yet."""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .errors import ModelError, fail

Payload = dict[str, Any]


@dataclass(frozen=True, slots=True)
class MigrationStep:
    source: str
    target: str
    description: str


@dataclass(frozen=True, slots=True)
class MigrationResult:
    payload: Payload
    steps: tuple[MigrationStep, ...]


class MigrationRegistry:
    """Each version has one explicit successor, validated before and after every step.

    Callbacks operate only on private staging data. Callers register complete
    version validators (including project-level references for project migrations).
    ID/blob preservation is the responsibility of each tested migration; changing
    versions alone is never accepted as proof of compatibility.
    """

    def __init__(self) -> None:
        self._validators: dict[str, Callable[[Payload], object]] = {}
        self._edges: dict[str, tuple[str, Callable[[Payload], Payload], str]] = {}

    def register_version(self, version: str, validator: Callable[[Payload], object]) -> None:
        if version in self._validators:
            fail("duplicate_migration_version", actual=version)
        self._validators[version] = validator

    def register(
        self, source: str, target: str, migrate: Callable[[Payload], Payload], *, description: str
    ) -> None:
        if source == target or source in self._edges or not description:
            fail("invalid_migration_registration")
        if source not in self._validators or target not in self._validators:
            fail("missing_migration_validator")
        cursor = target
        while cursor in self._edges:
            cursor = self._edges[cursor][0]
            if cursor == source:
                fail("migration_cycle")
        self._edges[source] = (target, migrate, description)

    def migrate(self, payload: Payload, target: str) -> MigrationResult:
        staged = deepcopy(payload)
        source = staged.get("schema_version")
        if not isinstance(source, str) or source not in self._validators:
            fail(
                "unsupported_version",
                code="unsupported_version",
                actual=source,
                supported=sorted(self._validators),
            )
        self._validators[source](deepcopy(staged))
        steps = []
        while source != target:
            if source not in self._edges:
                fail("no_migration_path", code="unsupported_version", actual=source, target=target)
            successor, callback, description = self._edges[source]
            try:
                result = callback(deepcopy(staged))
                if not isinstance(result, dict) or result.get("schema_version") != successor:
                    fail("migration_version_mismatch")
                self._validators[successor](deepcopy(result))
            except ModelError:
                raise
            except Exception as error:
                raise ModelError("migration_failed", source=source, target=successor) from error
            staged = deepcopy(result)
            steps.append(MigrationStep(source, successor, description))
            source = successor
        return MigrationResult(staged, tuple(steps))


def document_migrations() -> MigrationRegistry:
    from .codec import from_data
    from .models import Document

    registry = MigrationRegistry()
    registry.register_version("1.0", lambda payload: from_data(Document, payload))
    return registry
