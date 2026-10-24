"""Stable, transport-independent validation failures."""

from typing import Any, NoReturn


class ModelError(ValueError):
    def __init__(
        self, reason: str, path: str = "$", *, code: str = "invalid_project", **details: Any
    ) -> None:
        self.code = code
        self.reason = reason
        self.path = path
        self.details = details
        super().__init__(f"{code}: {reason} at {path}")

    def to_dict(self) -> dict[str, Any]:
        return dict(code=self.code, reason=self.reason, path=self.path, details=self.details)


def fail(reason: str, path: str = "$", **details: Any) -> NoReturn:
    raise ModelError(reason, path, **details)
