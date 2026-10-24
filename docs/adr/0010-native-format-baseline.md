# ADR 0010 — Menetapkan baseline format native 1.0

Status: accepted (kontrak dokumentasi). Tanggal: 21 Oktober 2026.

Konteks: baseline repository tidak memuat spesifikasi yang dirujuk PRD. Pengguna kemudian meminta spesifikasi tersebut dibuat. Karena itu B-001 diselesaikan dengan dokumen baru yang dinyatakan asal-usulnya, bukan pemulihan artefak historis atau implementasi segmen berikutnya.

Keputusan: [ltechdesign-file-format.md](../ltechdesign-file-format.md) menjadi source of truth format ltechdesign.project/container 1.0/document schema 1.0. Inventory mengecualikan manifest agar tidak self-hash, semua aset embedded content-addressed SHA-256, stable IDs, typed per-node payload dan token/font refs. Revision persisten hanya manifest.saved_revision sebagai checkpoint informasional; runtime revision dimulai 0 per admission/session baru. Unknown core field/version/required capability tidak dibuang; optional metadata extension dipreservasi opaque, clone unknown extension ditolak sampai remap adapter tersedia.

Alasan: format harus portabel/editable dan dapat divalidasi tanpa Qt/login/cloud. Menuliskan field dan error policy sekarang mencegah codec/GUI/MCP menetapkan format berbeda. Schema bersifat normatif, sedangkan validators dan domain implementation tetap milik 02.

Konsekuensi: ADR 0009 tetap berlaku untuk lifecycle, tetapi status missing-spec/conformance blocker digantikan keputusan ini. Arsitektur/matriks/progres diperbarui, contoh JSON dan audit kontrak tidak dianggap loader ZIP, native fixture, renderer atau bukti FR-002. Segmen 02/04 mengimplementasikan dan menguji schema/codec sesuai baseline ini; perubahan kompatibilitas wajib ADR/migration/version yang sesuai. 00B hanya dapat verified setelah audit/cross-check dokumentasi selesai.
