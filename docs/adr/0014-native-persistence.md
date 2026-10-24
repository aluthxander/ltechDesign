# ADR 0014 — Native ZIP, atomic I/O dan byte retention

Status: accepted. Tanggal: 23 Oktober 2026 (Asia/Jakarta). Pemilik: 04;
spike dua proses nyata 04A tetap terpisah.

`persistence` membungkus codec/typed schema domain 02. Semua core JSON memakai
validator yang juga menghasilkan JSON Schema; tidak ada schema kedua yang dibaca
dari working directory. Seluruh entry, hash, referensi dan embedded byte divalidasi
sebelum `LoadedProject`/admission dipublikasikan. Layout nonnull masih ditolak
`unsupported_capability` sampai evaluator 13. Optional metadata extension disimpan
byte persis; clone menolak extension tanpa remapper. Workspace invalid ditolak
(fallback bersifat opsional menurut spesifikasi). Thumbnail valid dipreservasi;
pembuatan thumbnail menunggu renderer. Save setelah perubahan semantic menghapus
preview lama dari snapshot output saja, supaya thumbnail admission lama tidak
dilabeli sebagai revision baru; opaque metadata extension tidak ikut dibuang.

ZIP dibaca tanpa extract. Preflight memeriksa central directory sebelum `ZipFile`
mengalokasikan daftar entry, kemudian pembacaan member dibatasi per chunk.
Batas tambahan operasional: raw ZIP 528 MiB, central directory 16 MiB, SVG 4 MiB,
SVG depth 64 / 10.000 elemen, thumbnail 4.194.304 pixel. Batas archive/asset/raster
PRD tetap 10.000 entry / 512 MiB / 50 MiB / 40.000.000 pixel. `ArchiveLimits` boleh
menurunkan batas; kenaikan melebihi default memerlukan evaluasi baru. Decode Qt
juga tunduk pada allocation limit runtime Qt; penerimaan header bukan bukti decode.

Raster memakai `QImageReader` tanpa widgets/QPixmap, memeriksa format actual,
ukuran sebelum decode dan hasil decode. Animasi multi-frame ditolak. SVG memakai
subset XML geometry statis, tanpa DTD/entities/CSS/script/link/external resources;
byte asli tidak disanitasi dengan membuang bagian atau diraster. Font admission
memeriksa SFNT/table ranges/required tables dan restriction embedding `OS/2`;
tidak memasang font, mengklaim lisensi pengguna terverifikasi, atau melakukan
shaping. Metadata/license tetap dipreservasi. Resolver/fallback warning dan
glyph rendering milik 11/12/06A; import font baru memerlukan pemeriksaan hak
distribusi di fitur import, bukan mempercayai boolean file asing.

`PersistenceService` adalah layanan I/O sinkron terserialisasi untuk dipanggil
worker/actor, bukan dari callback GUI. Ia tidak memutasi konten dispatcher.
Owner menangkap snapshot/checkpoint pada admission job; `SaveResult.checkpoint`
baru diterapkan lewat `Dispatcher.mark_saved` sesudah sukses. Penerimaan current
revision, scheduler/status/progress job dan marshal ke owner thread terintegrasi
pada 05/14/18C. Cancellation sebelum barrier membersihkan temp; sesudah replace
tetap sukses. FileHandle memuat admission awal, bukan salinan live model editor.

Canonical path resolve parent/final target, case dan link melalui stdlib Windows;
writer hardlink multi-link, UNC/mapped network drive, device/ADS/trailing alias
ditolak. Sidecar QLockFile `.lock` terpisah dari ZIP; stale age=0. Adapter menolak
PID hidup/izin tidak jelas/host asing/metadata rusak sebelum mencoba lock; Qt
mengecek ulang owner mati. Tidak pernah force-remove. Registry proses mencegah
reentrant writer dan target yang dipakai sesi lain. Aliases/ACL/crash nyata diuji
lebih luas pada 04A/20, bukan diklaim dari mock.

Baseline memuat device/inode/size/mtime_ns/SHA-256 dari handle yang benar-benar
dibaca, diperiksa lagi selama admission dan sebelum replace. Temp berada di parent
target, di-flush/fsync dan dibaca ulang melalui reader produksi. Save As mempertahankan
lock sumber sampai replace target berhasil. Tidak ada I/O yang dapat gagal atau
cancel check setelah barrier untuk menentukan sukses; baseline baru berasal dari
temp yang direplace. Foreign writers masih mempunyai celah setelah recheck final:
ini bukan filesystem compare-and-swap atau jaminan durability setelah power loss.
Read-only Save As hanya ke target baru. Overwrite target lain perlu parameter
intent eksplisit; UI decision tetap milik lifecycle 05. Save biasa tidak berubah
menjadi Save As bila alias sumber retarget.

Backup migrasi memakai exclusive create, byte asli/fsync/hash, nama digest,
tidak menimpa backup lain, lalu recheck baseline sebelum replace. Belum ada edge
migrasi historis yang didukung; `migration_backup=True` adalah mekanisme untuk
orchestrator migrasi mendatang, bukan alasan menerima versi tidak dikenal.

BlobStore immutable process-local (budget 512 MiB) menyediakan adapter two-phase
03, staging ID sekali pakai, roots terpisah per dispatcher dan leases mandiri bagi
job/recovery/named snapshot. GC dilarang selama prepare; undo/redo tetap roots.
Commit hanya swap metadata di memori, tanpa filesystem/decode/callback. Snapshot
job memegang referensi bytes sampai selesai. Persisted recovery inventory lintas
restart milik 14/39B; container native tidak menyimpan history atau leases.

Fixture JSON historis dan final 02 tetap utuh. PNG lamanya memiliki CRC IDAT rusak:
validator JSON/hash menerima byte tersebut, decoder Qt secara benar menolak.
Fixture ZIP baru mengganti PNG dengan RGBA valid dan memperbarui hash/path/index,
tanpa melemahkan decoder atau tes historis. Generator contoh hanya fixture;
aplikasi menggunakan modul `persistence`, tidak mengimpor script generator.

Referensi resmi yang diperiksa untuk implementasi:
[QLockFile](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QLockFile.html),
[QImageReader](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QImageReader.html),
[os.replace](https://docs.python.org/3.12/library/os.html#os.replace).
Bukti eksekusi berada di [baseline 04](../baseline-segment04.md).
