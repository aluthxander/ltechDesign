# ADR 0016 — Shared painter traversal dan root invalidation

Accepted, 23 Oktober 2026. Scope 06; conformance lintas target lengkap 06A.

Scene mempertahankan NodeItem per stable NodeId. Child item hanya index geometry/
world matrix; root item menggambar subtree dengan traversal QPainter yang sama
untuk canvas dan offscreen image. Karena itu parent clipping, z-order dan isolated
opacity tidak bergantung pada default QGraphicsItem opacity/child stacking.
Root invalidation mengikuti perubahan node dan ancestor lama/baru, item tidak
dibuat ulang setiap edit. Scene tidak menjadi sumber konten. Sync masih menelusuri
model dan menghitung conservative bounds; tidak mengklaim patch O(1) atau benchmark
1.000 objek sebelum segmen 23. Root raster cache/tiling merupakan optimasi mendatang.

Drawing memakai explicit local/world matrix domain, fill/stroke/background, path
rounded corner dengan proportional radius clamp, line/ellipse/polygon dan clipping
path yang sama. Positive uniform scale tetap kontrak. Setiap node ber-opacity
nontrivial diisolasi pada QImage ARGB premultiplied; opacity diaplikasikan sekali
pada composite. Nested buffers memakai sampling device transform (termasuk DPR),
origin/padding bounds lokal dan shared live allocation budget 64 megapixel. Output
image sendiri juga dihitung. Limit/memory error eksplisit; canvas menggambar kode
error, offscreen menolak. PDF metadata rasterization baru dibuktikan di 06A/16.

Geometry bounds terpisah dari conservative visual bounds (stroke/clip/overflow)
dan hit bounds domain dengan toleransi layar. Rounded clip tetap path, bukan AABB.
Selection dan grid hanya view foreground/background; shared drawing dan
QGraphicsScene.render tidak memasukkannya. Canvas pan/zoom/selection tidak menulis
model atau history; zoom 2%–1600%, middle-button pan, Ctrl+wheel anchored cursor,
fit artboard dan zoom selection memakai logical units, bukan export DPI.

Text/image/SVG ditandai placeholder dan warning pada canvas, shadow ditandai warning.
Strict render_image menolak fitur belum didukung (tidak menghasilkan file yang
seolah lengkap). Tidak membuang metadata; persistence/undo tetap utuh. Pemilik
text/image 11/12; shadow/style lengkap 10A; fixture shared cross-target 06A.
Ini bukan kontrak renderer final untuk fitur tersebut. Tidak ada dependency baru.

Referensi resmi diperiksa: [QPainter](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainter.html),
[QGraphicsView](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QGraphicsView.html).
