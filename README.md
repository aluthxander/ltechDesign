# ltechDesign Studio

Segmen12 menyediakan **File → Import images** (`Ctrl+Shift+I`) dan local file
drag-and-drop untuk PNG/JPEG/WebP/static SVG. Crop/fit/replace/radius/opacity/
rotation di Inspector, thumbnails embedded, undo/redo dan portable Save/Open
tersedia. Jalankan `scripts/run.ps1`; lihat [panduan/subset SVG](docs/image-import.md)
dan [hasil verifikasi12](docs/baseline-segment12.md). Clipboard image lintas aplikasi
tetap38A, production export jobs15–17 belum dikerjakan.

Segmen 02: model domain immutable tanpa Qt, schema/validator 1.0, JSON round-trip,
fixture final dan migration registry. Fondasi CLI/window minimal 01/01A tetap tersedia.
Canvas/editor, ZIP/disk persistence, renderer, export dan MCP menunggu segmen berikutnya.
Subcommand CLI yang tersedia hanya `gui`; `render/export/mcp` belum didaftarkan.

## Setup PowerShell (Windows x64)

Alur dependency tunggal: **uv 0.12.1 + Python 3.12.12 + uv.lock**. Pasang uv versi
tersebut dari [rilis resmi](https://github.com/astral-sh/uv/releases/tag/0.12.1),
lalu jalankan dari checkout:

```powershell
Set-ExecutionPolicy -Scope Process Bypass # bila skrip lokal diblokir; hanya sesi ini
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD '.cache/python'
uv python install 3.12.12
uv sync --locked
```

Tidak perlu activate environment; `uv run --locked` memakai `.venv`. Unduhan
pertama memerlukan internet. PySide6 membawa Qt Essentials/Addons/Shiboken yang
dikunci bersama. Pillow/MCP SDK akan ditambah bersama subsistem yang memakainya.
Jangan edit `uv.lock` manual. Pembaruan dependency disengaja: ubah pin di
`pyproject.toml`, `uv lock`, lalu ulangi semua pemeriksaan dan baseline. Backend
build hatchling juga dipin. Saat ini hanya Python 3.12 yang diklaim didukung.
Perilaku lock mengikuti [dokumentasi uv](https://docs.astral.sh/uv/concepts/projects/sync/).

## Pemeriksaan dan menjalankan aplikasi

```powershell
.\scripts\check.ps1                          # semua pemeriksaan tersedia
.\scripts\check.ps1 -Subsystem core          # model/schema/geometry + CLI/logging
.\scripts\check.ps1 -Subsystem desktop       # Qt offscreen, bukan inspeksi GUI
.\scripts\check.ps1 -Subsystem lint
.\scripts\check.ps1 -Subsystem types
.\scripts\check.ps1 -Subsystem fixtures
.\scripts\check.ps1 -Subsystem docs
.\scripts\check.ps1 -Subsystem package       # sdist/wheel + install wheel terisolasi
uv run --locked pytest                       # native Qt pada desktop lokal
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
.\scripts\run.ps1                            # window minimal
.\scripts\run.ps1 -Smoke                     # event loop, lalu tutup otomatis
.\scripts\run.ps1 -Mode cli -CliArgs '--version'
uv run --locked ltechdesign-cli gui
uv run --locked python -m ltechdesign --help
uv run --locked ltechdesign                   # entry point desktop tanpa console
```

Script bekerja dari cwd lain. Exit code check: 0 lulus, 1 kegagalan tool/test/setup,
2 subsistem tidak dikenal atau belum tersedia (misalnya `visual`, `rendering`).
Tes schema/migration/domain termasuk dalam subsystem `core`. Tidak ada fallback yang menganggap subsistem itu lulus.
Pytest memakai marker `core`/`desktop` dan binding `pyside6` eksplisit, sesuai
[pytest-qt](https://pytest-qt.readthedocs.io/en/master/intro.html).

Logging aplikasi dikonfigurasi saat entry point desktop dipanggil, ke stderr,
tanpa file persisten dan tanpa mengubah root logger. Import package/CLI tidak
menginisialisasi Qt. CLI help/version tetap dapat berjalan tanpa desktop.

## Fixture dan baseline

```powershell
uv run --locked python scripts/generate_fixtures.py
uv run --locked python scripts/generate_fixtures.py --check
$env:QT_QPA_PLATFORM = 'offscreen'
uv run --locked python scripts/baseline.py --output artifacts/baseline.json
Remove-Item Env:QT_QPA_PLATFORM
```

Generator tidak memakai random, timestamp, font sistem atau network. Ia memeriksa
hash font yang di-vendor dan menghasilkan manifest, teks, fixture domain, contoh docs
dan enam JSON Schema dari definisi typed yang sama. Font Abel
asli berlisensi SIL OFL 1.1 beserta copyright/lisensi lengkap ada di
`tests/fixtures/fonts/`; provenance dan hash ada di manifest. Fixture `schema/nested-v1.json` dan historis `legacy-00b.json` membuktikan kompatibilitas 1.0.
Registry migrasi hanya mendukung 1.0; tes versi sintetis tidak mengklaim format lama lain.
Lihat [baseline 02](docs/baseline-segment02.md) untuk penggunaan domain dan batas bukti;
ZIP dan golden screenshot tetap menunggu segmen 04/06A.

CI Windows menjalankan check yang sama serta merekam baseline/dependency dan
JUnit. Tes desktop hanya memverifikasi lifecycle window, pemuatan font, dan
startup/shutdown proses entry point dengan plugin offscreen. Tidak ada klaim
inspeksi GUI, pixel comparison, DPI native 100/150/200%, clean Windows release,
atau kesiapan rilis. Baseline aktual segmen 01 dan keterbatasannya dicatat di
[docs/baseline-segment01.md](docs/baseline-segment01.md); roadmap di
[docs/progress.md](docs/progress.md). Hasil spike executable 01A ada di bawah.

## Executable Windows minimal (01A)

```powershell
.\scripts\smoke-build.ps1                      # build + window native + close normal
.\scripts\smoke-build.ps1 -SkipBuild           # ulangi smoke artifact yang sama
.\scripts\smoke-build.ps1 -SmokeMode offscreen # build + smoke untuk runner headless
.\dist\windows\ltechDesign-Studio\ltechDesign-Studio.exe
```

PyInstaller 6.22.3 memakai group `packaging` dari lock yang sama. Mode native
menampilkan window sementara dan meminta close normal melalui Windows; offscreen
hanya menguji startup/event loop/shutdown. Script mengembalikan 0 bila lulus, 1
bila gagal, serta menyimpan report JSON, log build dan warning di `artifacts/`.
`-SkipBuild` dapat dijalankan tanpa uv/Python terhadap bundle lengkap; gunakan
`-Executable 'C:\path\ltechDesign-Studio.exe'` untuk lokasi lain.

Salin seluruh folder `dist/windows/ltechDesign-Studio`, termasuk `_internal`.
Ini belum installer atau artifact rilis bertanda tangan. Lihat
[ADR 0011](docs/adr/0011-windows-executable-spike.md) untuk resep, versi dan plugin;
[bukti 01A](docs/baseline-segment01a.md) membedakan hasil mesin development dari
uji Windows bersih segmen 24 yang masih pending. CI hanya smoke offscreen.
