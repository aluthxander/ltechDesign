# ADR 0008 — Owner thread dan attached/headless bridge

Status: accepted (desain). Tanggal: 21 Oktober 2026.

Konteks: MCP subprocess tidak boleh memodifikasi scene atau menyimpan salinan stale dari file milik GUI.

Keputusan: live sessions/dispatcher attached di GUI main thread; headless satu owner event-loop thread. SDK stdio di console process, QLocalServer/QLocalSocket named pipe pada Windows untuk bridge, user-only ACL + token/challenge + instance/protocol handshake. Endpoint acak/descriptor per-user, framing length-prefix JSON bounded. QThread actors menangani IPC/persistence I/O, subprocess menangani render/CPU berat; semuanya snapshot/DTO immutable dan queued completion. Owner recheck revision sebelum publish plan worker.

Alasan: satu authority konten menghindari race history/revision. Named pipe lokal bukan layanan cloud/HTTP. Tidak perlu menjalankan server HTTP untuk stdio.

Konsekuensi: authenticated client scope bertahan reconnect, timeout 30 detik tidak berarti rollback. Queue/backpressure wajib, GUI tidak blocking wait. Shutdown/close menghentikan admission, drain commit barrier sebelum unlock. 17A wajib subprocess → dispatcher → canvas → undo nyata; 19A lifecycle dan 19B concurrency. Official SDK/protocol pins di 18A; ACL behavior dan alias path diuji 04A/17A/20. Detail: architecture bagian 10–11.

Headless console meluncurkan owner child; attached tidak membuat writer child. EOF proxy attached tidak menutup GUI, EOF headless menutup child dengan graceful drain. Completion worker membawa generation sesi agar hasil lama tidak memulihkan sesi tertutup.
