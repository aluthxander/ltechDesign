"""Deterministic segment 02 fixtures. Imported by generate_fixtures.py."""

import base64
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from ltechdesign.domain.codec import json_bytes, load_project
from ltechdesign.domain.models import (
    EmptyData,
    Fill,
    FrameData,
    NodeId,
    NodeType,
    PageId,
    Point,
    Shadow,
    Stroke,
    Style,
    create_node,
)
from ltechdesign.domain.schema import schemas
from ltechdesign.domain.typing import primitive

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
LEGACY_SHA256 = "37238ac0d8e696c4d256a7518f92a391593c61ad4bfd8c5a47e2c7ee182d45c9"


def formatted(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def example() -> dict[str, Any]:
    legacy_bytes = (FIXTURES / "schema/legacy-00b.json").read_bytes()
    if hashlib.sha256(legacy_bytes).hexdigest() != LEGACY_SHA256:
        raise ValueError("Historical 00B fixture was changed")
    wrapper: dict[str, Any] = json.loads(legacy_bytes.decode("utf-8-sig"))
    members = wrapper["members"]
    document = members["document.json"]
    nodes = document["nodes"]
    document["name"] = "Fixture final 1.0 — nested geometry, text, assets and bindings"
    nodes["text-title"]["data"]["text"] = "ltechDesign Studio\nEditable — 日本語 e\u0301"
    nodes["rectangle-card"]["style"]["shadows"] = [primitive(Shadow(blur=2, offset_y=3))]

    def add(
        kind: NodeType, name: str, parent: str, width: float, height: float, **changes: Any
    ) -> dict[str, Any]:
        node = create_node(
            kind, PageId(nodes[parent]["page_id"]), width=width, height=height, node_id=NodeId(name)
        )
        data = primitive(replace(node, parent_id=NodeId(parent)))
        data.update(changes)
        nodes[name] = data
        nodes[parent]["children"].append(name)
        return dict(data)

    add(
        "frame",
        "frame-nested",
        "group-content",
        80,
        40,
        x=120,
        y=50,
        rotation=-17,
        clip_content=True,
        style=primitive(Style(fill=Fill(color="#224466FF"), radius=(6, 6, 6, 6))),
        data=primitive(FrameData(background="#224466FF")),
    )
    add(
        "ellipse",
        "ellipse-overlap",
        "frame-nested",
        50,
        30,
        x=15,
        y=5,
        style=primitive(Style(fill=Fill(color="#FF6600AA"))),
    )
    add(
        "rectangle",
        "rectangle-overlap",
        "frame-nested",
        30,
        25,
        x=32,
        y=10,
        style=primitive(Style(fill=Fill(color="#0088FFAA"))),
    )
    add(
        "line",
        "line-horizontal",
        "artboard-web",
        100,
        0,
        x=15,
        y=20,
        style=primitive(Style(stroke=Stroke(width=2))),
    )
    add(
        "line",
        "line-vertical",
        "artboard-web",
        0,
        60,
        x=20,
        y=35,
        style=primitive(Style(stroke=Stroke(color="#FF0000FF"))),
    )
    add(
        "polygon",
        "polygon-triangle",
        "artboard-web",
        40,
        40,
        x=45,
        y=35,
        rotation=20,
        style=primitive(Style(fill=Fill(color="#00FF00FF"))),
    )
    add("group", "group-empty", "artboard-web", 0, 0)
    # A nonempty degenerate group is legal; its child has zero extent on one axis.
    degenerate = add("group", "group-line", "artboard-web", 0, 0, x=120, y=30)
    add("line", "line-group-child", "group-line", 0, 50, style=primitive(Style(stroke=Stroke())))
    degenerate.update(
        width=0,
        height=50,
        pivot=primitive(Point(y=25)),
        data=primitive(EmptyData()),
        children=["line-group-child"],
    )
    nodes["group-line"] = degenerate
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        b'<rect width="10" height="10" fill="#ff0000"/></svg>'
    )
    svg_hash = hashlib.sha256(svg).hexdigest()
    svg_path = "assets/data/" + svg_hash
    members["assets/index.json"]["assets"].append(
        {
            "id": "asset-svg",
            "path": svg_path,
            "media_type": "image/svg+xml",
            "byte_length": len(svg),
            "sha256": svg_hash,
        }
    )
    svg_node = dict(nodes["image-pixel"])
    svg_node.update(
        id="svg-logo",
        type="svg",
        page_id="page-web",
        parent_id="artboard-web",
        x=180,
        y=30,
        data={
            "asset_id": "asset-svg",
            "fit": "fill",
            "crop": {"x": 0, "y": 0, "width": 1, "height": 1},
        },
    )
    nodes["svg-logo"] = svg_node
    nodes["artboard-web"]["children"].append("svg-logo")
    wrapper["asset_blobs"].append({"path": svg_path, "base64": base64.b64encode(svg).decode()})
    # Embedded fixture font plus unused asset reference: save must preserve both registries.
    font_bytes = (FIXTURES / "fonts/Abel-Regular.ttf").read_bytes()
    font_hash = hashlib.sha256(font_bytes).hexdigest()
    font_path = "assets/data/" + font_hash
    members["assets/index.json"]["assets"].append(
        {
            "id": "asset-abel",
            "path": font_path,
            "media_type": "font/ttf",
            "byte_length": len(font_bytes),
            "sha256": font_hash,
        }
    )
    members["fonts.json"]["fonts"].append(
        {
            "id": "font-abel",
            "family": "Abel",
            "style": "Regular",
            "weight": 400,
            "italic": False,
            "postscript_name": "Abel-Regular",
            "source": "embedded",
            "asset_id": "asset-abel",
            "fallback_families": ["sans-serif"],
            "license": {
                "identifier": "SIL-OFL-1.1",
                "url": "https://openfontlicense.org",
                "embedding_allowed": True,
            },
        }
    )
    wrapper["asset_blobs"].append(
        {"path": font_path, "base64": base64.b64encode(font_bytes).decode()}
    )
    nodes["text-title"]["data"]["typography"]["font_id"] = "font-abel"
    token_member = members["tokens.json"]
    token_member["tokens"].extend(
        [
            {
                "id": "token-title",
                "name": "Title",
                "type": "string",
                "value": nodes["text-title"]["data"]["text"],
            },
            {"id": "token-font-size", "name": "Title size", "type": "number", "value": 20},
        ]
    )
    token_member["bindings"].extend(
        [
            {"node_id": "text-title", "property": "data.text", "token_id": "token-title"},
            {
                "node_id": "text-title",
                "property": "data.typography.font_size",
                "token_id": "token-font-size",
            },
        ]
    )
    # More than one root proves root order independently of registry insertion order.
    foreground = primitive(
        create_node(
            "rectangle", PageId("page-web"), node_id=NodeId("root-foreground"), width=15, height=15
        )
    )
    foreground.update(x=800, y=20, style=primitive(Style(fill=Fill(color="#FFFFFFFF"))))
    nodes["root-foreground"] = foreground
    document["pages"][1]["root_ids"].append("root-foreground")
    manifest = members["manifest.json"]
    manifest["writer"] = {"name": "ltechDesign fixture generator", "version": "segment02-1"}
    manifest["required_capabilities"].extend(["assets.svg/1", "fonts.embedded/1"])
    blobs = {b["path"]: base64.b64decode(b["base64"]) for b in wrapper["asset_blobs"]}
    payloads = {p: json_bytes(v) for p, v in members.items() if p != "manifest.json"}
    payloads.update(blobs)
    media = {a["path"]: a["media_type"] for a in members["assets/index.json"]["assets"]}
    manifest["files"] = [
        {
            "path": p,
            "media_type": media.get(p, "application/json"),
            "byte_length": len(b),
            "sha256": hashlib.sha256(b).hexdigest(),
        }
        for p, b in sorted(payloads.items())
    ]
    payloads["manifest.json"] = json_bytes(manifest)
    load_project(payloads)
    return wrapper


def domain_files() -> dict[str, bytes]:
    result = {"schema/nested-v1.json": formatted(example())}
    result.update(
        {f"schema/json-schema/{name}": formatted(schema) for name, schema in schemas().items()}
    )
    return result
