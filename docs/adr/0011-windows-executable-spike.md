# ADR 0011: Windows executable minimal dengan PyInstaller

Tanggal: 21 Oktober 2026 (Asia/Jakarta). Status: accepted untuk spike 01A.
Keputusan ini tidak menetapkan installer atau kesiapan rilis segmen 24/25.

## Keputusan dan alasan

Gunakan PyInstaller **6.22.3**, `onedir`, `windowed`, tanpa UPX. Python tetap
**3.12.12 x64**, PySide6/Qt/shiboken6 **6.10.2**, uv **0.12.1** dari segmen 01.
Build tools berada di dependency group `packaging`, terpisah dari dependency
runtime. `uv.lock` mengunci pula hooks-contrib **2026.9**, altgraph **0.17.5**,
pefile **2024.8.26**, pywin32-ctypes **0.2.3**, setuptools **84.2.1** dan packaging
**26.3** pada Windows. macholib dalam lock hanya berlaku untuk macOS, tidak diuji.

`onedir` memudahkan audit runtime/DLL/plugin dan tidak perlu ekstraksi satu-file
saat startup. Seluruh direktori bundle harus dipindahkan bersama executable;
menyalin `.exe` saja tidak cukup. Tidak ada klaim build byte-identical: versi,
hash dependency dan resep build direproduksi, sementara hash artifact aktual
dicatat per build. Belum ada code signing, installer atau optimasi ukuran.

Bootstrap [freeze_desktop.py](../../scripts/freeze_desktop.py) memanggil entry
point desktop segmen 01. Tidak ada editor, canvas, atau implementasi fitur baru.
Spesifikasi PyInstaller di `build/pyinstaller/` dihasilkan otomatis dari resep
skrip; keberadaan `.spec` bukan bukti executable bekerja.

## Perintah dan plugin

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\smoke-build.ps1
# Artifact yang sudah dibangun; tidak membutuhkan Python/uv untuk smoke:
.\scripts\smoke-build.ps1 -SkipBuild
# Headless runner: hanya event loop/startup/shutdown, tanpa window native:
.\scripts\smoke-build.ps1 -SkipBuild -SmokeMode offscreen
```

[smoke-build.ps1](../../scripts/smoke-build.ps1) menetapkan cache di workspace,
menjalankan `uv sync --locked --group packaging`, lalu:

```powershell
uv run --locked --group packaging python -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name ltechDesign-Studio --distpath dist/windows --workpath build/pyinstaller --specpath build/pyinstaller scripts/freeze_desktop.py
```

PyInstaller memakai hook bawaan `PySide6`, `shiboken6`, `PySide6.QtCore`,
`PySide6.QtGui`, `PySide6.QtWidgets` dan `PySide6.QtNetwork`, serta runtime hook
`pyi_rth_pyside6` dan `pyi_rth_inspect`. Tidak ada custom hook/hidden import atau
penyalinan plugin manual. Native wajib menyertakan dan memuat
`_internal/PySide6/plugins/platforms/qwindows.dll`; CI offscreen memakai
`qoffscreen.dll`. Qt6Core/Gui/Widgets DLL, python312.dll dan VC runtime dibundel
oleh hook/analisis dependency. Hook ikut mengumpulkan plugin imageformats,
styles, TLS dan plugin lain; kehadiran plugin tersebut bukan bukti fitur aplikasi.

Rujukan: [opsi PyInstaller](https://pyinstaller.org/en/stable/usage.html),
[cara kerja bundle](https://pyinstaller.org/en/latest/operating-mode.html),
[distribusi versi yang dipin](https://pypi.org/project/pyinstaller/6.22.3/).

## Pembuktian dan batas

Hasil aktual dan snapshot evidence ada di [laporan 01A](../baseline-segment01a.md).
Native harness mengamati handle/judul main window, memastikan tetap hidup sebelum
close, lalu meminta `Process.CloseMainWindow()` (WM_CLOSE). Lulus hanya bila
exit code 0 dalam 15 detik dan semua modul runtime teramati berasal dari bundle.
Tidak ada timer auto-close untuk tes native; timer `--smoke` hanya dipakai offscreen.
Proses dijalankan dari cwd di luar source dengan PATH hanya direktori Windows,
tanpa PYTHONHOME/PYTHONPATH/VIRTUAL_ENV atau override lokasi plugin Qt.

Timeout, missing artifact/plugin, build gagal, dan exit nonzero menghasilkan
exit 1 serta laporan failed. Jika timeout, cleanup boleh menghentikan hanya
proses yang diluncurkan harness dan harus mencatat `forced_termination`; ini
tidak pernah dihitung shutdown bersih. Laporan JSON berisi hash artifact,
hash lock, runtime/plugin, judul, PID, metode close dan exit code.

Workflow Windows membangun lalu menjalankan artifact offscreen; belum ada klaim
runner remote telah dieksekusi atau inspeksi GUI manual. Mesin development yang
memiliki toolchain bukan Windows bersih. Segmen 24 masih wajib menguji bundle
yang dipindahkan pada mesin Windows tanpa Python/Qt/dev toolchain, kompatibilitas
runtime/OS, distribusi lisensi, signing/installer dan lifecycle produk lengkap.
Perubahan Python/Qt/plugin/packager wajib mengulang smoke ini.
