# Bukti conformance renderer 06A

Status **verified untuk scope fixture conformance yang diminta**. Baseline commit
54162c5; seluruh implementasi tetap working tree tanpa commit otomatis.
Scope hanya 06A: satu fixture 600×400, nested rotations pada frame/ellipse,
rounded clip, group opacity0,5 dengan dua opaque children overlap dan dua baris
primitive text Abel. Tidak membuat export UI atau drawing tools.

Checkpoint 06A.fixture, 06A.text, 06A.targets dan 06A.handoff. Keputusan dan
riwayat mismatch di [ADR 0017](adr/0017-render-conformance.md).

## Reproduksi

```powershell
$env:QT_QPA_PLATFORM = 'windows'
.\.venv\Scripts\python.exe scripts/check_render_conformance.py --mode canvas --output artifacts/render06a/canvas
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe scripts/check_render_conformance.py --mode offscreen --output artifacts/render06a/offscreen
.\.venv\Scripts\python.exe -m pytest tests/test_render_conformance.py -v
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen
```

Harness membuat PDF/PNG 1x/2x, raster PDF via QtPdf/PDFium, screenshot canvas
native serta report font metrics/fixture hashes. Kedua child merupakan proses
terpisah, QApplication native Windows versus QGuiApplication offscreen. Native
dan offscreen menerima byte members/domain fixture identik. QGraphicsScene.render
menggunakan NodeItem → shared drawing yang sama, bukan renderer kedua.

## Bukti aktual

- Tiga tes conformance lulus, ditambah tujuh tes regresi renderer 06 lulus.
- Gate awal lengkap: **324 core + 19 desktop passed**, lint/format57 files,
  mypy53 files, fixtures/docs/build/wheel/installed-wheel smoke exit0.
- Python3.12.12, PySide6/Qt6.10.2, pytest8.4.2, ruff0.14.0, mypy1.18.2.
- Native canvas vs PNG exact. Native/offscreen font metrics exact: ascent23,5,
  line widths139,953125 /79; line origins0 /28,8. Pixels different474 (0,20% dari
 240.000), semuanya edge glyph; max4/255, interior0.
- PDF raster comparison: native3456 differing edge pixels, offscreen3110; maximum
  premultiplied channel error58/255 hanya dalam edge band1px; interior0 kedua mode.
  Bounding box setiap region group/frame/text tidak bergeser lebih dari1px.
- Alpha group overlap dan single-child127±1, clipped rounded corner0, frame center255.
- PDF page450×300pt; dua image objects dengan dimensi sama = group fallback + SMask.
  Text outline tidak menjadi image dan bukan searchable; PDF reader mengembalikan
  empty text sebagaimana diassert, tidak mengklaim font embedding.

## Batas dan integrasi

PDF dan screenshot native serta raster PDF di atas background putih benar-benar
diperiksa secara visual. Tidak ada inspeksi print fisik, banyak monitor, atau
PDF viewer lain; Poppler tidak tersedia. PDFium merupakan rasterizer pembanding
yang berbeda dari Qt QPainter raster path. Perbedaan anti-aliasing tidak disembunyikan
dalam toleransi global; seluruh interior dan geometry/alpha probes tetap strict.

Text primitive belum inline editing/advanced type/auto sizing; belum auto-resolve
font proyek pada shell GUI umum. Caller memberi Resources family mapping; metadata
FontId/TextData tetap tersimpan. UI/resolver lengkap di11, image/SVG12, shadow10A,
production preview/export services dan jobs15–17. Fixture transparent-image dan
multi-artboard acceptance menyusul fitur pemilik/22; tidak diklaim dari fixture ini.
API PDF proof tidak menjamin atomic target file operation atau production export
security. Tidak mengubah .ltechdesign atau undo/revision lewat render.

Segmen07 belum dimulai. Aman memperluas drawing sesudah gate06A terverifikasi;
tidak dikerjakan otomatis dalam sesi ini.

Gate final selesai exit0: 324 core + 19 desktop; lint/format57 files, mypy53 files, fixture/docs/build/wheel smoke lulus. Setelah full gate, tambahan assert ancestor rounded clip saat isolation di tests/test_rendering.py dijalankan: 7 passed; tidak melemahkan tes lama. Executable spike 01A diulang: scripts/smoke-build.ps1 -SmokeMode offscreen exit0, PyInstaller6.22.3/hooks2026.9. Bukti [package](evidence/segment06a-package-offscreen.json), [comparison](evidence/segment06a-comparison.json), [PDF](evidence/segment06a.pdf), [PNG](evidence/segment06a-shared.png), [canvas](evidence/segment06a-canvas.png), [PDF raster white](evidence/segment06a-pdf.png). Semua checkpoint verified; tidak ada blocker. Segmen07 belum dimulai.
