# ADR 0015 — GUI session shell dan persistence worker

Accepted, 23 Oktober 2026. Pemilik pembuktian 05.

Setiap tab mempunyai Dispatcher owner GUI, selection/page state dan BlobStore
sendiri. FileHandle hanya lifecycle/path/ownership; bukan model editor live.
Open dan Import adalah loader sama yang membuka tab lengkap. Existing canonical
path fokus ke sesi sama; writer luar proses dibuka read-only dengan label jelas.
Reload memvalidasi staging sebelum mengganti model/history/session_id; lock tetap
dipegang. Save snapshot mengembalikan checkpoint; Save As sukses mempromosikan
dispatcher read-only melalui lifecycle setter owner thread.

Adapter sinkron PersistenceService/QLockFile tidak memerlukan QObject event loop:
05 memilih executor satu worker ketimbang actor QThread yang direncanakan 00.
Semua I/O/decode/admission byte-store berjalan di worker yang sama; queued signal
menerbitkan admission dan hasil pada GUI. Maksimum satu job aktif, lifecycle
actions ditolak saat busy; widget dan dispatcher tidak dipindah ke worker.
05 tidak mengiklankan job scheduler/cancellation MCP 18C. Shutdown menunggu hasil
job, lalu unsaved decision dan close tiap tab sebelum keluar. Dialog cancel/save
error tidak menutup tab.

Canvas QGraphicsScene/View disediakan sebagai placeholder disabled sampai 06;
tidak merender preview flatten sebagai pengganti model. Tools drawing/export yang
belum ada disabled. Rename objek di Inspector adalah command Update dan mengikuti
serialization/undo; rendering/export menunggu subsistem pemilik. Tidak ada format
atau dependency runtime baru. Bukti di baseline-segment05.md.
