# Baseline segmen12 — Portable image import

Tanggal25 Oktober2026, Asia/Jakarta. Status `verified` untuk lingkup12.
Base HEAD `3f7a785dee15c9d5b61eaa6f207f9dd07412bb1a`
(`feat : segmen 11`), working tree awal bersih, tanpa commit otomatis/ubah PRD.
Checkpoint12.import/render/editor/retention/baseline/handoff hanya lingkup12;
13 tidak dikerjakan. Existing08.layout tetap blocked pada evaluator13.

File dialog dan local Copy drag/drop mengimpor PNG/JPEG/WebP/SVG lewat worker
staging ke BlobStore dan RegisterAsset+Create/SetMedia atomik. Thumbnail gallery,
place embedded asset, centered fit/fill/stretch, normalized non-destructive crop,
radius, rotation, opacity, raster↔SVG replace tanpa mengubah container tersedia.
Shared canvas/PNG/PDF memakai original embedded assets; SVG static geometry direkam
sebagai drawing vector, bukan preview flatten. Crop/replace/Save/Open mempertahankan
ID/geometry/style dan editable data. [Kontrak/subset](image-import.md),
[ADR0024](adr/0024-portable-media-import.md).

File utama: assets/importing.py/store.py/validation.py, commands/contracts.py dan
planning.py (`SetMedia` tanpa Qt), rendering/media.py/drawing.py/text.py/fonts.py,
ui/images.py/canvas.py/Inspector/window.py dan adapter clipboard internal editing.py.
Tes tests/test_media_commands.py/test_images.py, harness check_image_conformance.py,
benchmark_editor.py --images dan packaged codec smoke. Dependency tidak berubah:
Python3.12.12, PySide6/Qt6.10.2, Pillow12.3.0; PyInstaller6.22.3 untuk spike.

## Reproduksi dan demo

```powershell
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run.ps1
```

File → Import images (`Ctrl+Shift+I`) atau drop file lokal. Pilih image, ubah mode
dan normalized crop di Inspector, Apply crop/Reset crop. Scroll Inspector untuk
radius/rotation/opacity. Replace image mempertahankan container/crop/fit. Undo/redo,
Save .ltechdesign, pindahkan file sumber, Open kembali dan edit crop lagi. Thumbnail
gallery dapat discroll dan double click menempatkan ulang embedded asset.

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv/Scripts/python.exe -m pytest tests/test_images.py tests/test_media_commands.py -q --junitxml=artifacts/segment12-targeted.xml
$env:QT_QPA_PLATFORM = 'windows'
.venv/Scripts/python.exe -m pytest tests/test_images.py tests/test_style_rendering.py tests/test_editor_transforms.py -q --junitxml=artifacts/segment12-native-final.xml
.venv/Scripts/python.exe scripts/check_image_conformance.py --output artifacts/images12-demo
.venv/Scripts/python.exe scripts/check_image_conformance.py --heavy --output artifacts/images12-heavy
.venv/Scripts/python.exe scripts/benchmark_editor.py --seconds 10 --output artifacts/segment12-benchmark-shapes-final.json
.venv/Scripts/python.exe scripts/benchmark_editor.py --images --seconds 10 --output artifacts/segment12-benchmark-images-final.json
Remove-Item Env:QT_QPA_PLATFORM
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen
$env:QT_QPA_PLATFORM = 'offscreen'
.cache/package-smoke/Scripts/python.exe -I scripts/check_image_conformance.py --verify artifacts/images12-final/portable.ltechdesign --output artifacts/images12-wheel
```

Harness output memakai direktori baru agar fixture native lama tidak ditimpa.
Native fixture di artifacts/images12-final/portable.ltechdesign memuat4image asset
(PNG/JPEG/WebP/SVG); file asal sudah diubah namanya menjadi*.moved. Native/app
screenshot, shared.png, actual shared.pdf dan pdf-raster.png ada di direktori itu.
Wheel --verify tidak membaca sumber*.moved dan tidak bergantung cwd package source.

## Hasil aktual dan batas pembuktian

- Targeted **38passed** (2core+36desktop), native **53passed** (36image+17regresi
  style/transforms), masing-masing **36passed** pada QT_SCALE_FACTOR1.5/2.
  Probe native aktual DPR1.25/1.875/2.5; faktor tersebut bukan klaim OS DPI fisik.
- Final `scripts/check.ps1` offline exit0: **420core+160desktop**, Ruff102files/
  mypy98, fixtures/docs/build/installed-wheel lulus. Log artifacts/segment12-check-final.log.
- Canvas==PNG exact termasuk nested rotation/ancestor rounded clip, source crop,
  isolated image/group opacity. PDF opaque interior error≤2/255 pada fixture
  transform; SVG opaque PDF tidak punya image XObject, isolation dilaporkan.
  Native/offscreen/wheel dan tiga DPR menghasilkan shared PNG SHA256 sama:
  `0456b7ef1cc18b7608b0934993ad4dabd5480fd8b76cc96e78ea3426086c7707`.
- Editable ZIP roundtrip setelah crop+replace dan source move, malformed raster,
  MIME mismatch, hostile/unsupported SVG, APNG/animation, EXIF orientation,
  size/header/actual/budget guards, atomic multi-file rollback, cancel setelah
  staging/late cancel, stale revision/page/closed session dan worker result commit
  pada GUI thread diuji. Existing clipboard node internal kini juga menyiapkan
  media sebelum publication; itu bukan clipboard image lintas aplikasi38A.
- AT-25 real store: replace lalu remove old asset/delete/new asset/cleanup masih
  dapat undo/redo; independent snapshot lease menahan bytes setelah dispatcher
  close. Sesudah lease terakhir dilepas, dua blob dapat dikoleksi. Disk recovery14
  belum dibuat dan tidak diklaim selesai.
- Impor PNG nyata **36MP**, cancel20ms yang diminta melalui event loop, selesai
  **180.64ms**, **29heartbeat**, gap maksimum **38.60ms**, nodes/staging/blobs0.
  Codec read tunggal tidak preemptible; GUI tetap memproses event. Bukti
  artifacts/images12-heavy-final/report.json. Run ini bersamaan build (bukan baseline FPS).
- Executable build lulus, semua PNG/JPEG/WebP encoder+decoder dan SVG vector
  record/replay benar-benar dijalankan dalam paket dengan PATH/Qt env dibersihkan.
  Evidence berisi DLL/plugin/executable hashes; log artifacts/segment12-build-final.log.
- Screenshot native aplikasi dan actual PDF raster benar-benar diperiksa;
  bukan klaim mouse/keyboard/Explorer fisik atau viewer PDF independen.

## Baseline ringan setelah renderer image aktif

Warm Windows11 build26300, i5-13450HX,16logicalCPU,32GiBRAM, Qt Windows DPR1.25.
Jenis disk tidak diverifikasi; ini development host, bukan mesin rilis acuan.
Masing-masing phase10detik; baseline final tidak bersamaan dengan build.
Source hash kedua baseline `ca5feacaa731cbffc6105db7c20f941cb2c8346049e2568fbc168ed8948c91fd`.

| Ukuran / phase | Shapes p95 / p99 / max ms | 80%shape+10%raster+10%SVG p95 / p99 / max ms |
| --- | --- | --- |
|100 pan|16.74 / 17.03 / 23.88|16.78 / 17.00 / 17.20|
|100 drag|16.72 / 17.13 / 28.39|16.79 / 17.16 / 26.71|
|1000 pan/selection|23.65 / 133.94 / 164.84|21.78 / 110.40 / 120.14|

Batch100 commit-only47.18ms shapes/54.44ms mixed; GUI command101.16/88.89ms dan
heartbeat123.50/117.98ms. RSS repeated open/close≈103.8–105.2MB shapes dan
106.8–107.8MB mixed, tanpa asset raster besar. Error list kedua run kosong.
Target100shape p95≤20ms tercapai; **1000selection gap≤100ms dan batch GUI response
≤100ms belum tercapai**. Tidak menurunkan target atau menganggap seluruh NFR
performance verified. Ini melanjutkan pending08, pemilik optimasi23; bukan blocker
portabilitas/fitur12 atau pekerjaan layout13 yang independen. Bukti penuh termasuk
callback/repaint dan release commit tersimpan di dua JSON baseline.

Manual yang belum dilakukan: Explorer drag/drop dan file dialog dengan mouse fisik,
keyboard navigation/screen reader, crop pada monitor/DPI OS berbeda, memory stress
beberapa dokumen besar, viewer PDF independen dan clean Windows release machine.
Skenario manual: import empat format ke rotated frame, crop/fill/radius/opacity,
replace raster↔SVG, undo/redo; pindahkan sumber lalu buka .ltechdesign dan edit lagi;
drop malformed/SVG unsafe dan cancel image besar, periksa tab/dirty state tetap.
Acceptance22/performance23/release24 tetap pemilik; production export jobs15–17,
MCP18/19, recovery14 dan external image clipboard38A tidak dikerjakan di12.

Berikutnya13 `not_started`. Aman melanjutkan scope/prasyarat13; tidak dijalankan
otomatis. [Evidence12](evidence/segment12-verification.json).
