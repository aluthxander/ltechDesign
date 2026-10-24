# Bukti executable Windows segmen 01A

Tanggal: 21 Oktober 2026, Asia/Jakarta. Status: **verified untuk spike pada mesin
development lokal**. Tidak ada installer/editor/canvas baru, inspeksi visual manual,
atau klaim berhasil di Windows bersih. Mesin sama dengan [baseline 01](baseline-segment01.md):
Windows 11 build 26300 x64, i5-13450HX, RAM sekitar 31,72 GiB; metadata layar
native DPR 1,25 dan 1,5. Ini bukan pengujian layout pada dua skala tersebut.

## Build yang benar-benar dijalankan

Resep: [scripts/smoke-build.ps1](../scripts/smoke-build.ps1),
[ADR 0011](adr/0011-windows-executable-spike.md). Dependency runtime segmen 01
dipakai bersama PyInstaller 6.22.3 dan hooks-contrib 2026.9 yang dikunci di uv.lock.
Build selesai menggunakan bootloader Windows x64 `runw.exe`, `onedir/windowed`.
Artifact lokal: `dist/windows/ltechDesign-Studio/ltechDesign-Studio.exe` beserta
folder `_internal`. Bundle berisi **161 berkas, 117.604.073 byte**; bukan satu exe mandiri.

SHA-256 exe yang diuji:

```text
b78b7bb053cef7abc7d6d814699df3f0e87171ffceb9ba236b746337e86f0d7d
```

## Startup dan shutdown artifact aktual

[Snapshot laporan native](evidence/segment01a-native.json) berasal dari build
dan proses executable aktual pada **19:31:36–19:32:15 WIB**, termasuk waktu build.
Harness menjalankan `.exe` tanpa Python launcher, dari `artifacts/executable-smoke-cwd`.
PATH child hanya direktori Windows; Python/venv/plugin-path environment dibersihkan.

| Observasi otomatis native | Hasil |
| --- | --- |
| Judul main window | ltechDesign Studio |
| PID / window handle | 35924 / 461140 |
| Waktu sampai window teramati | 1.377 ms; satu observasi, bukan benchmark |
| Window hidup sebelum close | Ya, ditahan setidaknya 1 detik |
| Runtime yang benar-benar termuat | python312, Qt6Core, Qt6Gui, Qt6Widgets, qwindows; seluruh path dari bundle |
| Penutupan | Process.CloseMainWindow, permintaan WM_CLOSE normal |
| Exit code | 0 |
| Waktu proses sampai selesai | 2.481 ms, termasuk hold dan permintaan close |
| Force kill / timeout | Tidak |

MainWindowHandle/judul dan daftar modul adalah bukti otomatis adanya window native
serta runtime yang dipakai. Ini bukan screenshot atau inspeksi visual manusia.
Tidak menggunakan `--smoke`/auto-close pada pengujian native.

[Snapshot offscreen](evidence/segment01a-offscreen.json) mencatat executable dengan
hash yang sama juga selesai exit 0 memakai `--smoke`. Itu hanya bukti event loop,
bukan observasi window native. CI dikonfigurasi membangun dan melakukan smoke
offscreen; runner GitHub belum dijalankan dalam sesi ini.

## Skrip, log dan pemeriksaan pendukung

- Exit 0 berarti build (bila diminta) dan smoke berhasil; missing artifact diuji
  menghasilkan exit 1 dan JSON failed, bukan success palsu. Output offscreen
  kemudian diulang dengan artifact yang benar.
- Log build: `artifacts/segment01a-build.log`; session transcript dan warning
  juga di `artifacts/`. Snapshot JSON di `docs/evidence/` dipertahankan sebagai
  bukti build ini, sedangkan laporan di artifacts dapat ditimpa saat pengulangan.
- Warning analisis berisi modul platform lain/stdlib seperti pwd, grp, posix,
  resource, fcntl dan frozen import internals. Tidak menambahkan hidden import
  untuk modul Unix pada Windows. Startup native/offscreen sudah membuktikan
  tidak ada missing runtime yang menghalangi spike ini.
- Ruff, mypy strict, 10 smoke test fondasi dan audit dokumentasi diperiksa kembali.

Unduhan PyInstaller berhasil melalui eskalasi jaringan. Satu sync ulang sempat
gagal mengakses metadata hatchling (socket 10013); sync dan build berikutnya
berhasil dengan eskalasi. Tidak ada blocker build/runtime yang tersisa untuk 01A.

## Gate yang masih pending

Segmen 24 wajib memindahkan bundle lengkap ke Windows bersih tanpa Python/Qt/dev
toolchain dan menguji kompatibilitas/runtime, licensing, signing/installer serta
aplikasi lengkap. PATH child yang dibersihkan pada mesin development tidak
menggantikan gate itu. Perubahan Qt/plugin/rendering/packager wajib mengulang
skrip ini. Segmen 02 dan UI lanjutan belum dikerjakan pada sesi 01A.
