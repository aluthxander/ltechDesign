# ADR 0006 — Batas transaksi konten

Status: accepted (desain). Tanggal: 21 Oktober 2026.

Konteks: GUI dan MCP harus memakai undo/revision yang sama tanpa memasukkan viewport dan output file dalam rollback konten.

Keputusan: dispatcher tunggal dengan plan/validate/publish atomik, layout dan registered asset references dalam commit. Satu transaksi berhasil termasuk undo/redo menaikkan counter sekali; event hanya setelah commit. Selection/pan/zoom/active page adalah event sesi terpisah. Save/export/preview job di luar batch konten. Import+create memakai staging atomik. Guides manual P1 adalah konten undoable yang tidak diekspor.

Alasan: save/export tidak bisa dibatalkan dengan rollback registry node; session selection tidak membuat revision conflict konten.

Konsekuensi: gesture hanya preview ephemeral lalu satu undo entry. Dirty memakai semantic save checkpoint, bukan kesamaan revision. Save snapshot lama tidak menandai edit baru clean. Failed batch tidak menyisakan model/history/events/aset. 03 membuktikan engine, 13 layout atomik, 18/19 integrasi. Detail: architecture bagian 6.
