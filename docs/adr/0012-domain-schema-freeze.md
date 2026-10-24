# ADR 0012 — Freeze domain dan schema 1.0

Status: accepted, implementasi segmen 02. Tanggal: 21 Oktober 2026.

Domain memakai frozen/slots dataclasses, tuple dan defensive-copy mapping proxy.
Constructor memeriksa tipe/range dan invariants lokal; Document memeriksa graph
serta geometry group; Project memeriksa hubungan lintas-member, inventory dan
capabilities. Tidak ada import Qt, IO filesystem, resolver font atau transport.
Schema Draft 2020-12 dihasilkan dari anotasi yang sama dengan typed parser.
Semua field tetap wajib di file, termasuk field nullable; default hanya saat create.

`schema_version=1.0`, ID legacy sah dipreservasi, ID baru UUID4. Content revision
runtime awal 0 per DocumentSession; session ID tidak dapat diserialisasi sebagai
member. Checkpoint hanya `manifest.saved_revision`. Kontrak `data.text`,
`data.typography`, FontId dan property-path binding tetap sesuai baseline 00B.
Contoh 00B dibekukan sebagai fixture historis yang diuji tanpa migrasi. Tidak ada
klaim dukungan versi 0.x atau versi native lain.

Transform mempertahankan `T(x,y) T(p) R S T(-p)`, pivot lokal dan positive uniform
scale. Zero extent pada satu sumbu line/group sah. Dimensi positif tidak memakai
epsilon untuk mengubah nol menjadi sah. Verifikasi hasil geometri group memakai
abs 1e-9 logical px dan rel 1e-12; tidak membulatkan geometry atau serialized
rotation. Decomposition similarity memeriksa residual ternormalisasi 1e-12.

Geometry subtree mencakup hidden nodes dan overflow descendants tanpa efek/clip.
Visual bounds domain adalah conservative world AABB, termasuk stroke/shadow dan
intersection AABB clip ancestors. Rounded clip, text ink, transparent pixels dan
isolated compositing harus dibuktikan renderer 06A. `blur` dibekukan sebagai sigma
Gaussian logical px dengan support 3 sigma; renderer wajib konsisten. Hit bounds
menambah physical screen tolerance / zoom / DPR. Bounds tidak disimpan ke node.

Project menolak unsupported required capability. Layout/constraints dapat
direpresentasikan dan JSON round-trip sebagai Document untuk diagnostic, tetapi
Project admission menolaknya sampai evaluator 13 tersedia. Tidak ada adapter
extension required; unknown optional metadata `preserve_opaque` mempertahankan
byte dan asset refs persis. Malformed workspace ditolak oleh boundary 02; tidak
diabaikan tanpa warning. Reader 04 dapat menambah fallback eksplisit sesuai spec.

Migration registry mengharuskan validator tiap versi, successor tunggal tanpa
siklus, staging copy dan laporan langkah. Hanya validator 1.0 terdaftar; tes
versi sintetis membuktikan mekanismenya tanpa mengiklankan migrasi historis.
Tidak ada penulisan sumber atau backup IO pada registry domain.

Bukti: [tes model](../../tests/test_domain.py),
[tes lintas-member](../../tests/test_project_format.py),
[baseline 02](../baseline-segment02.md). Actual ZIP, decode/sanitasi SVG, ownership,
renderer dan command/undo tetap mengikuti segmen pemiliknya.
