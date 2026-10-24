# Baseline segmen 01

Tanggal pengujian: 21 Oktober 2026, Asia/Jakarta. Ini mesin development, bukan
Windows bersih atau baseline performa editor. Tidak ada inspeksi GUI manual.

## Mesin dan display

- Windows 11 x64, build 10.0.26300, AMD64.
- CPU: 13th Gen Intel Core i5-13450HX, 16 logical processors.
- RAM dilaporkan CIM: 34.053.414.912 byte (sekitar 31,72 GiB).
- Plugin Qt native `windows`: DISPLAY1 1536×864 logical pixel, DPR 1,25 (125%);
  PM161Q J 1280×720 logical pixel, DPR 1,5 (150%). Logical DPI keduanya 96.
  Ini metadata QGuiApplication, bukan hasil inspeksi layout di kedua monitor.
- Tes otomatis memakai `offscreen`: layar sintetis 800×800, DPR 1, logical DPI 96.
  QT_SCALE_FACTOR/QT_SCREEN_SCALE_FACTORS tidak disetel. Ini bukan bukti DPI native.
- CIM awal gagal `Access denied` di sandbox. Probe read-only kemudian berhasil
  dengan eskalasi; tidak ada setting display/OS yang diubah.

## Dependency yang terpasang dan diuji

Python 3.12.12, MSC v.1944 64 bit; uv 0.12.1. `uv.lock` mencatat distribusi,
versi transitif dan hash unduhan. Backend: hatchling 1.27.0, build sdist/wheel
benar-benar dijalankan. Package aplikasi 0.1.0.

| Dependency | Versi aktual |
| --- | --- |
| PySide6 / PySide6_Addons / PySide6_Essentials / shiboken6 | 6.10.2 |
| Qt runtime dan compiled | 6.10.2 |
| pytest | 8.4.2 |
| pytest-qt | 4.5.0 |
| ruff | 0.14.0 |
| mypy | 1.18.2 |
| colorama | 0.4.6 |
| iniconfig | 2.3.1 |
| mypy_extensions | 1.1.0 |
| packaging | 26.3 |
| pathspec | 1.1.1 |
| pluggy | 1.7.0 |
| Pygments | 2.21.0 |
| typing_extensions | 4.16.0 |

Font uji Abel Regular asli, copyright Matthew Desmond 2011, Reserved Font Name
Abel. SIL Open Font License 1.1 mengizinkan redistribusi bersama lisensi dan
copyright; font tidak dimodifikasi atau dijual sendiri. Berkas lisensi lengkap
dan [manifest provenance/hash](../tests/fixtures/fonts/manifest.json) disertakan.

## Hasil dan cara mengulang

Perintah lengkap ada di [README](../README.md). Bukti mentah lokal dibuat pada
`artifacts/baseline.json`, `artifacts/baseline-native.json`, `artifacts/core.xml`
dan `artifacts/desktop.xml` (diabaikan Git). CI mengunggah hasilnya sendiri;
workflow GitHub Actions belum dijalankan dalam sesi lokal ini.

- `uv sync --locked`: berhasil membuat `.venv` dan memasang 17 package termasuk aplikasi.
- Core: 5 tes lulus (CLI/version/error, import tanpa Qt, logging idempoten,
  regenerasi deterministik serta deteksi fixture berubah).
- Desktop: 5 tes lulus dengan pytest-qt/offscreen, termasuk proses entry point
  desktop, CLI gui dan module; tiap proses wajib selesai dalam 30 detik.
- Ruff check/format dan mypy strict lulus untuk 9 berkas Python, tanpa blanket ignore.
- Generator `--check` lulus; tidak melakukan network atau memproduksi native project palsu.
- Sdist dan wheel dibangun; runtime terisolasi disinkronkan dari lock tanpa dev
  dependency. Wheel non-editable dipasang; version dan GUI event loop smoke lulus.
- Audit dokumen dan 13 kasus negatif contoh format tetap lulus; bukan tes codec.
- `scripts/check.ps1` penuh selesai exit 0. Probe fixture yang sengaja diubah
  menghasilkan exit 1, kemudian dipulihkan; subsistem `schema` menghasilkan exit 2.
  `scripts/run.ps1` diuji dari cwd di luar repo: CLI version dan desktop smoke
  exit 0, subcommand belum tersedia exit 1. Sdist diperiksa bebas `.cache/.venv`.

Percobaan awal unduh Python gagal socket 10013; unduhan Python dan dependency
kemudian berhasil dengan eskalasi jaringan. Build pertama sempat gagal karena
README belum dibuat; berhasil setelah file lengkap. Instalasi wheel dengan
resolver pip sempat mencoba metadata jaringan lagi. Jalur final memakai
`uv sync --locked --offline --no-dev --no-install-project` pada environment
terisolasi, lalu memasang wheel lokal `--offline --no-deps`; semuanya memakai
runtime yang sudah terunduh oleh sync awal. Tidak ada dependency unduhan yang
masih menjadi blocker.

Belum dibuktikan: inspeksi window native, DPI 100/150/200%, pixel/golden comparison,
schema/migration/persistence, benchmark performa, binary bundle, installer dan
Windows bersih. Spike executable berikutnya tetap segmen 01A.
