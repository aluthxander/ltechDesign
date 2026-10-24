# Bukti dua proses persistence 04A

Tanggal: 23 Oktober 2026 (Asia/Jakarta). Status: **verified untuk fondasi 04A**.
Baseline commit `54162c5f1c7300d5701dd841b0fb961592540d8b`;
implementasi masih working tree, tanpa commit otomatis.

Harness [persistence_worker.py](../scripts/persistence_worker.py) menjalankan
PersistenceService/QLockFile/reader/writer produksi di dua proses Python berbeda.
Parent pytest mengirim JSON lines untuk koordinasi tes saja. Tidak ada GUI atau
MCP server. Setiap child memakai cwd direktori sementara, PID berbeda dan stdout
flush; timeout 15 detik, cleanup graceful atau kill/wait terbatas bila macet.

Reproduksi dari root workspace (environment dev sudah tersedia):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_persistence_processes.py -v --junitxml=artifacts/segment04a.xml
$env:UV_OFFLINE = 'true'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
```

Perintah pertama benar-benar dijalankan: **7 passed, 0 skipped**, Windows 11 build
26300 x64, Python 3.12.12, PySide6/Qt 6.10.2, pytest 8.4.2. Log request/response
beserta PID ada di `artifacts/segment04a/`; JUnit di `artifacts/segment04a.xml`.
Snapshot bukti persisten: [segment04a-processes.json](evidence/segment04a-processes.json).

Gate penuh `scripts/check.ps1` benar-benar selesai **exit 0: 324 core + 5 desktop
offscreen**; ruff check/format 43 files, mypy strict 41 files, fixture drift,
schema/docs, sdist/wheel dan isolated-wheel native portability smoke lulus.
Transcript disalin setelah run penuh (run ulang tujuh skenario juga lulus).
Tidak ada perubahan kode produksi atau kontrak yang diperlukan. Tidak ada blocker
lingkup 04A; aman melanjutkan ke 05 setelah instruksi pengguna.

| Bukti | Hasil aktual | Acceptance fondasi |
| --- | --- | --- |
| Dua writer path sama, alias case/.. | Writer kedua `file_owned`; read-only sukses, save sumber `read_only`; close writer pertama memungkinkan writer kedua masuk | AT-21 |
| Writer aktif dengan mtime lock tua | Dua percobaan takeover ditolak, proses masih hidup, byte sidecar tidak berubah | AT-21 |
| Crash nyata | Parent kill child dan wait exit; sidecar tertinggal; proses lain membuka melalui stale-owner check nyata dan close menghapus lock | AT-21 |
| External replace dari child lain | Byte-identical replacement maupun perubahan bytes terdeteksi `external_change_conflict`; save tidak menimpa file eksternal; Save As ke path baru berhasil | AT-22 |
| Save As gagal I/O nyata | Child kedua memegang handle baca target; Windows menolak replace dengan `io_error`. File sumber/target utuh, temp dibersihkan, target lock dilepas, source writer tetap dimiliki | AT-21/22 |
| Save As sukses | Setelah handle target dilepas, save berhasil; selama staging kedua path menolak writer kedua. Sesudah sukses sumber dapat dibuka proses lain, target masih locked sampai close; session_id tetap | AT-21/22 |
| Dua salinan document_id sama | Keduanya dapat menjadi writer pada path berbeda, session_id berbeda/revision awal 0; save independen, reopen menghasilkan session baru; lock salinan lain tetap terlindungi | AT-26 |
| Hardlink nyata | Writer lewat kedua alias ditolak path_not_allowed; read-only kedua proses berhasil | AT-21 |

Save As memakai callback cancellation yang tersedia untuk handshake sebelum write:
callback hanya menunggu instruksi resume dan selalu mengembalikan false. Service,
lock, replace, validasi dan filesystem tidak di-mock atau diganti. Kegagalan save
berasal dari sharing semantics Windows, bukan exception buatan. Kasus ini ditandai
skip di platform non-Windows; pada mesin aktual Windows benar-benar dijalankan.

Kontrak produksi tidak berubah; tidak diperlukan ADR baru. Mypy standalone untuk
worker mula-mula melaporkan import-untyped karena source package tidak ikut target;
worker kemudian dimasukkan ke konfigurasi pemeriksaan repo bersama `src`, tanpa
mengabaikan error atau menurunkan strictness.

Integrasi GUI/headless attached/MCP, routing multi-tab dan history antar sesi tetap
19B/22; tes 04A tidak mengklaim acceptance produk itu verified. Junction/ACL dan
simulasi PID reuse ambigu yang lebih luas tetap audit platform 20; host asing/
unknown-owner coverage fondasi sebelumnya ada di 04. Tidak ada pemeriksaan visual
manual, perubahan dependency/rendering/packaging runtime, atau mesin Windows bersih.
Program eksternal yang mengabaikan lock masih dapat menulis setelah baseline check
terakhir; tidak ada klaim filesystem compare-and-swap. Berikutnya 05 setelah 04A
ditutup, tidak dimulai otomatis.
