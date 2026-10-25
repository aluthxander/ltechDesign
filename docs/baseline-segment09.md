# Bukti segmen09 — Pages dan Layers

Tanggal24 Oktober2026 (Asia/Jakarta). Status **verified** untuk lingkup09.
Base revision aktual
`d05a7e171d070987eddf091cd7b21a4f1ad5c06f`; working tree awal09 bersih. Tidak
membuat commit otomatis atau mengubah PRD. 08.layout tetap blocked oleh evaluator13;
tidak diperlukan untuk pekerjaan hierarchy09 dan tidak diimplementasikan di sini.

| Checkpoint | Status | Lingkup |
| --- | --- | --- |
| 09.commands | verified | Page CRUD/duplicate, state flags, stable IDs/refs, relocation atomic/world geometry/undo, optional workspace cleanup |
| 09.panel | verified | Pages/artboard list, tree bertingkat, rename/duplicate/hide-lock, search/type/collapse per tab, bidirectional selection |
| 09.drag | verified | Real Qt drag/drop event path, reverse visual z-order, nested world pose, stale/cycle/context guards |
| 09.handoff | verified | Full gate, native visual, executable spike dan dokumen final |

Keputusan rutin/kontrak baru di [ADR0020](adr/0020-pages-and-layer-projection.md).
Source utama commands/contracts.py/planning.py/dispatcher.py, ui/hierarchy.py,
integrasi ui/window.py dan focus guard ui/editing.py. Domain model tetap bebas Qt.
Serialization dan shared renderer yang sudah ada mengonsumsi perubahan snapshot;
tidak menambah schema/format version, dependency, MCP server atau layout evaluator.

## Bukti aktual final

- Targeted **18 passed** (8 core+10 GUI), artifacts/segment09.xml.
- Windows native **10 passed (1,40s)**, artifacts/segment09-native.xml.
- `scripts/check.ps1` offline **exit0**: **360 core+63 desktop passed**, tanpa
  skipped. Ruff check/format73 files, mypy69 files, fixture/schema/inventory/docs,
  sdist/wheel build dan installed-wheel domain/native/desktop smoke lulus. Log
  artifacts/segment09-check-final.log, artifacts/core.xml, artifacts/desktop.xml.
- `scripts/smoke-build.ps1 -SmokeMode offscreen`: build dan executable startup/
  close melalui event loop **exit0**, PyInstaller6.22.3. Log artifacts/segment09-spike-final.log,
  report artifacts/segment01a-offscreen.json. Tidak mengklaim manual drawing pada
  executable atau mesin Windows rilis bersih. Full gate juga mengulang conformance
  canvas/PNG/PDF/QGui offscreen06A tanpa mengubah toleransi.
- Versi aktual diuji: Python3.12.12, PySide6/Qt6.10.2, pytest8.4.2,
  pytest-qt4.5.0, ruff0.14.0, mypy1.18.2, PyInstaller6.22.3. Tidak ada dependency baru.
- Screenshot artifacts/hierarchy09/panel-windows.png benar-benar diperiksa:
  Pages, daftar artboard, tree nested, search/type dan Shown/Locked terbaca.
  Native fixture memuat text/image/shadow yang renderer pemilik11/12/10A belum
  mendukung; warning/placeholder sebelumnya tetap ada, tidak diklaim selesai09.

Tes membuktikan page aktif stabil saat command menyisipkan page di depan,
session selection tidak menaikkan revision, fallback/undo page deletion, last-page
guard dan penghapusan isi eksplisit, graph/token binding remap dan asset/font
references saat duplicate, ZIP save/reload embedded bytes, optional workspace
reference cleanup dan penolakan callback layout yang mengubah workspace sendiri.
Layer tests memakai actual QDragEnterEvent/QDragMoveEvent/QDropEvent pada viewport,
matriks dunia pada parent berotasi, pixel PNG serta scene z-value setelah reorder,
undo/redo, empty-group normalization, hidden/locked ancestry, search ancestor,
selection signal count, external command pada active/inactive tab, rename inline
serta revision eksternal ketika editor masih terbuka. Caller eksternal adalah
dispatcher lokal yang nyata; tidak mengklaim transport MCP18/19 telah tersedia.

Riwayat harness: tes pertama sempat memakai Save pada fixture sumber yang memiliki
path; fixture tersebut dikembalikan byte-identik ke HEAD yang bersih sebelum09.
Tes final membuka salinan di tmp_path dan memakai Save As; fixture repo tidak lagi
ditulis. Satu tes juga sempat mengirim parent snapshot lama dengan children kosong;
guard structural_update_forbidden bekerja, dan tes diperbaiki memakai node terbaru.
Tidak melemahkan guard/model test untuk membuat pemeriksaan lulus.

## Reproduksi dan demo

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv/Scripts/python.exe -m pytest tests/test_hierarchy_commands.py tests/test_hierarchy_panel.py -q --junitxml=artifacts/segment09.xml
$env:QT_QPA_PLATFORM = 'windows'
.venv/Scripts/python.exe -m pytest tests/test_hierarchy_panel.py -q --junitxml=artifacts/segment09-native.xml
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run.ps1
```

New → +Page/Rename/Duplicate/Delete pada Pages; artboard dibuat lewat toolbar yang
sudah tersedia. Artboard list memilih/fit objek. Layers: F2/double-click untuk
rename; checkbox Shown/Locked; klik kanan duplicate/rename/administrasi flags;
drag Above/Below/OnItem untuk reorder/reparent. Undo/redo memakai Edit atau shortcut
canvas/Layers yang sudah ada. Pilih nama/tipe di search; pilih objek lain dari
canvas untuk mengungkap path bila filter menyembunyikannya.
Fixture editable hasil pengujian di artifacts/hierarchy09/fixture.ltechdesign.

Skenario manual yang belum dijalankan dengan input fisik: create/rename/duplicate/
delete page berisi node dan undo; drag nested layer dengan keyboard modifiers,
reorder dua shape overlap dan lihat z-order; toggle hidden/locked ancestor lalu
filter/reveal selection; rename inline sambil memakai Ctrl+Z/arrow/Delete;
Save As/close/Open salinan proyek dan periksa embedded assets. Event Qt otomatis
telah menguji skenario setara; tidak diklaim sebagai mouse fisik/multi-monitor.

Integrasi tertunda: style/shadow10A, snapping/alignment10B, text11/image12,
layout13 (termasuk08.layout), public export/jobs15–17, SDK/MCP18/19, acceptance22,
performance23/clean Windows24. Baseline08/NFR latency111ms tetap historis/pending23;
09 tidak mengklaim penutupan target performa yang belum diukur ulang. Berikutnya
10A not_started; tidak dijalankan otomatis.

Tidak ada blocker09. Infrastruktur09 siap untuk pekerjaan10A setelah instruksi
pengguna. Penutupan09 tidak menaikkan08.layout atau gate MVP/release menjadi verified.
