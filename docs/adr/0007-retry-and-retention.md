# ADR 0007 — Retry terbatas dan retensi aset

Status: accepted (desain). Tanggal: 21 Oktober 2026.

Konteks: respons bisa hilang setelah commit; cleanup aset tidak boleh merusak undo/recovery/export.

Keputusan: owner ledger keyed authenticated client/session/request ID, canonical payload digest, cek sebelum revision. Sama/in-flight join atau hasil lama; beda payload conflict. Retensi minimal 30 menit pada sesi hidup; kapasitas penuh menolak entry baru sebelum commit. Client context tetap sama saat reconnect; create_project memakai server-instance scope. Side effect memakai job ID/request/snapshot revision. Tidak menjamin exactly-once setelah restart/crash/expiry.

Alasan: menjalankan ulang request stale tanpa rekonsiliasi dapat menggandakan objek; memakai revision dulu akan menolak retry yang sebenarnya sukses.

Konsekuensi: history budget 128 MiB, eviction utuh; asset GC menahan live/history/redo/snapshot/recovery/jobs termasuk staging. Durable recovery menyimpan referensi untuk restart. Cancel sesudah commit tidak menghapus side effect. 03/04/14 menyiapkan engine/store; 18B/18C/19B menguji respons hilang, capacity, restart, GC dan cancellation. Detail: architecture bagian 7 dan 9.
