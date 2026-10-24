# Segmen 06 — shared drawing dan canvas navigation

23 Oktober 2026, Asia/Jakarta. Status verified untuk renderer dasar dan navigation. Revision dasar 54162c5; implementasi di working tree tanpa
commit otomatis. Tidak ada dependency baru, Python 3.12.12 / PySide6 Qt 6.10.2.

Modul: rendering/drawing.py dan rendering/canvas.py; integrasi Tab/Inspector pada
ui/window.py. Kontrak [ADR 0016](adr/0016-shared-painter-scene.md).
Checkpoint 06.drawing, 06.adapter, 06.navigation dan 06.verification.

Perintah reproduksi:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest tests/test_rendering.py -v
$env:QT_QPA_PLATFORM = 'windows'
.\.venv\Scripts\python.exe scripts/demo_renderer.py --capture artifacts/render06-window.png
```

Tanpa --capture demo tetap terbuka. Hasil shared image di artifacts/render06/shared.png,
native editable fixture di artifacts/render06/fixture.ltechdesign. Buka fixture itu
lewat GUI biasa juga memakai renderer sama. Grid/selection hanya overlay view.
Fixture dibuat dari domain valid dengan embedded shape data, bukan loader pengganti.

Bukti awal: tes isolation overlap alpha 128±1 termasuk overlap anak opaque, nested
alpha 64±1, z-order reorder, visibility, rounded clip, matrix dunia, stable identity
setelah edit, scene/shared image agreement di interior, Ctrl+wheel/pan, zoom bounds
dan snapshot/history tidak berubah. Limit output dan nested isolation diuji sebelum
alokasi besar. Tes pertama isolation limit salah memilih skala sehingga terkena
output limit lebih dahulu; input diperbaiki untuk menguji branch isolation khusus,
assertion limit tetap strict. Toleransi alpha 1 hanya quantization 8-bit; bukan
toleransi pixel-diff final 06A.

Demo native Windows benar-benar dijalankan dan screenshot diperiksa: group rotated
merah/biru overlap ber-opacity 0,5 di atas artboard putih; rounded rotated frame
hijau mengclip ellipse kuning. Screenshot bukan proof PDF/font/export. Pixel tests
memeriksa transparansi aktual pada target transparent, tidak hanya screenshot putih.

Manual lanjutan belum dilakukan: navigasi via mouse fisik pada beberapa monitor,
uji subjektif performa dokumen besar. Automated Qt events menguji navigasi dasar.
Renderer 06 tidak membuat drawing tools baru atau export dialogs. Text/image/SVG
dan shadow belum digambar lengkap: canvas memberi warning, strict preview/export
contract menolak unsupported feature. Serialization dan command undo tetap memakai
model utama; renderer mendengar snapshot terbaru. Render/export akhir di 06A/15–17,
text 11, image/SVG 12, style/shadow lengkap 10A.

Sesuai klarifikasi pengguna, **06A tidak dikerjakan pada sesi ini**, dan wajib
dijalankan sebelum perluasan drawing tools. Jangan mengklaim fixture canvas/PNG/PDF/
offscreen lengkap atau preview visual text/image sudah verified oleh segmen 06.

Hasil final aktual: scripts/check.ps1 offline exit 0, 324 core + 16 desktop (7 tes renderer baru), ruff check/format 52 files, mypy strict 49 files, fixture/docs/sdist/wheel dan installed-wheel smoke lulus. scripts/smoke-build.ps1 -SmokeMode offscreen exit 0 dengan PyInstaller 6.22.3. [Bukti executable](evidence/segment06-package-offscreen.json), [screenshot native](evidence/segment06-window.png), [shared image](evidence/segment06-shared.png). Seluruh checkpoint 06.drawing/adapter/navigation/verification verified pada scope dasar; aman melanjutkan 06A setelah instruksi pengguna. Tes mouse fisik/monitor manual dan conformance full 06A tetap pending.
