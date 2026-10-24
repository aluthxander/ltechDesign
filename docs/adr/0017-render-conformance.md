# ADR 0017 — Shared text primitive dan device-aligned isolation

Accepted, 06A. Tidak mengubah format native atau menambah dependency/pins.

Primitive fixed-box text memakai QTextLayout dengan reference QImage 96 DPI,
design metrics, explicit font family resources, no hinting dan no font merging.
Font fixture Abel/OFL dipin SHA-256, bukan font default mesin. Missing family/
glyph atau text stroke/sizing yang belum didukung ditolak, tidak silent fallback.
Resolver embedded/system lengkap, per-font warnings dan inline editing milik 11.
Resource injection hanya renderer port; tidak memutasi font metadata/teks domain.

Metrik native dan offscreen awal berbeda (ascent 23,5 vs 24; width 139,953125 vs
141). No-hinting menyamakan metrik. Native glyph rasterization masih berbeda,
maka shaping/layout tetap QTextLayout tetapi draw memakai QRawFont glyph paths
dan posisi glyph run yang sama di seluruh target. Selisih terakhir 474 pixel hanya
di tepi glyph, maksimal 4/255; interior exact. PDF teks berupa vector outline,
bukan searchable text/font embedding. Native document tetap menyimpan TextData
editable. Searchable/embedded PDF text bukan klaim 06A dan akan dievaluasi 11/16.

Group isolation 06 awal membuat bitmap lokal lalu memutarnya saat composition.
PDF image/soft-mask resampling menghasilkan fringe di luar edge band (interior
error sampai 105/255); mengaktifkan smooth sampling saja tidak menyelesaikannya.
Sekarang shared draw_node mengalokasikan buffer pada device-aligned pixel bounds,
menggambar subtree memakai device transform, lalu composite sekali dengan device
transform identity. Clip painter tetap berlaku; nested isolation dan DPR memakai
semantik sama. Budget live buffers 64 MP tetap ditegakkan.

PDF proof adapter memanggil traversal yang sama melalui QPdfWriter; tidak ada
pipeline drawing alternatif. Sampling PDF fallback 2x dengan page size tetap
logical-pixel-to-point (600×400 px @96 → 450×300 pt). LosslessImageRendering
mencegah JPEG artifacts pada fallback. Hanya group opacity membutuhkan image +
soft mask; shape/text lain tetap vector. Return IDs isolation untuk pelaporan
caller; object image/SMask di PDF diperiksa untuk membuktikan fallback aktual.

Adapter PDF ini proof single-page, bukan export service publik: belum atomic jobs,
UI, multipage policy, cancellation/allowlist atau production target permissions.
Itu pemilik 15–17/20. QtPdf/PDFium dipakai test untuk membaca PDF hasil QPdfWriter;
Poppler tidak tersedia di host. PySide6 sudah membawa QtPdf, tidak menambah package.

Conformance tidak memakai toleransi global besar: canvas vs PNG exact; layout
metrics/members native vs offscreen exact; offscreen glyph edge max4, interior0.
PDF interior allowance1/255 (observed0); edge allowance64 hanya dalam band1px
di sekitar edge referensi (observed58), bounding boxes per region ≤1px. Alpha
overlap/nonoverlap127±1, rounded corner0 dan opaque center255 diperiksa. Checker
sendiri diuji menolak kerusakan alpha di interior. Lihat baseline 06A untuk bukti.
