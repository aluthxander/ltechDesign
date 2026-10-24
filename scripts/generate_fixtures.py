"""Generate only fixtures supported by the current foundation, without network."""

import argparse
import hashlib
import json
from pathlib import Path

from generate_domain_fixtures import domain_files
from generate_native_fixture import native_fixture

ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
REVISION = "9437b806936896fa1a8c812e561067a5f30f5933"
FONT_HASHES = {
    "Abel-Regular.ttf": "8809dcad25318225052f88333e208c5aad4adcb7b2c934c135735ec19aa410b4",
    "OFL.txt": "4f4bc3806a1e55789c6ef75ca5fc628297b05292f74966474dc0d40324abc609",
}


def expected_files() -> dict[str, bytes]:
    for name, expected in FONT_HASHES.items():
        if hashlib.sha256((ROOT / "fonts" / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Vendored font/license hash mismatch: {name}")
    manifest = {
        "fixture_version": 1,
        "subsystem": "desktop-font-smoke",
        "family": "Abel",
        "license": "SIL-OFL-1.1",
        "source": f"https://github.com/google/fonts/tree/{REVISION}/ofl/abel",
        "sha256": FONT_HASHES,
        "not_implemented": ["renderer", "visual-golden"],
    }
    return {
        **domain_files(),
        "fonts/manifest.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
        "visual/text-sample.txt": b"ltechDesign Studio\nABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
        b"abcdefghijklmnopqrstuvwxyz\n0123456789 !?.,:;+-=()\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    expected = {args.output / relative: content for relative, content in expected_files().items()}
    if args.output.resolve() == ROOT.resolve():
        docs = ROOT.parents[1] / "docs"
        expected[docs / "examples/ltechdesign-v1-contract.json"] = expected[
            args.output / "schema/nested-v1.json"
        ]
        for target, content in list(expected.items()):
            if target.parent.name == "json-schema":
                expected[docs / "schemas" / target.name] = content
        expected[ROOT.parents[1] / "examples/proyek-contoh.ltechdesign"] = native_fixture()
    for target, content in expected.items():
        if args.check:
            if not target.is_file() or target.read_bytes() != content:
                print(f"Fixture missing or stale: {target}")
                return 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
