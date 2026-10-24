# ADR 0013 — Dispatcher lokal, publication dan retention ports

Status: accepted; bukti domain lokal segmen 03. Tanggal: 22 Oktober 2026.
Melengkapi ADR 0006/0007; tidak mengubah format native 1.0.

`commands.Dispatcher` menjadi pemilik snapshot `DocumentSession` pada satu owner
thread. GUI dan AI memakai `Request`/typed operation union yang sama. Authenticated
`client_id` datang dari adapter tepercaya, bukan field payload. Adapter IPC kelak
harus enqueue ke owner; pemanggilan langsung dari thread lain ditolak. Project
immutable dapat dibuat oleh loader/planner, tetapi publication live hanya dispatcher.

Draft privat menampung operasi berurutan, normalization group, validasi hierarchy,
bindings/font/aset dan hasil hook layout murni. Satu assignment `_State` memublikasikan
snapshot, history dan revision +1; transaksi valid tanpa perubahan juga naik sekali.
Undo/redo memulihkan snapshot lengkap dan menaikkan revision, bukan mengembalikan
counter lama. Kesalahan planning/layout/prepare/cancel tidak memublikasikan state
atau event. Event immutable diterbitkan setelah commit dan receipt final tersedia;
kegagalan subscriber dicatat tanpa mengubah sukses menjadi gagal. Reentrant mutasi
baru mendapat `queue_full`; caller harus enqueue setelah notification selesai.

`Update` mengganti properti authoring node lengkap, bukan identity/type/hierarchy.
Move memakai delta relatif parent; reorder memakai indeks akhir setelah detach.
Reparent (termasuk lintas page) mempertahankan world similarity. Group siblings
diurutkan menurut paint order dan ditempatkan pada posisi pilihan teratas. Default
preserve-appearance menolak pilihan tidak contiguous dan perubahan ancestor
clip/opacity/visibility/shadow; `preserve_appearance=False` adalah intent eksplisit
mengubah konteks compositing. Ungroup juga menolak group dengan binding yang belum
dapat dipertahankan. Group geometry diturunkan dari subtree; update dimensinya
langsung ditolak, resize menggunakan uniform scale. Node dengan binding yang
materialized value-nya berubah harus diperbaiki dalam batch yang sama atau ditolak.
Duplicate subtree meremap node/parent/children/binding, berbagi ID aset/font/token,
dan mengembalikan pasangan ID. Opaque extensions memerlukan remap adapter sebelum
duplicate; operasi ditolak sampai adapter ada. Duplicate Project bukan operasi 03.

History awal 128 MiB per admission. Charge memakai traversal ukuran object Python
(termasuk registry dan opaque bytes), shared objects dihitung sekali per entry tetapi
dihitung ulang antar-entry agar konservatif. Ini budget retensi engine, bukan batas
RSS proses. Eviction membuang entry tertua utuh; entry tunggal melebihi budget tetap
boleh commit tetapi langsung dievict dan hasil/event melaporkan jumlah eviction.
`clear_history` melepaskan akar history tanpa mutasi konten; UI peringatan pemangkasan
dan benchmark 1.000 node tetap 05/08/23.

AssetRetention adalah port dua fase per admission. `prepare(roots, staged)` melakukan
seluruh pekerjaan fallible, memvalidasi metadata/integrity/ownership staging, dan
menahan root lama hingga barrier. `commit` wajib swap registration/roots in-memory
tanpa exception, callback, GC atau I/O; `abort`/`discard` wajib idempotent dan
non-throwing. Ini prasyarat adapter, bukan distributed transaction atau journal.
Pelanggaran kontrak adapter tidak dapat dijamin rollback oleh Python dispatcher.
Akar engine mencakup seluruh registrasi live + before/after undo/redo. Blob immutable
di store terpisah. Store 04 harus menambahkan lease snapshot/recovery/job secara
independen dan melarang GC saat staging commit bersaing; timeout bukan pelepasan
lease. Default MetadataOnlyRetention tidak mengaku memiliki bytes dan menolak import
aset baru. Tes memakai conformance double, bukan blob store produksi. Cancel diperiksa
sebelum planning dan setelah prepare; sesudah barrier hasil tetap sukses.

Dedup key adalah client + admission/session + request ID. Canonical digest mencakup
operation discriminator, seluruh typed defaults, revision, source dan action name;
keys diurutkan, finite number integral dan signed zero dinormalisasi. Correlation ID,
cancellation signal dan client credential tidak masuk payload digest. Ledger menyimpan
digest + final result/error, bukan snapshot dokumen. Kapasitas default 4.096 entry,
configurable; retensi minimum 1.800 detik sejak hasil final (monotonic clock), in-flight
tidak dievict. Request sama in-flight menerima Future yang sama dan tidak dapat
membatalkan owner dengan `Future.cancel()`. Dedup mendahului stale revision. Error
admission malformed/wrong-session/capacity/busy tidak membuat receipt; error transaksi
termasuk cancellation disimpan. Retry receipt cancelled memerlukan intent/request ID
baru setelah rekonsiliasi. Close/restart/expiry menghilangkan jaminan retry: tidak ada
exactly-once lintas crash tanpa journal. Real transport reconnect tetap 18/19.

Clean checkpoint berupa fingerprint semantic content, terpisah dari revision.
Save job menangkap checkpoint dan lease snapshot; setelah side-effect sukses memanggil
`mark_saved` pada owner. Save snapshot lama tidak membersihkan edit baru; undo ke
konten tersimpan dapat clean pada revision lebih besar. Save jobs harus diserialkan
oleh lifecycle service 04/05. Manifest inventory/hash dan saved_revision ditulis oleh
codec/save job, bukan dirty checkpoint. Satu drag melakukan preview ephemeral lalu
satu batch saat release dengan base revision; conflict membatalkan/rebase preview,
tidak menimpa perubahan AI. Session selection/viewport dan save/export tidak ada dalam
operation union. Hook layout dipanggil sebelum publication, tetapi evaluator nyata
belum ada: layout/constraints aktif tetap `unsupported_capability` sampai 13.

Bukti: [baseline 03](../baseline-segment03.md), `tests/test_commands.py`.
Renderer/export/UI/IPC memakai snapshot/event yang sama pada segmen pemiliknya;
tidak ada QGraphicsItem sebagai sumber model atau klaim visual dari tes domain.
