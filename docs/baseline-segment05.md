# Segmen 05 — desktop session shell

Tanggal 23 Oktober 2026, Asia/Jakarta. Status verified untuk shell/lifecycle 05.
Revision dasar 54162c5; belum ada commit otomatis. Renderer/drawing/export belum
tersedia dan kontrolnya dinonaktifkan secara eksplisit.

Implementasi: `ui/window.py`, bootstrap main, lifecycle read-only promotion pada
dispatcher dan staged reload pada persistence. Tabs memiliki dispatcher, history,
selection, page aktif, blob store dan path sendiri. New memakai nama proyek;
Open dan Import memakai loader yang sama dan membuka tab baru tanpa menimpa tab
dirty. File invalid tidak menghasilkan tab. Save/Save As mengembalikan checkpoint
snapshot; read-only dipromosikan setelah Save As sukses. Reload memvalidasi staging
sebelum mengganti admission/history dengan session_id baru dan mempertahankan lock.

IO terserialisasi memakai executor satu worker; widget dan dispatcher hanya GUI
thread melalui queued completion signal. Selama job, lifecycle actions dinonaktifkan
dan close ditolak sampai hasil final. Ini bounded satu job aktif, bukan MCP scheduler.
Pilihan executor menggantikan rencana actor QThread untuk adapter sinkron yang
tidak memakai QObject I/O; QLockFile dibuat dan dipakai pada worker yang sama.
Tidak ada perubahan format native atau domain Qt dependency.

Verifikasi aktual:

- `scripts/check.ps1` offline: 324 core + 6 desktop, lint/format/type, docs/fixtures,
  wheel/installed-package smoke exit 0 sebelum penambahan dua tes GUI terakhir.
- `pytest tests/test_editor_shell.py -q`: 3 passed setelah penambahan tes konflik/
  read-only/reload gagal dan responsivitas timer. Mypy 44 files exit 0.
- Windows native `scripts/check_shell_scale.py`: baseline monitor DPR 1,25;
  QT_SCALE_FACTOR 0.8/1.2/1.6 menghasilkan DPR efektif 1/1.5/2. Area canvas logical
  676 px pada ketiganya; tinggi window menyesuaikan available screen. Screenshot
  di artifacts/shell-dpi-*.png. Screenshot shell pada faktor 2 (DPR2,5) benar-benar
  diperiksa: panel/menu/label terlihat, kontrol belum tersedia disabled.
- Python 3.12.12, PySide6/Qt 6.10.2, pytest 8.4.2, ruff 0.14.0, mypy 1.18.2.

Demo: `uv run --offline --locked python -m ltechdesign gui` dengan environment uv
workspace sesuai scripts/common.ps1, atau `.venv/Scripts/python.exe -m ltechdesign gui`.
Open/Import contoh examples/proyek-contoh.ltechdesign; pilih objek Layers, ubah
nama di Inspector, Undo/Redo, Save As, tutup dan buka kembali.

Checkpoint 05.shell dan 05.lifecycle telah diimplementasikan dengan tes awal.
05.verification: New/Save As/read-only promotion dan dialog cancellation sudah diuji;
loaded-document pada ketiga DPR sudah dijalankan dan screenshot diperiksa.
AT-27 penuh (Windows settings 100/150/200%, pindah monitor, handles/hit test serta
export dimensions) tetap pending renderer 06/06A dan audit 22. Tidak mengklaim
ukuran ekspor telah diuji karena export belum tersedia. Skenario manual belum
dilakukan: keyboard-only seluruh lifecycle, save/discard/cancel shutdown multi-tab,
read-only Save As promotion dan perubahan monitor nyata. Tidak ada blocker eksternal
untuk memperluas tes shell; pekerjaan ini tetap lingkup 05. Segmen 06 belum dimulai.

Verifikasi final: scripts/check.ps1 offline exit 0, 324 core + 9 desktop; ruff format/check 47 files, mypy strict 44 files, fixture/docs/build/wheel smoke lulus. Empat tes GUI baru meliputi lifecycle dua tab, cancel close, invalid load, conflict/error, failed reload, read-only, New/Save As/promotion dan timer UI selama worker tertahan. Runtime Python/PySide6 tetap versi terkunci di atas. Source baru: ui/window.py; service.reload dan Dispatcher.set_read_only adalah lifecycle API, bukan jalur mutasi konten baru. Segmen 06 belum dimulai. ADR 0015 mencatat keputusan executor.

Executable spike final: scripts/smoke-build.ps1 -SmokeMode offscreen, exit 0; PyInstaller 6.22.3. Bukti [segment05-package-offscreen.json](evidence/segment05-package-offscreen.json). Checkpoint 05.shell, 05.lifecycle dan 05.verification verified untuk lingkup shell, dengan batas AT-27 penuh seperti di atas. Tidak ada commit otomatis. Aman melanjutkan 06 setelah instruksi pengguna.
