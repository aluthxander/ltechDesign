# Bukti segmen08 — Transform, clipboard dan grouping

Tanggal24 Oktober2026, Asia/Jakarta. Base Git23515f33714519cf732ded30e818ef9fc0ff0c28.
Working tree07 sudah berisi perubahan sebelum08; tidak ditimpa, PRD tidak diubah,
tidak ada commit otomatis. Status induk `blocked`; pekerjaan independen terverifikasi, checkpoint
08.layout `blocked` oleh evaluator constraints/layout13 yang belum tersedia.
Induk08 tidak verified selama checkpoint tersebut belum ditutup.

| Checkpoint | Status | Lingkup |
| --- | --- | --- |
| 08.transforms | verified | Move/resize/rotate, uniform group/multiselect, anchor/local/world, ephemeral wireframe dan single transaction |
| 08.editing | verified | Delete/duplicate/group/ungroup/reparent, nudge/z-order, context menu dan safe shortcuts |
| 08.clipboard | verified | Native structured MIME, validated dependencies/embedded assets, fresh IDs, atomic staged paste, cut setelah copy |
| 08.layout | blocked | Frame default fixed tersedia; evaluator untuk Constraints/Layout belum ada dan Project/Draft menolaknya. Pemilik13; tidak diarang atau dianggap lulus |
| 08.baseline | verified | Windows native100/1000 shape10 detik per fase direkam; hasil bukan klaim semua target NFR lulus |
| 08.handoff | verified | Full gate/native visual/spike lulus, blocker/integrasi dan evidence dicatat |

Kontrak detail: [ADR0019](adr/0019-editor-transform-clipboard.md).
Source: domain/editing.py, commands/contracts.py/planning.py/dispatcher.py,
persistence/clipboard.py, ui/transforms.py/editing.py/canvas.py/window.py.
Cache scene di rendering/canvas.py dan staging cleanup di assets/store.py.
Tidak mengubah format native atau menambah dependency. Renderer/content export
tetap memakai snapshot domain dan shared drawing yang sudah ada.

## Bukti aktual final

Tes targeted terbaru **15 passed (8 core+7 GUI)**, termasuk actual PNG AT24 dengan
maximum byte-channel delta≤1/255 setelah group/reparent/ungroup dan undo hierarchy
persis. Full gate offline `scripts/check.ps1` **exit0, 352 core+53 desktop passed**,
tanpa skipped; Ruff check/format70 files, mypy66 files, fixture/docs/format audit,
sdist/wheel build dan isolated installed-wheel domain/native/GUI smoke lulus.
Log final: artifacts/segment08-check-final.log, artifacts/core.xml, artifacts/desktop.xml.
Tujuh tes GUI baru diulang pada platform Windows native: **7 passed (1,48s)**,
artifacts/segment08-native.xml. Capture handles/context menu Windows native dan
PNG AT24-before/after di artifacts/editing08 benar-benar diperiksa.

Spike executable `scripts/smoke-build.ps1 -SmokeMode offscreen`: build/runtime
exit0, PyInstaller6.22.3, report artifacts/segment01a-offscreen.json dan log
artifacts/segment08-spike-final.log. Ini startup/close executable, bukan manual release
drawing pada Windows bersih. Conformance06A canvas/PNG/PDF/QGui offscreen juga
diulang di full gate, dengan toleransi yang sama dan tanpa melonggarkan tes.
Versi aktual: Python3.12.12, PySide6/Qt6.10.2, pytest8.4.2, pytest-qt4.5.0,
ruff0.14.0, mypy1.18.2, PyInstaller6.22.3. Tidak ada dependency baru.

Benchmark debug1 detik menemukan selection1000 freeze225ms, lalu jalur deselect
individual dapat mencapai638ms. Profil membuktikan repeated projection dan Qt
selection satu per satu; cache immutable/projection serta bulk selection diterapkan.
Debug terbaru sebelum final10 detik: gap1000 maksimum53,53ms; data debug disimpan
di artifacts/segment08-benchmark-debug*.json. Ini investigasi, bukan baseline final.

Pengujian clipboard offscreen memerlukan cleanup clipboard milik tes saat teardown
agar QMimeData tidak menahan shutdown interpreter; assertion data/undo tidak dihapus.
Tes binding/reference, format, asset staging dan history lama tetap dijalankan.

## Baseline ringan20.5

Evidence pengukuran kedua tersimpan di [segment08-benchmark.json](evidence/segment08-benchmark.json),
salinan artifacts/segment08-benchmark.json dan artifacts/segment08-benchmark-final.log.
[Run pertama](evidence/segment08-benchmark-run1.json) dipertahankan sebagai pembanding,
bukan dipilih hanya run tercepat. Setiap run mengukur10detik/fase native Windows11
build26300, Intel Core i5-13450HX,16 logical processor, RAM34.053.414.912 byte;
tipe disk belum diverifikasi. Qt melaporkan DPR1,25/1,5 pada dua display; tidak
membuktikan perpindahan monitor fisik. Bukan perangkat acuan4-core/16GiB atau
cold/release benchmark23. Source SHA256 tercatat di JSON (working tree, bukan commit).

| Fixture/fase10detik | Sampel interval | p95 ms | p99 ms | Gap terpanjang ms | Freeze excess di atas16ms |
| --- | --- | --- | --- | --- | --- |
| 100 shapes pan | 625 | 16,45 | 16,83 | 17,15 | 1,15 |
| 100 shapes drag | 625 | 16,49 | 16,84 | 17,05 | 1,05 |
| 1000 shapes pan/selection | 609 | 16,90 | 48,04 | 53,30 | 37,30 |

Timer16ms dipakai sebagai pacer; setiap callback melakukan actual viewport repaint.
JSON juga menyimpan callback+repaint p95/p99/max terpisah (100 pan3,56/4,01/4,50ms,
100 drag3,64/4,70/9,00ms,1000 pan-selection16,30/47,97/53,20ms). Drag10 detik
memiliki **satu history entry**, release+GUI commit11,41ms; admission12,28/8,39/63,76ms
dicatat di luar interval fase. Gap event dan excess disimpan terpisah agar freeze
tidak disamarkan oleh waktu timer.

Batch100 pada dokumen1000 shape: commit-only tanpa subscriber GUI,3 sampel,
p95/p99/max **49,16ms** (target≤500ms). GUI command91,23ms; heartbeat berikutnya
**110,69ms**, sehingga target respons100ms **belum tercapai** dan tetap pekerjaan
optimisasi/pembuktian23. Tidak menaikkan budget atau mengklaim semua NFR lulus.
Resident fixture1000=94.765.056byte; tiga putaran open/close sesudahnya mencatat
97.685.504/97.992.704/97.968.128byte. Di bawah512MiB pada host ini, tetapi tiga
putaran tidak cukup untuk menyimpulkan bebas leak jangka panjang.

Run pertama:100pan/drag p95=16,84/16,77ms,1000 p99/gapmax=48,73/54,03ms,
batch100 commit48,29ms dan GUI heartbeat111,07ms. Kedua run gagal target100ms yang
sama; tidak ada perubahan ambang. Hash source benchmark kedua mengacu sumber
sesaat sebelum perbaikan context menu yang mempertahankan pilihan group saat
klik kanan mengenai child. Perbaikan itu tidak mengubah jalur pan/drag/batch
yang diukur; full gate kode final dijalankan sesudahnya.

## Reproduksi

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv/Scripts/python.exe -m pytest tests/test_editing_commands.py tests/test_editor_transforms.py -q --junitxml=artifacts/segment08.xml
$env:QT_QPA_PLATFORM = 'windows'
.venv/Scripts/python.exe -m pytest tests/test_editor_transforms.py -q --junitxml=artifacts/segment08-native.xml
.venv/Scripts/python.exe scripts/benchmark_editor.py --seconds 10 --output artifacts/segment08-benchmark.json
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen
```

Demo: scripts/run.ps1 → New/artboard → draw shapes → Select. Drag body untuk move;
handles untuk resize, lingkaran di atas untuk rotate. Shift menjaga rasio/snap15°;
Alt resize dari pusat. Ctrl+G/Shift+Ctrl+G, Ctrl+D, Delete, Ctrl+C/X/V,
Ctrl+]/[, panah/Shift+panah; klik kanan membuka context menu dan Reparent.
Esc membatalkan preview. Ctrl+Z/Shift+Ctrl+Z untuk undo/redo saat fokus canvas.

Pemeriksaan visual screenshot native sudah dilakukan; gesture/input tes memakai
event Qt otomatis. Mouse fisik, screen reader, monitor lintas DPI, cold/reference
machine dan Windows rilis bersih belum diuji. Text/image editing tetap11/12,
clipboard image lintas aplikasi38A, production export/jobs15–17, MCP18/19,
acceptance22 dan benchmark menyeluruh23. Segmen09 tidak dijalankan otomatis.

Skenario manual yang belum dijalankan dengan mouse/keyboard fisik: buat dua shape
di nested rotated frame, move/resize/rotate dengan Shift/Alt dan Esc; group lalu
klik kanan child untuk ungroup/reparent; copy/cut ke tab baru, tutup sumber, save,
open dan undo/redo; ketik nama objek sambil memakai panah/Delete/Ctrl+Z untuk
memastikan editing teks tidak mengubah konten canvas. Skenario otomatis sepadan
telah dijalankan, tetapi tidak diklaim sebagai pemeriksaan input fisik.

Prasyarat spesifik penutupan08: evaluator Constraints/Layout di13 beserta admission
dan validation yang kini menolak layout di domain/validation.py dan
commands/planning.py. Jalur ResizeNode/ScaleNodes sudah fail-closed; perlu pengujian
ulang frame resize+layout+undo satu transaksi setelah evaluator nyata tersedia.
Prasyarat hierarchy/commands untuk pekerjaan Pages/Layers09 yang independen sudah
tersedia, tetapi itu tidak membuat induk08 verified atau mengotorisasi09 otomatis.
