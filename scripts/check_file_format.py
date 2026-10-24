"""Audit frozen JSON examples using the same domain boundary as future persistence."""

import base64
from pathlib import Path

from ltechdesign.domain import ModelError, dump_project, load_project, semantic_content
from ltechdesign.domain.codec import json_bytes, parse_json

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for relative in (
        "docs/examples/ltechdesign-v1-contract.json",
        "tests/fixtures/schema/legacy-00b.json",
    ):
        wrapper = parse_json((ROOT / relative).read_bytes())
        assert wrapper["example_kind"] == "ltechdesign.documentation-members/1"
        payloads = {p: json_bytes(v) for p, v in wrapper["members"].items()}
        blobs = {
            b["path"]: base64.b64decode(b["base64"], validate=True) for b in wrapper["asset_blobs"]
        }
        payloads.update(blobs)
        project = load_project(payloads)
        restored = load_project(dump_project(project, blobs))
        assert semantic_content(project) == semantic_content(restored)
        manifest = wrapper["members"]["manifest.json"]
        manifest["required_capabilities"].append("future.unknown/1")
        payloads["manifest.json"] = json_bytes(manifest)
        try:
            load_project(payloads)
        except ModelError as error:
            assert error.code == "unsupported_capability"
        else:
            raise AssertionError("Unsupported required capability was accepted")
        print(f"PASS: strict members, integrity, references and semantic round-trip: {relative}")
    print("PASS: unknown required capabilities rejected. ZIP/decode/GUI gates belong to 04/06A/22.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
