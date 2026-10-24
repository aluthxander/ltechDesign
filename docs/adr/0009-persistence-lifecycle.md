# ADR 0009 — Proyek portabel dan admission staging

Status: accepted (lifecycle); blocker spesifikasi ditutup ADR 0010. Tanggal: 21 Oktober 2026.

Konteks: PRD 1.2 mewajibkan `.ltechdesign`, tetapi spesifikasi normatif dan contoh format belum ada di baseline repository.

Keputusan: Open dan Import Project memakai satu loader/validator dan membuka dokumen editable utuh dengan ownership sumber. Load/migration/asset verification dalam staging sebelum tab/session aktif berubah. Save memakai temp pada filesystem tujuan, validation, baseline recheck lalu replace atomik; backup sebelum menulis hasil migrasi. Font/aset embedded mengikuti spec, tanpa absolute path/database/preview flatten untuk restore. Format/app/PRD versions terpisah; session/history/jobs/locks tidak portabel.

Alasan: thumbnail atau kode generator fixture tidak memulihkan model editable. Pada awal 00, exact schema tidak diasumsikan karena spesifikasi yang dirujuk belum ada. Pengguna kemudian meminta spesifikasi baru dibuat; asal-usul dan baseline-nya dicatat ADR 0010.

Konsekuensi: 00B menetapkan dan mencocokkan spesifikasi dokumentasi baru sesuai otorisasi pengguna. 02 mengimplementasikan typed schema/fixtures, 04 codec, 05 admission GUI, 14 recovery dan 22 AT-31–AT-34 penuh. Field manifest, revision checkpoint dan extension/capability rules sekarang ditetapkan pada spesifikasi 1.0; conformance aplikasi tetap belum diuji. Lifecycle termasuk Save As, read-only, close/reload ada di architecture bagian 8.
