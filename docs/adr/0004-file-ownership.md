# ADR 0004 — Single writer dan external-change detection

Status: accepted (desain). Tanggal: 21 Oktober 2026.

Konteks: revision tidak mencegah GUI dan headless menimpa file yang sama.

Keputusan: canonical path service + QLockFile adapter, lock sepanjang sesi writer dan expiry usia dimatikan. Resolve alias Windows/junction/symlink, cek ulang identity sebelum replace; hardlink multi-link writer ditolak, UNC writer default ditolak sampai terbukti. Open kedua attached ke owner yang sah, read-only atau error. Stale owner diperiksa; ambiguous owner tidak diambil alih. Baseline hash/metadata/identity dicek saat save walaupun ada watcher.

Alasan: koordinasi lokal pengguna yang sama memerlukan ownership proses, terpisah dari optimistic revision dan bukan collaboration.

Konsekuensi: source lock tetap ditahan selama Save As sampai target berhasil, target lock/baseline wajib. Save conflict menawarkan Reload/Save As. Lock tidak melindungi dari program asing yang mengabaikan protokol atau semua TOCTOU races. 04A wajib dua proses nyata, crash/stale lock, external replace, Save As gagal/sukses; 19B integrasi GUI/MCP dan 20 path security. Detail: architecture bagian 8.
