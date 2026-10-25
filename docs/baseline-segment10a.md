# Baseline 10A — Inspector/style/color/basic shadow

25 Oktober 2026 (Asia/Jakarta). **10A verified**: checkpoint10A.properties,
10A.history,10A.shadow dan10A.handoff verified. Induk10 masih `in_progress`
sampai10B dijalankan atas instruksi pengguna.

Base HEAD `d05a7e171d070987eddf091cd7b21a4f1ad5c06f`; perubahan09 sudah ada di
working tree dan dipertahankan. Tanpa commit otomatis, PRD/native schema tetap.
Kontrak [ADR0021](adr/0021-inspector-and-shared-shadow.md).

## Source dan lingkup

- `domain/inspector.py`, `commands/contracts.py`/`planning.py`: typed SetProperties,
  parent translation, anchor/pivot resize, uniform group extent, finite/range/type/
  color validation dan atomic multiselect. Memakai field model/codec1.0 yang ada.
- `commands/dispatcher.py`: grouped Undo per client, tetap per-commit revision/
  receipt. History/command/client/save boundaries memutus merge.
- `ui/inspector.py`, `window.py`/`canvas.py`: geometry/style/Mixed/none/disabled,
  RGBA picker, opacity slider, palette new drawing, read-only/stale-edit guards.
- `rendering/shadow.py`/`drawing.py`/`pdf.py`: alpha shadow, spread/blur/tint,
  transformed offset, isolated group opacity, clipping/union bounds/budget dan
  PDF fallback reporting. Memakai canvas/PNG/PDF proof06A, bukan public jobs/UI.
- Suite `test_inspector_commands.py`, `test_inspector_panel.py`,
  `test_style_rendering.py`; tidak menghapus/melonggarkan tes existing.

## Verifikasi aktual

Regresi awal75 passed. Final targeted: **34 passed offscreen** (16core+18desktop),
**18 passed Windows native**, termasuk real Qt RGBA dialog dengan event timer,
QTest keyboard/arrows/drawing dan slider. Full `scripts/check.ps1` offline exit0:
**376 core +81 desktop**, lint/format79 files, mypy75 files, docs/fixtures, sdist/
wheel/isolated installed-wheel smoke lulus. Final executable build/offscreen
smoke exit0, PyInstaller6.22.3. Probe isolated wheel juga membuka ZIP editable10A,
merender PNG byte-identik dan PDF shadow fallback, exit0.

[Evidence JSON](evidence/segment10a-verification.json) menyimpan hasil JUnit,
versi, source/artifact hashes dan laporan executable. Tidak ada tes skipped
pada empat suite evidence.
```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv/Scripts/python.exe -m pytest tests/test_inspector_commands.py tests/test_inspector_panel.py tests/test_style_rendering.py -q --basetemp=artifacts/segment10a-offscreen --junitxml=artifacts/segment10a-offscreen.xml
$env:QT_QPA_PLATFORM = 'windows'
.venv/Scripts/python.exe -m pytest tests/test_inspector_panel.py tests/test_style_rendering.py -q --basetemp=artifacts/segment10a-native --junitxml=artifacts/segment10a-native.xml
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen
.cache/package-smoke/Scripts/python.exe -I artifacts/segment10a-wheel-probe.py
```

Canvas/PNG **exact** pada nested rotation/scale/stroke/radius/shadow. PDF raster2×:
max premultiplied channel **18/255**, interior **1/255**, report `[child]`.
Ukuran point integral menghindari pembulatan page pada perbandingan QtPdf.
Development downsample1× menunjukkan edge coverage sampai116/255/interior3/255;
tidak mengklaim exact pada semua sampling/viewer. Existing06A gate tetap utuh.

Python **3.12.12**, PySide6/Qt **6.10.2**, Pillow **12.3.0** benar-benar dipakai.
Pillow dikunci setelah install/tes, bukan versi contoh PRD. Tooling mengikuti lock;
executable memakai PyInstaller6.22.3.

Bukti `artifacts/segment10a-native/`:

- `test_palette_defaults_and_styl0/`: Inspector screenshot, editable native ZIP,
  PNG. Save/close/Open mempertahankan seluruh Document dan PNG exact.
- `test_real_alpha_color_dialog_a0/`: Mixed dan actual RGBA picker screenshot.
  Screenshot native ini benar-benar diperiksa.
- `test_shadow_shared_scene_png_p0/`: scene/shared/2× PNG, PDF/raster/report.json;
  PNG/PDF raster benar-benar diperiksa.
- JUnit di `artifacts/segment10a-*.xml`; full gate log
  `artifacts/segment10a-check.log`; build report mengikuti smoke-build.ps1.

## Demo, pending dan manual

Jalankan `powershell -ExecutionPolicy Bypass -File scripts/run.ps1`, buat artboard
dan dua rectangle. Pilih keduanya untuk Mixed; ubah Fill/slider, Undo/Redo,
Save As/Open. Pada nested rotated frame, X/Y anak mengikuti sumbu parent. Width/
Height group menjaga rasio. Gulir Inspector untuk foreground/background defaults.

Mouse/keyboard fisik, screen reader, perpindahan monitor/Windows DPI, viewer PDF
lain dan mesin rilis bersih **belum dilakukan**. Visual yang diperiksa berasal
dari aplikasi/test QTest Windows native, bukan klaim manual fisik.

Tidak ada blocker lingkup10A. Stroke bounds tebal/rotated square cap/miter,
empty-group shadow serta extreme finite shadow limits juga teruji. Existing08.layout menunggu13.
Constraints/export Inspector lengkap13/15–17, text11/image12, public MCP18/19,
acceptance22/performance23/clean release24 tetap pemilik. Limit buffer menolak
effect ekstrem; throughput dokumen besar belum dibuktikan. Berikutnya
**10B not_started**, snapping tidak dikerjakan.
