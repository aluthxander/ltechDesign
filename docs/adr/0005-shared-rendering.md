# ADR 0005 — Satu kontrak drawing untuk semua target

Status: accepted (desain). Tanggal: 21 Oktober 2026.

Konteks: canvas Qt item default dan export terpisah berisiko berbeda alpha, clip, teks dan bounds.

Keputusan: satu snapshot traversal/render plan dan QPainter primitives; scene adapter hanya indexing/cache/input. Transform, text layout/font resolver, style/stroke/shadow, clipping dan isolation sama untuk canvas/QImage/PDF. Heavy renderer menggunakan subprocess offscreen dengan QGuiApplication di main thread prosesnya. Tidak memakai widget/scene live sebagai input worker.

Alasan: konsistensi visual lebih mudah dibuktikan pada shared primitives daripada dua renderer. DPR memengaruhi sampling layar saja.

Konsekuensi: raster fallback group/shadow juga dipakai PDF dan dilaporkan. Resolusi/toleransi font/alpha dibuktikan 06A, bukan dipin berdasarkan asumsi; text/image integrasi 11/12, raster/PDF produk lengkap 15/16, headless 17. PDF multipage dasar P0. 06A harus menghasilkan artifact nyata dan memicu smoke-build jika plugin berubah. Detail: architecture bagian 5 dan 9.
