# Baseline segmen11 — Text dan typography

Tanggal25 Oktober2026. Status `verified` untuk11.commands/layout/editor/handoff, base HEAD `f1918d2d28f2139f31fe4d2f5cc1a65ff533cc95`, working tree awal bersih. Tanpa commit otomatis atau perubahan PRD; hanya segmen11. Prasyarat10A/10B/induk10 sudah verified. Existing08.layout tetap blocked pada13, tidak menghalangi typography.

Text tool klik membuat auto_width; drag membuat fixed box, termasuk parent berotasi. Double click/F2 mengedit inline, Enter newline; Esc/Ctrl+Enter selesai. Ctrl+C/X/V/Delete mengedit teks; Ctrl+Z/Y memakai document history. Typography Inspector menyediakan local family, size/weight/italic, horizontal/vertical alignment, baseline line height dengan multiplier/px, absolute letter spacingpx, fixed/auto_width/auto_height; fill RGBA dan opacity memakai kontrol10A. Mixed selection/invalid input eksplisit. Pilihan font tidak menimpa metadata font hilang tanpa tindakan pengguna.

Domain command dan shared text layout/renderer terhubung serialization1.0 dan PNG/PDF service06A. Auto-size dihitung atomik sebelum revision/history publication; fixed box resize/wrapping, group bounds/opacity, fallback dan glyph warnings memakai logika bersama. IME composition hanya preview canvas; PNG, scene.render dan PDF memakai dokumen yang sudah commit. Kontrak dan batas di [ADR0023](adr/0023-inline-text-and-layout.md).

File utama: domain/typography.py, commands contracts/planning/dispatcher, rendering/text.py/fonts.py/drawing.py/pdf.py/canvas.py, ui/text_editing.py/typography.py/canvas.py/Inspector/window. Tes domain/layout/editor/conformance dan scripts/check_text_conformance.py. Tanpa dependency baru: Python3.12.12, PySide6/Qt6.10.2, Pillow12.3.0.

## Reproduksi

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.cache/uv'
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run.ps1
```

Klik Text atau T saat canvas fokus. Buat box, ketik multiline, Esc; ubah Typography/Fill/Opacity di Inspector. Resize width untuk wrapping atau pilih auto_height. Undo/redo lalu Save/Open `.ltechdesign`; semua teks, typography, ID dan embedded font tetap editable. Font system harus terpasang lokal untuk hasil yang sama; metadata dan warning tetap ada jika hilang.

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
uv run --locked --offline pytest tests/test_typography_commands.py tests/test_text_layout.py tests/test_text_editor.py tests/test_text_conformance.py --junitxml=artifacts/segment11-targeted.xml
$env:QT_QPA_PLATFORM = 'windows'
uv run --locked --offline pytest tests/test_text_editor.py tests/test_text_layout.py tests/test_inspector_panel.py tests/test_editor_transforms.py --junitxml=artifacts/segment11-native.xml --basetemp=artifacts/text11-gui
Remove-Item Env:QT_QPA_PLATFORM
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen
$env:QT_QPA_PLATFORM = 'offscreen'
.cache/package-smoke/Scripts/python.exe -I scripts/check_text_conformance.py --mode offscreen --output artifacts/text11-wheel
```

## Bukti dan batas

Hasil aktual: `scripts/check.ps1` offline exit0, **418core+124desktop**, Ruff96/mypy92 files, fixtures/docs/build/package/installed-wheel lulus; log artifacts/segment11-check.log. Targeted27=13core+14desktop, native28=13text/layout+15regresi Inspector/transforms. Tujuh tes editor diulang dengan QT_SCALE_FACTOR1.5/2: actual screen.json DPR1.875/2.5, semua lulus; native utama actual DPR1.25. Faktor bukan klaim DPR1.5/2. `smoke-build.ps1 -SmokeMode offscreen` exit0, PyInstaller6.22.3, executable a70c264c4fff2793b0e0b073f07540efaa1caf71bfdd23e45d201e5a3f991a6b; log artifacts/segment11-build.log. Isolated noneditable-wheel text conformance exit0, artifacts/text11-wheel. [Evidence/hash snapshot](evidence/segment11-verification.json).

Tes mencakup wrapping/blank/trailing lines, design metrics, auto size anchor parent berotasi, strict command validation/rollback, typography undo, Unicode/Arabic/CJK/combining/emoji, missing-font warning dan explicit replacement, Mixed values, IME preedit, clipboard/Delete, external revision/selection, dan editable native roundtrip. Conformance benar-benar memakai QApplication Windows dan QGuiApplication offscreen serta font Abel OFL-1.1 dari embedded ZIP setelah resolver lama ditutup. Gagal save/reopen awal akibat urutan registrasi embedded fallback sudah diperbaiki dan menjadi regresi conformance.

Native canvas==PNG exact; metrics native/offscreen exact. Actual perbedaan outline backend max19/255 hanya glyph edges/interior0. PDF2x max40 native/38 offscreen, interior2/255 untuk compositing alpha nested pada frame opaque; existing06A thresholds/tests tidak diubah. PDF outline tidak searchable. Native screenshot Inspector/font controls/scroll pada DPR1.25/1.875/2.5, shared Unicode/emoji PNG dan actual PDF raster benar-benar diperiksa. Layout Inspector diperbaiki dengan minimum size constraint setelah screenshot awal menunjukkan nested typography controls tertekan; tes minimum heights dan screenshot ulang membuktikan kontrol terbaca dan dapat discroll.

Manual yang belum dilakukan: keyboard/IME fisik Windows candidate-window, mouse fisik, screen reader, monitor switching/OS DPI fisik, viewer PDF lain, clean Windows release machine. Skenario: buat fixed text box di rotated frame; ketik Latin/Arabic/CJK dan emoji; copy/cut/paste/delete substring, undo/redo; ubah lineheightpx dan auto_height, resize width; save/reopen lalu edit lagi; buka dengan font hilang dan periksa warning tanpa metadata berubah. Pengujian Qt event otomatis dibedakan dari skenario manual tersebut.

Emoji hanya outline monokrom yang tersedia, replacement+warning bila tidak didukung. Rich spans/variable fonts/text-on-path31, font management UI lanjutan, constraints13, image12, public export/jobs15–17 dan acceptance/performance/release22–25 tetap pemiliknya. Tidak ada blocker11. Berikutnya12 `not_started`; aman dilanjutkan pada scope/prasyaratnya, tidak dikerjakan otomatis.
