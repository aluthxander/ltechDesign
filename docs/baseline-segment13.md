# Baseline segmen 13 — Stack layout dan constraints MVP

Tanggal 26 Oktober 2026 (Asia/Jakarta). Base HEAD `db9fe72`; working tree awal
bersih. Tidak ada commit otomatis. Status `verified` untuk subset MVP13.

Checkpoint `13.engine`, `13.commands`, `13.inspector`, `13.integration`,
`13.handoff`: seluruhnya `verified`. Tidak ada blocker lingkup13.
Kontrak lengkap: [ADR 0025](adr/0025-deterministic-stack-layout.md).

Source: domain/layout.py; commands contracts/planning/dispatcher; shared text
measured port; ui/layout.py, Inspector dan window. Tidak ada renderer layout
kedua. Geometry derived disimpan native1.0 dan dikonsumsi shared drawing existing.

## Verifikasi aktual final

- `.venv/Scripts/python.exe -m pytest tests/test_layout_commands.py -q`: 39 passed.
- Offscreen `pytest tests/test_layout_panel.py -q`: 7 passed. Mencakup Inspector
  padding/gap/alignment/constraints, actual Qt text reflow/nested hug, pointer
  resize satu undo, inline text dan native read-only reopen/PNG/PDF adapter.
- `python scripts/demo_layout.py --capture`: exit0, platform windows, native
  Inspector screenshot dan shared PNG/PDF raster benar-benar dilihat. PDF interior
  colors toleransi <=2/255. Artifact di `artifacts/layout13/` (gitignored).
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1 all`,
  `UV_OFFLINE=1`: exit0; **459 core +167 desktop**, Ruff107/mypy103, fixture,
  documentation audit, sdist/wheel dan isolated installed-wheel smoke lulus.
  Log `artifacts/segment13-check.log`, XML core.xml/desktop.xml.
- Native `pytest tests/test_layout_panel.py tests/test_editor_transforms.py
  tests/test_inspector_panel.py -q --junitxml=artifacts/segment13-native.xml`:
  **22 passed**. Final targeted kedua file layout: **46 passed** (39core+7GUI),
  `artifacts/segment13-targeted.xml`. Native Inspector actual DPR1.25.
- Sesudah final root-parent constraint control guard: mypy103, Ruff check,
  format107, native22/targeted46 lulus; `check.ps1 package` diulang exit0
  (`artifacts/segment13-package.log`). Tidak mengandalkan wheel sebelum guard.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1
  -SmokeMode offscreen`: build/start/codec/close **exit0**, PyInstaller6.22.3,
  `artifacts/segment13-spike.log`, segment01a-offscreen.json. Ini executable
  offscreen di development host, bukan uji fisik mesin rilis.
- Installed wheel `.cache/package-smoke/Scripts/python.exe -I
  scripts/demo_layout.py --capture --output artifacts/layout13-wheel`: exit0.
  PNG wheel/native identik, SHA256
  `f0ecdb62f1aac695485022d0c1db3cc75fc7bf65121d07339c714fd1dbd18364`.
  Actual PDF raster interior delta<=2/255. Screenshot/PNG/PDF dilihat, tidak hanya
  memeriksa header file. Demo native dijalankan ulang sesudah final UI guard.
- Versi aktual: Python3.12.12, PySide6/Qt6.10.2, Pillow12.3.0,
  pytest8.4.2/pytest-qt4.5.0, Ruff0.14.0, mypy1.18.2. Tidak ada dependency baru.
- Full gate pertama menemukan fixed-text limit guard terlewat saat ekstraksi
  measured port. Guard dipulihkan, tes limit asli tetap tanpa perubahan dan lulus
  pada rerun. Log pertama disimpan `segment13-check-initial-failed.log`.
- [Evidence/hash](evidence/segment13-verification.json) mengikat source/artifact
  final ke base revision. 08.layout dan induk08 kini `verified`; semua checkpoint
  lainnya sudah verified. Benchmark/physical acceptance pending tidak dinaikkan.

## Demo dan manual

Jalankan `uv run --locked python scripts/demo_layout.py` atau `scripts/run.ps1`.
Demo menghasilkan `artifacts/layout13/demo.ltechdesign`, shared.png/shared.pdf dan
inspector.png; file editable dapat dibuka di aplikasi. Pilih frame/artboard pada
Inspector, pilih stack/direction, padding T,R,B,L, gap, align dan sizing; Apply.
Pilih anak dalam parent bebas untuk start/end/center/stretch lalu resize parent.
Resize lebar stack fixed untuk melihat fill/text wrap dan Ctrl+Z/Ctrl+Shift+Z.

Manual fisik belum dilakukan: keyboard/mouse manusia, screen reader, perpindahan
monitor/DPI OS, viewer PDF lain dan clean Windows release. Tes native memakai
QTest/signal, bukan klaim uji fisik. Performance target 1000 node tetap segmen23.
Public export jobs15–17, recovery14, MCP18–19 dan advanced layout28 tetap pemilik.
Tidak ada prasyarat hilang untuk subset13. Segmen berikutnya14 tidak dijalankan.
