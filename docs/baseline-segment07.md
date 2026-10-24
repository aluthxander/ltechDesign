# Bukti segmen 07 — Artboard, drawing, selection

Status `verified` untuk lingkup segmen 07. Tanggal 24 Oktober 2026 (Asia/Jakarta).
Baseline Git aktual `23515f33714519cf732ded30e818ef9fc0ff0c28`; perubahan sesi ini
belum di-commit. Tidak mengubah prd.md atau melanjutkan segmen 08.

Checkpoint 07.artboards, 07.gestures, 07.selection dan 07.handoff semuanya `verified`.
Kontrak rutin ada di [ADR 0018](adr/0018-drawing-and-selection.md).

## Implementasi

- domain/authoring.py: 11 preset PRD, custom px/mm/cm/in, DPI/orientasi/background,
  pure node factories dengan canonical line/polygon payload. Schema tidak berubah.
- ui/artboard.py dan ui/canvas.py: intent form, lima drawing tools, preview overlay,
  satu Create/revision/undo saat release, cancellation dan session selection.
- rendering/hit_testing.py memakai path/world transform/clip shared renderer;
  ui/window.py menghubungkan toolbar, Layers, dispatcher, Save/Open yang sudah ada.
- Text/image tidak memiliki tool dummy; pemilik 11/12. Tidak menambah resize,
  rotate, clipboard, grouping, hide/lock toggles atau page management milik 08/09.

## Verifikasi

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv/Scripts/python.exe -m pytest tests/test_authoring.py tests/test_drawing_tools.py -q --junitxml=artifacts/segment07.xml
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
$env:QT_QPA_PLATFORM = 'windows'
.venv/Scripts/python.exe -m pytest tests/test_drawing_tools.py -q --junitxml=artifacts/segment07-native.xml
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen
```

Hasil aktual final: targeted **47 passed** (20 core + 27 GUI); full gate exit0,
**344 core + 46 desktop passed**, tanpa skipped. Ruff check/format63 files dan
mypy59 files lulus. Fixture generation, schema/round-trip, audit docs/links/status,
sdist/wheel build, isolated installed-wheel domain/native/GUI smoke semuanya lulus.
27 tes GUI baru juga lulus pada Windows native (2,35s). Uji conformance06A pada
full gate menjalankan child QApplication Windows dan QGui offscreen, PNG/PDF,
geometri/clip/alpha/text metrics dengan toleransi sebelumnya tanpa perubahan.

Log akhir: artifacts/segment07-check-final.log, artifacts/segment07-native.xml,
artifacts/segment07-desktop.xml, artifacts/core.xml, artifacts/desktop.xml.
Spike executable final **exit0**, build dan runtime smoke lulus; log
artifacts/segment07-spike-final.log dan report artifacts/segment01a-offscreen.json.
Dependency yang benar-benar diuji: Python3.12.12, PySide6/Qt6.10.2, pytest8.4.2,
pytest-qt4.5.0, ruff0.14.0, mypy1.18.2, PyInstaller6.22.3; tidak menambah dependency.

Verifikasi awal menemukan benturan nama width/height dengan method QWidget dan
callback teardown harness yang salah; keduanya diperbaiki, lalu seluruh gate
diulang lulus. Notifikasi revision-cancel sempat tertimpa refresh; queued GUI
connection dan regresi actual status bar kini membuktikan pesan tetap terlihat.

Cakupan yang benar-benar diuji: semua preset dan konversi fisik, artboard1080×1350, lima tools
pada zoom0.5/1/2/4 dengan pan, nested rotated/scaled frame, single undo/redo,
preview tanpa konten/history/scene-export, cancellation, ellipse/line path/rounded clipping,
hidden/locked ancestor, multiselect/marquee/select all dan page routing,
native Save/Open posisi/ID/hierarchy/data yang sama, custom metadata reload.
Shape baru termasuk nested ellipse di frame dan horizontal line; modifier Shift
dan Ctrl, page/tab switch serta toleransi hit zoom/DPR diuji eksplisit.

Artifact lokal di artifacts/drawing07: fixture.ltechdesign editable, shared.png,
shared.pdf, editor-windows.png/editor-offscreen.png serta dialog screenshot.
Artifact hasil tes tidak disimpan Git. Offscreen screenshot dapat memakai font
kotak pada host ini; pemeriksaan teks/UI mengacu platform Windows native.

## Demo dan manual

Jalankan `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run.ps1`.
New → Artboard preset/custom → Instagram Portrait → OK; pilih tool lalu drag.
Select: click, Shift/Ctrl multiselect, drag marquee, Ctrl+A saat fokus canvas.
Middle mouse pan, Ctrl+wheel zoom; Esc/right click membatalkan drawing.
Ctrl+Z/Shift+Ctrl+Z undo/redo; Ctrl+S, close, Open file .ltechdesign.
Fixture tes bisa dibuka dari artifacts/drawing07/fixture.ltechdesign.

Screenshot native Windows benar-benar diperiksa; interaksi tes memakai event Qt
otomatis. Mouse/keyboard fisik, monitor multi-DPI dan mesin Windows bersih belum
diuji manual. Daftar cek manual: drag tiap tool pada zoom berbeda, nested frame,
Esc saat preview, marquee dan hidden/locked dari file yang sudah memiliki state
tersebut, Save/close/Open lalu bandingkan posisi.

Integrasi serialization/undo/shared canvas/PNG/PDF proof memakai implementasi yang
sudah ada. Dialog/service export produksi, multipage, jobs/cancellation tetap15–17;
MCP attached/headless tetap18/19; full acceptance22, performance23, clean release24.
Tidak ada blocker prasyarat; berikutnya08 tetap not_started sampai instruksi pengguna.
