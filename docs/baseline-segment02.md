# Baseline segmen 02

Tanggal: 21 Oktober 2026 (Asia/Jakarta). Lingkup: domain/schema/JSON tanpa GUI.
Kode berada di `src/ltechdesign/domain`; tidak ada dependency baru.

## Kontrak dan penggunaan

```python
from ltechdesign.domain import (
    DocumentSession, create_project, dump_project, load_project,
)

project = create_project("Desain baru")
members = dump_project(project, asset_blobs={})  # dict path -> bytes, belum ZIP
restored = load_project(members)
session = DocumentSession(project=restored)  # ID sesi baru, revision 0
```

`create_node` menghasilkan ID/default lokal; pemanggil menyediakan font/asset
reference untuk text/image/svg. Gunakan `dataclasses.replace` untuk menyusun
snapshot baru; Document/Project menolak snapshot tidak konsisten. Dispatcher
atomik, commit revision, history dan editor gestures belum merupakan bagian 02.

## Invariants dan bukti perilaku

| Kontrak | Bukti |
| --- | --- |
| Import tanpa Qt, ID/default, immutability, session/revision terpisah | `test_domain.py`: subprocess dengan import Qt diblokir, snapshot defensive copy, runtime serialization ditolak |
| Seluruh 10 node, style, unit typography, reference data | fixture nested final dan tes constructor/payload/round-trip |
| Finite, bool bukan number, range/color/unknown/missing/duplicate keys | tes negatif scalar, object nested, strict JSON dan limits |
| Parent/children/root/page, duplicate/orphan/cycle/depth/z-order | tes corrupt graph, registry reorder dan root reorder |
| Pivot/order/world/relative transforms, group normalization/hidden geometry | tes matriks analitik dan world preservation, epsilon, degenerate group |
| No shear/flip/nonuniform resize; horizontal/vertical line | tes affine rejection dan fixture extent nol |
| Geometry/visual/hit bounds dan ancestor clip | tes stroke/shadow/zoom/DPR/ellipse/visibility/clip; AABB konservatif |
| Manifest/assets/fonts/tokens/workspace lintas-member | `test_project_format.py`: missing refs, media/hash/path/capability, binding types/value/range |
| Unknown required ditolak, opaque optional dipreservasi | tes capability, adapter required, exact extension byte round-trip |
| Compatibility 00B dan fixture final | masing-masing tiga Load–Save–Load, stable IDs, world matrices, Unicode dan blob hashes |
| Migration staging/version registry | synthetic success/failure/cycle/duplicate/no-path; input tidak berubah |
| Spec/example/generator/schema sinkron | fixture drift test, generator `--check`, audit format memakai validator produksi |

## Verifikasi aktual

Environment lokal: Windows, Python 3.12.12, pytest 8.4.2, PySide6/Qt 6.10.2.
Tidak ada dependency atau lock resolution baru. Gate dijalankan dengan:

```powershell
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
```

| Gate | Hasil |
| --- | --- |
| Ruff check dan format | Lulus, 23 file formatted |
| Mypy strict | Lulus, 22 source files |
| Core | 193 passed; 188 domain/format + 5 foundation |
| Desktop offscreen regression | 5 passed |
| Fixture generator --check | Lulus; final example dan 6 schemas tidak drift |
| Format audit | Final + immutable historical 00B round-trip, required capability rejection lulus |
| Documentation audit | 184 matrix rows, 79 segments/checkpoints, 37 planned MCP tools, 20 Markdown files; link/status lulus |
| Package | sdist + wheel berhasil; non-editable isolated install lulus CLI/domain JSON/no-Qt/offscreen GUI smoke |

JUnit lokal: `artifacts/core.xml` dan `artifacts/desktop.xml`. Artifact build:
`dist/ltechdesign-0.1.0.tar.gz` dan `dist/ltechdesign-0.1.0-py3-none-any.whl`.
Tidak ada commit otomatis. CI remote belum dijalankan pada sesi ini.

Percobaan awal gate terhenti oleh execution policy PowerShell, lalu oleh akses
PyPI untuk hatchling yang dibatasi jaringan. Child PowerShell dengan process-only
ExecutionPolicy Bypass dan UV_OFFLINE memakai dependency cache yang sudah ada;
gate penuh kemudian exit 0. Tidak mengubah execution policy mesin atau dependency pin.

## Batas bukti

Codec ini hanya JSON dan member bytes dalam memori, belum ZIP atau disk writer.
Hash/length metadata dan byte diperiksa; decode raster/font, SVG safety, archive
limits/paths/locks/atomic save adalah gate tambahan 04/12. Schema mendeskripsikan
struktur; graph, numeric finite, integrity dan binding memerlukan typed validator.
Model font system tidak melakukan pencarian OS atau mengganti metadata.

Bounds domain tidak mengklaim painted-pixel bounds untuk glyph/rounded clip/
transparent image. Layout bertipe bisa diperiksa sebagai Document tetapi belum
diadmit sebagai Project. Rendering/compositing dan acceptance GUI/MCP penuh
tetap 06A/22. Versi native yang diklaim hanya 1.0; fixture 00B juga berlabel 1.0.
