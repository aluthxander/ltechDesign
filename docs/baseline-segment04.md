# Bukti fondasi persistence segmen 04

Tanggal: 23 Oktober 2026, Asia/Jakarta. Status: **verified untuk fondasi segmen 04**.
Baseline Git `54162c5f1c7300d5701dd841b0fb961592540d8b`; implementasi 00–04 masih
working tree. Tidak membuat commit dan tidak mengubah `prd.md` pengguna.

## Checkpoint

| ID internal | Lingkup | Status | Bukti |
| --- | --- | --- | --- |
| 04.codec | ZIP, inventory, schema, assets, portable semantic round-trip | verified | tests/test_persistence.py, tests/test_asset_validation.py; 87 tes baru |
| 04.ownership | canonical path, lock, baseline, atomic save/Save As, backup | verified | Fault injection dan stale metadata sintetis; dua proses nyata tetap 04A |
| 04.retention | byte store/staging, dispatcher undo/redo, recovery/job leases | verified | Store adapter nyata + dispatcher 03; recovery persisten tetap 14 |
| 04.handoff | docs, fixture drift, wheel/cwd, regresi dan package spike | verified | Full gate exit 0, 317 core + 5 desktop; installed wheel dan executable offscreen lulus |

## Implementasi dan demo

Modul utama: [persistence](../src/ltechdesign/persistence/service.py),
[ZIP codec](../src/ltechdesign/persistence/archive.py),
[blob store](../src/ltechdesign/assets/store.py),
[asset validation](../src/ltechdesign/assets/validation.py).
[ADR 0014](adr/0014-native-persistence.md) menjelaskan batas, asumsi dan lifecycle.

Demo offline tanpa GUI, dari root repository:

```powershell
$env:UV_CACHE_DIR = "$PWD/.cache/uv"
$env:UV_PYTHON_INSTALL_DIR = "$PWD/.cache/python"
uv run --offline --locked python scripts/check_persistence.py examples/proyek-contoh.ltechdesign --scratch artifacts/persistence-demo
```

Loader juga dapat dipakai langsung dengan path absolut:

```python
from ltechdesign.persistence import PersistenceService

service = PersistenceService()
opened = service.open(absolute_path, read_only=True)
try:
    project = opened.loaded.project
    blobs = opened.loaded.blobs
    # GUI 05 menerbitkan admission ini hanya setelah open berhasil.
    service.save(opened, opened.admission, blobs, target=new_absolute_path)
finally:
    service.close(opened)
```

Editor menyerahkan `Dispatcher.snapshot` dan blob lease ke save; owner menerapkan
hasil `checkpoint` dengan `Dispatcher.mark_saved`. Save snapshot R ketika live
sudah R+1 tidak menandai live clean. Contoh ini bukan GUI, MCP atau job scheduler.

Fixture [proyek-contoh.ltechdesign](../examples/proyek-contoh.ltechdesign) berisi
dua page, nested/rotated nodes, text, image, SVG, embedded font dan token bindings.
Generator PowerShell/Python hanya membuat contoh dan fixture gate; bukan loader
produksi. PNG corrupt dalam JSON fixture 02 tidak diedit; tes produksi menolaknya.

## Hasil aktual

Environment diuji: Windows 11 build 26300 x64, Python **3.12.12**, PySide6/Qt
**6.10.2**, pytest **8.4.2**, pytest-qt **4.5.0**, ruff **0.14.0**, mypy **1.18.2**,
uv **0.12.1**. Spike executable: PyInstaller **6.22.3**, hooks-contrib **2026.9**.
Tidak menambah dependency atau mengubah pins/uv.lock.

| Perintah / pemeriksaan | Hasil aktual |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/test_persistence.py tests/test_asset_validation.py -q` | Exit 0, 87 passed; skenario thumbnail kemudian diperluas dan diverifikasi lagi melalui full gate |
| `$env:UV_OFFLINE = 'true'; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1` | Exit 0; **317 core + 5 desktop offscreen**, ruff check/format (41 files), mypy strict (39 files), JSON/native fixture drift, docs/schema checks, sdist/wheel dan isolated-wheel smoke lulus. Dijalankan ulang setelah perbaikan invalidasi thumbnail, hasil tetap lulus |
| Installed wheel: `python.exe -I scripts/check_persistence.py examples/proyek-contoh.ltechdesign --scratch artifacts/persistence-wheel` (oleh runner) | Exit 0; **2 page, 17 editable nodes, 3 blob byte-identical**; Save As, close, move/reopen dengan cwd sementara. Tidak mengimpor source checkout/generator atau menggunakan database/cache/source asset path |
| `$env:UV_OFFLINE = 'true'; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-build.ps1 -SmokeMode offscreen` | Exit 0; PyInstaller build + executable startup/shutdown. 161 file, 117.604.073 byte; report [segment04-package-offscreen.json](evidence/segment04-package-offscreen.json). Minimal desktop regression, bukan native persistence UI atau inspeksi visual |
| Wheel/sdist inspection | Runtime persistence/assets ada di wheel; fixture/cache/tests tidak menjadi isi/dependency wheel. Native example ada di sdist. Warning uv tentang cache di source tidak berarti cache masuk distribusi: inventory diperiksa dan bersih |
| `git diff --check` | Exit 0. Diff tracked hanya perubahan pengguna sebelumnya pada prd.md; file implementasi masih untracked working tree, tidak membuat commit |

Tidak ada blocker lingkup 04. Aman melanjutkan ke **04A setelah instruksi pengguna**;
04A tetap not_started. Tidak melompat ke 05 sebelum spike 04A selesai.

- Tes terkait awal: 60 passed. Setelah perluasan race/media, 87 passed.
- Mypy strict: 39 source files, exit 0 setelah koreksi typing.
- Pengujian menemukan PySide6 6.10.2 QImage.save menerima `str` untuk format;
  stub menyebut bytes tetapi bytes gagal di runtime. Tes mencatat ignore bertarget
  untuk ketidakcocokan stub; tidak mengubah dependency atau melemahkan assertion.
- Injeksi rename ketika file masih dibuka ditolak Windows dengan WinError 5;
  kasus perubahan saat load memakai competing write in-place yang benar-benar
  mungkin. Kasus external replace setelah admission diuji terpisah.
- Percobaan dot-source common.ps1 pertama terhalang execution policy. Pemeriksaan
  selanjutnya memakai Python venv atau runner `powershell -ExecutionPolicy Bypass`.
- Fixture PNG corrupt awal ditolak actual Qt decode; PNG native baru lulus decode.
  Full gate pertama lulus sebelum tambahan invalidasi stale thumbnail; full gate
  kedua lulus setelahnya. Tidak menandai kegagalan awal sebagai hasil lulus.

## Batas bukti dan integrasi tertunda

- AT-31–34 **fondasi**: editable model/tokens/IDs/order, byte assets, dua page,
  pemindahan file + penghapusan source bytes, repeated semantic round-trip, serta
  malformed load tidak mengubah model/admission lama. Tidak mengklaim tab GUI.
- 04A belum dijalankan: dua proses nyata, crash/stale/PID reuse, junction/alias/ACL
  Windows yang lebih luas. Tidak otomatis melanjutkan segmen itu.
- GUI registry/read-only promotion, dialogs, async owner admission: 05. Recovery
  disk/autosave: 14. Scheduler/job status/cancel IPC: 18C/19. Blob leases runtime
  sudah bekerja; recovery inventory persisten lintas restart belum tersedia.
- Layout nonnull/constraints tetap ditolak sampai solver 13, required extension
  tidak dikenal ditolak. Tidak ada data fitur tersebut dibuang atau diperkirakan.
- Thumbnail belum dihasilkan; thumbnail valid dipreservasi selama konten sama,
  dan preview lama dikeluarkan dari output save bila semantic content berubah. Canvas/
  preview/export/visual equality menunggu 06/06A/15–17; font resolution/fallback
  warning/glyphs 11 dan SVG rendering/import penuh 12. SFNT validation bukan tes
  glyph shaping. Model tetap Qt-independent; adapter byte decode/lock memakai Qt.
- GUI tidak berubah pada segmen ini. Inspeksi visual/manual **belum dilakukan**.
  Skenario manual setelah 05: Open dua-page → edit → Save As → tutup/buka/import;
  read-only open saat file dimiliki; corrupt manifest/hash harus meninggalkan tab
  aktif utuh; close/cancel/save saat job berjalan. Tidak ditandai lulus sekarang.
- Clean Windows release/CI remote pending 24/25. Lock tidak mencegah foreign
  writer yang mengabaikan sidecar pada celah setelah baseline recheck terakhir.
