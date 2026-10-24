"""Generate standalone Draft 2020-12 schemas from the runtime type vocabulary.

Cross-member graph, geometry, integrity and capability checks remain mandatory
typed-validator gates; JSON Schema alone cannot prove those invariants.
"""

import types
from collections.abc import Mapping
from dataclasses import is_dataclass
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from .codec import MEMBER_TYPES
from .models import Node, Record
from .typing import ID_PATTERN, PATTERNS, hints
from .validation import DATA_TYPES


def member_schema(cls: type[Record]) -> dict[str, Any]:
    definitions: dict[str, Any] = {}

    def describe(annotation: Any) -> dict[str, Any]:
        origin, args = get_origin(annotation), get_args(annotation)
        if origin is Annotated:
            schema = describe(args[0])
            for rule in args[1:]:
                if rule in PATTERNS:
                    schema["pattern"] = "^" + PATTERNS[rule] + "$"
                if rule == "entry_path":
                    schema.update(
                        minLength=1,
                        pattern=r"^(?!/)(?!.*[\\:\u0000-\u001f\u007f])"
                        r"(?!.*(?:^|/)\.{1,2}(?:/|$))(?!.*//)(?!.*[. ](?:/|$)).*[^/]$",
                    )
                    schema["$comment"] = "Also enforce NFC, reserved device names and path aliases."
                if rule == "timestamp":
                    schema["format"] = "date-time"
                if rule == "positive":
                    schema["exclusiveMinimum"] = 0
                if rule == "nonnegative":
                    schema["minimum"] = 0
                if rule in ("revision", "safe_integer"):
                    schema["maximum"] = 9007199254740991
                    schema["minimum"] = 0
                if rule == "unit_interval":
                    schema.update(minimum=0, maximum=1)
                if rule == "weight":
                    schema.update(minimum=1, maximum=1000)
                if rule == "nonempty":
                    schema["minLength"] = 1
                if rule == "max_eight":
                    schema["maxItems"] = 8
                if rule in ("min_one", "min_three"):
                    schema["minItems"] = 1 if rule == "min_one" else 3
            return schema
        if hasattr(annotation, "__supertype__"):
            return {"type": "string", "pattern": "^" + ID_PATTERN + "$"}
        if origin in (types.UnionType, Union):
            return {"anyOf": [describe(a) for a in args]}
        if origin is Literal:
            return {"enum": list(args), "type": "string"}
        if annotation in (str, bool, int, float, type(None)):
            return {
                "type": {
                    str: "string",
                    bool: "boolean",
                    int: "integer",
                    float: "number",
                    type(None): "null",
                }[annotation]
            }
        if origin is tuple:
            if len(args) == 2 and args[1] is Ellipsis:
                return {"type": "array", "items": describe(args[0])}
            return {
                "type": "array",
                "prefixItems": [describe(a) for a in args],
                "items": False,
                "minItems": len(args),
                "maxItems": len(args),
            }
        if origin is Mapping:
            return {
                "type": "object",
                "propertyNames": describe(args[0]),
                "additionalProperties": describe(args[1]),
            }
        if isinstance(annotation, type) and is_dataclass(annotation):
            name = annotation.__name__
            if name not in definitions:
                definitions[name] = {}
                properties = {k: describe(t) for k, t in hints(annotation).items()}
                definitions[name] = {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties),
                    "additionalProperties": False,
                }
                for key in (
                    "children",
                    "root_ids",
                    "required_capabilities",
                    "optional_capabilities",
                    "paths",
                    "asset_ids",
                ):
                    if key in properties:
                        properties[key]["uniqueItems"] = True
                if annotation is Node:
                    conditions = []
                    for kind, data in DATA_TYPES.items():
                        then: dict[str, Any] = {"properties": {"data": describe(data)}}
                        if kind not in ("line", "group"):
                            then["properties"].update(
                                width={"exclusiveMinimum": 0}, height={"exclusiveMinimum": 0}
                            )
                        if kind not in ("artboard", "frame", "group"):
                            then["properties"].update(
                                children={"maxItems": 0}, clip_content={"const": False}
                            )
                        if kind == "artboard":
                            then["properties"]["parent_id"] = {"type": "null"}
                        conditions.append(
                            {"if": {"properties": {"type": {"const": kind}}}, "then": then}
                        )
                    definitions[name]["allOf"] = conditions
            return {"$ref": f"#/$defs/{name}"}
        raise TypeError(f"Not a file annotation: {annotation!r}")

    root = describe(cls)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:ltechdesign:1.0:{cls.__name__}",
        "$comment": "Finite numbers, strict JSON keys, bounds and cross-references also require "
        "ltechdesign.domain validators. All fields are required on disk.",
        **root,
        "$defs": definitions,
    }


def schemas() -> dict[str, dict[str, Any]]:
    return {
        path.replace("/", "-").replace(".json", ".schema.json"): member_schema(cls)
        for path, cls in MEMBER_TYPES.items()
    }
