# Baseline10B — Rulers/grid/snapping/smart guides/align/distribute

25 Oktober 2026 (Asia/Jakarta). **10B verified**:10B.snapping,10B.arrangement,
10B.overlays dan10B.handoff verified. **Induk10 verified** karena10A sudah verified
sebelum10B dan seluruh checkpoint wajib10B kini mempunyai bukti. Segmen11 tidak
dikerjakan otomatis.

Base HEAD `d05a7e171d070987eddf091cd7b21a4f1ad5c06f`; working tree sudah memuat
09/10A, seluruh perubahan dipertahankan. Tidak membuat commit otomatis atau
mengubah PRD/native schema1.0. Kontrak [ADR0022](adr/0022-canvas-aids-and-arrangement.md).

## Perubahan dan source

- `domain/snapping.py`: deterministic world edge/center/grid snapping, physical
  pixel tolerance, exclusion hierarchy dan constrained resize ray.
- `domain/arrangement.py`, `commands/contracts.py`/`planning.py`: typed ArrangeNodes,
  world geometry six-way align/equal gaps, inverse-parent deltas/atomic history.
- `ui/canvas_aids.py`, integrasi `ui/canvas.py`/`transforms.py`, `rendering/canvas.py`:
  per-view controls/rulers/grid/smart guides; pointer move/resize/drawing snap,
  offset-correct handle math, visibility/history/export separation.
- `ui/arrangement.py`, Inspector/window integration: eight buttons dan disabled
  selection/read-only states. Inspector tetap parent translation dan literal input.
- `scripts/check_canvas_aids.py`: Qt subprocess DPI/gesture spike. Tiga suite
  `test_snapping.py`, `test_arrangement.py`, `test_canvas_aids.py`. Tidak menghapus
  atau melonggarkan existing tests. Dependency tidak berubah.

## Verifikasi aktual

Final targeted **58 passed offscreen** (29core+29GUI), **47 passed native**
(29GUI10B+8Inspector10A+10Hierarchy09). Full `scripts/check.ps1` offline exit0:
**405 core +110 desktop**, Ruff87/mypy83 files, docs/fixtures/sdist/wheel/isolated
installed-wheel smoke lulus. Build/executable offscreen exit0, PyInstaller6.22.3.
Wheel terisolasi menjalankan actual snapping/one-undo/Inspector-sync spike dari
site-packages, exit0. [Evidence JSON](evidence/segment10b-verification.json)
menyimpan JUnit, source/artifact hashes, executable report dan Qt scale runs.
Tidak ada skipped pada empat suite evidence.

Native GUI mencakup subprocess Windows dengan
**actual viewport DPR1/1.5/2**, masing-masing zoom0.5/1/2/4. Near7.9 physical px
snap, far8.1 tidak; QTest gesture3px-near snap tepat dan satu Undo. Pure tolerance
juga diuji pada zoom0.25/1/4×DPR1/1.5/2. Regresi awal42 GUI lulus.

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv/Scripts/python.exe -m pytest tests/test_arrangement.py tests/test_snapping.py tests/test_canvas_aids.py -q --basetemp=artifacts/segment10b-offscreen --junitxml=artifacts/segment10b-offscreen.xml
$env:QT_QPA_PLATFORM = 'windows'
.venv/Scripts/python.exe -m pytest tests/test_canvas_aids.py -q --basetemp=artifacts/segment10b-native --junitxml=artifacts/segment10b-native.xml
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen
$env:QT_QPA_PLATFORM = 'offscreen'
.cache/package-smoke/Scripts/python.exe -I scripts/check_canvas_aids.py artifacts/segment10b-wheel-aids
```

Runtime yang
dipakai Python3.12.12, PySide6/Qt6.10.2, Pillow12.3.0; tanpa dependency baru.
Native tests memakai event sintetis Qt, bukan input fisik. Actual Windows DPR
awal dikalibrasi sebelum QT_SCALE_FACTOR; bukan mock DPR atau perubahan setting OS.

Bukti `artifacts/segment10b-native/`:

- `test_object_snap_nested_rotati0..2/smart-guides-native.png`: preview/magenta
  guide, nested parent rotation, ruler/grid controls dan Inspector. Screenshot
  native benar-benar diperiksa.
- `test_actual_qt_screen_scale_su0..2/report.json` dan `canvas-aids-native.png`:
  actual DPR1/1.5/2, four-zoom tolerance/one-undo/Inspector sync. Screenshot native
  1×/1.5×/2× benar-benar diperiksa.
- `test_overlay_toggle_no_history0/`: scene/PNG overlay-free exact, PDF tanpa aids,
  arranged PNG/PDF/PDF raster dan native arranged-editable ZIP. Piksel PDF
  membuktikan posisi baru sesudah align dan lokasi lama kosong; PNG shared dan
  PDF raster byte-identik pada fixture ini. Save/close/Open
  mempertahankan Document lengkap;
  per-tab aids kembali default dan tidak menjadi syarat restore.
- JUnit targeted/full core/desktop, `artifacts/segment10b-check.log`, build log dan
  wheel probe report menjadi evidence final; tanpa klaim visual executable smoke.

Tes mencakup nested parent move/resize/align, cross-parent multiselect rigid move,
six align/equal gaps/negative gaps/stable z-order, uniform group/multiselect
resize, hidden/locked subtree targets, stale revision rollback/cancellation,
grid root/rotated parent drawing, master snap off, literal nudge/Inspector,
ruler ticks pan/zoom, cancelled preview (termasuk selection Layers programmatic
tanpa focus-out) dan ruler click tanpa manual guide. Bar ruler dipisahkan oleh
viewport margin, sehingga gesture drawing10A di tepi tetap bekerja tanpa mengubah
tes lama. Native PNG/PDF raster arranged benar-benar diperiksa.

## Demo, pending dan batas scope

Jalankan `powershell -ExecutionPolicy Bypass -File scripts/run.ps1`, buat beberapa
shape, aktifkan **Snap** serta Grid snap/Object snap. Grid/ruler/Smart guides
visibility terpisah. Drag dekat edge/center untuk magenta guide; satu Undo
mengembalikan gesture. Pilih ≥2 shapes untuk Left/Center/Right/Top/Bottom,
≥3 untuk Space H/V (equal gaps). Width group tetap uniform. Save/Open kemudian
cek desain editable; angka Inspector X/Y tetap dalam parent space.

Manual mouse/keyboard fisik, screen reader, monitor switching/OS DPI fisik,
mesin rilis bersih dan reference performance besar **belum dilakukan**. Candidate
clip AABB konservatif; shared renderer tetap rounded/path clip sebenarnya.
10B tidak membuat manual guides38B, typography11, evaluator layout13, public
export15–17 atau MCP18/19. Existing08.layout tetap blocked khusus evaluator13.
Berikutnya11 `not_started`, tidak dikerjakan otomatis.
