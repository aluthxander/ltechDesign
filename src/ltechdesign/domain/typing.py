"""One strict type vocabulary shared by constructors, JSON decoding and schema generation."""

import math
import re
import types
import unicodedata
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints

from .errors import ModelError, fail

ID_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
PATTERNS = {
    "color": r"#[0-9A-F]{8}",
    "sha256": r"[a-f0-9]{64}",
    "extension_id": r"[a-z][a-z0-9._-]{0,63}",
    "timestamp": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
}


_HINTS: dict[type[Any], dict[str, Any]] = {}


def hints(cls: type[Any]) -> dict[str, Any]:
    if cls not in _HINTS:
        _HINTS[cls] = get_type_hints(cls, include_extras=True)
    return _HINTS[cls]


def entry_path(value: str, path: str) -> None:
    parts = value.split("/")
    if (
        unicodedata.normalize("NFC", value) != value
        or "\\" in value
        or ":" in value
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
        or any(
            not part
            or part in (".", "..")
            or part.endswith((".", " "))
            or re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])", part.split(".")[0])
            for part in parts
        )
    ):
        fail("unsafe_path", path)


def check_rule(value: Any, rule: str, path: str) -> None:
    if rule in PATTERNS and re.fullmatch(PATTERNS[rule], value) is None:
        fail(f"invalid_{rule}", path)
    if rule == "timestamp":
        try:
            datetime.fromisoformat(value)
        except ValueError:
            fail("invalid_timestamp", path)
    if rule == "entry_path":
        entry_path(value, path)
    invalid = (
        (rule == "positive" and value <= 0)
        or (rule == "nonnegative" and value < 0)
        or (rule == "unit_interval" and not 0 <= value <= 1)
        or (rule == "revision" and not 0 <= value <= 9007199254740991)
        or (rule == "safe_integer" and value > 9007199254740991)
        or (rule == "weight" and not 1 <= value <= 1000)
        or (rule == "nonempty" and not value)
        or (rule == "max_eight" and len(value) > 8)
        or (rule == "min_three" and len(value) < 3)
        or (rule == "min_one" and len(value) < 1)
    )
    if invalid:
        fail("out_of_range", path, rule=rule)


def typed(value: Any, annotation: Any, path: str, *, wire: bool) -> Any:
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        result = typed(value, args[0], path, wire=wire)
        for rule in args[1:]:
            check_rule(result, rule, path)
        return result
    if hasattr(annotation, "__supertype__"):
        typed(value, str, path, wire=wire)
        if re.fullmatch(ID_PATTERN, value) is None:
            fail("invalid_id", path)
        return value
    if origin in (types.UnionType, Union):
        candidates = list(args)
        if isinstance(value, dict) and "type" in value:
            discriminated = [
                a
                for a in candidates
                if isinstance(a, type)
                and is_dataclass(a)
                and value["type"] in get_args(hints(a).get("type"))
            ]
            if discriminated:
                candidates = discriminated
            elif all(
                isinstance(a, type)
                and is_dataclass(a)
                and get_origin(hints(a).get("type")) is Literal
                for a in candidates
            ):
                fail(
                    "invalid_literal",
                    path + ".type",
                    actual=value["type"],
                    allowed=[v for a in candidates for v in get_args(hints(a)["type"])],
                )
        errors = []
        for candidate in candidates:
            try:
                return typed(value, candidate, path, wire=wire)
            except ModelError as error:
                errors.append(error)
        # Prefer the deepest failure so an invalid field is not hidden by another union arm.
        raise max(errors, key=lambda e: len(e.path))
    if origin is Literal:
        if value not in args or type(value) not in {type(a) for a in args}:
            if path.rsplit(".", 1)[-1] in (
                "schema_version",
                "format_version",
                "document_schema_version",
            ):
                fail(
                    "unsupported_version",
                    path,
                    code="unsupported_version",
                    actual=value,
                    supported=list(args),
                )
            fail("invalid_literal", path, actual=value, allowed=list(args))
        return value
    if annotation is type(None):
        if value is not None:
            fail("invalid_type", path, expected="null")
        return None
    if annotation in (str, bool, int, float, bytes):
        valid = type(value) is annotation
        if annotation is float:
            valid = type(value) in (int, float)
            if valid:
                try:
                    valid = math.isfinite(value)
                except OverflowError:
                    valid = False
                if not valid:
                    fail("nonfinite_number", path)
        if not valid:
            fail("invalid_type", path, expected=annotation.__name__)
        if annotation is str:
            try:
                value.encode("utf-8")
            except UnicodeError:
                fail("invalid_unicode", path)
        return value
    if origin is tuple:
        if type(value) is not (list if wire else tuple):
            fail("invalid_type", path, expected="array" if wire else "tuple")
        variable = len(args) == 2 and args[1] is Ellipsis
        if not variable and len(value) != len(args):
            fail("invalid_length", path, expected=len(args))
        return tuple(
            typed(v, args[0] if variable else args[i], f"{path}[{i}]", wire=wire)
            for i, v in enumerate(value)
        )
    if origin is Mapping:
        if not isinstance(value, Mapping) or (wire and type(value) is not dict):
            fail("invalid_type", path, expected="object")
        return MappingProxyType(
            {
                typed(k, args[0], f"{path}.<key>", wire=wire): typed(
                    v, args[1], f"{path}[{k}]", wire=wire
                )
                for k, v in value.items()
            }
        )
    if isinstance(annotation, type) and is_dataclass(annotation):
        if not wire:
            if type(value) is not annotation:
                fail("invalid_type", path, expected=annotation.__name__)
            return value
        if type(value) is not dict:
            fail("invalid_type", path, expected="object")
        expected = hints(annotation)
        extra, missing = value.keys() - expected.keys(), expected.keys() - value.keys()
        if extra:
            fail("unknown_property", path, properties=sorted(extra))
        if missing:
            fail("missing_property", path, properties=sorted(missing))
        kwargs = {k: typed(value[k], t, f"{path}.{k}", wire=True) for k, t in expected.items()}
        try:
            return annotation(**kwargs)
        except ModelError as error:
            raise ModelError(
                error.reason, path + error.path[1:], code=error.code, **error.details
            ) from error
    raise TypeError(f"Unregistered model annotation: {annotation!r}")


def check_record(record: Any) -> None:
    for name, annotation in hints(type(record)).items():
        result = typed(getattr(record, name), annotation, f"$.{name}", wire=False)
        # Defensive copy: frozen dataclasses alone do not freeze caller-owned dictionaries.
        if isinstance(result, Mapping):
            object.__setattr__(record, name, result)


def primitive(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: primitive(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {k: primitive(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [primitive(v) for v in value]
    return value
