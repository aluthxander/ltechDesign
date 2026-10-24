# ADR 0003 — Similarity transform, pivot dan isolated opacity

Status: accepted (desain). Tanggal: 21 Oktober 2026.

Konteks: reparent parent berotasi, group resize dan alpha overlap harus sama pada undo/canvas/export.

Keputusan: logical pixels, `T(x,y) T(p) R S T(-p)`, world composition; positive uniform scale, tanpa shear/flip. Pivot eksplisit dan default pusat geometry; resize menyelesaikan anchor/pivot/translasi atomik. Reparent memakai inverse parent baru dan mempertahankan matriks dunia. Group geometry dinormalisasi dengan kompensasi transform anak; group resize uniform, frame resize menjalankan layout. Geometry/visual/hit bounds berbeda. Artboard clip default true; frame/group false; rounded fill/clip satu path. Group opacity diterapkan sekali sesudah komposit children terisolasi.

Alasan: menyalin scene bounding box atau menurunkan opacity ke tiap child mengubah desain. Approximation affine bukan pengganti representasi yang benar.

Konsekuensi: nonuniform group scaling butuh ADR/schema baru, bukan backlog tersembunyi MVP. Reparent/ungroup yang tidak dapat mempertahankan konteks clip/compositing ditolak pada mode preserve-appearance; perubahan konteks harus eksplisit. Line horizontal/vertical sah; empty group tidak diresize dengan pembagian nol. PDF boleh raster isolation dengan warning. 02/03 menguji matematika, 06A pixel/geometry, 08 AT-24. Detail termasuk normalisasi/stacking: architecture bagian 5.
