# ADR 0018 — Drawing intents dan selection lokal

Accepted, 24 Oktober 2026. Pemilik: 07. Acuan PRD FR-003/004/006,
20.2–20.3. Tidak mengubah schema native 1.0 atau kontrak dispatcher.

- Preset PRD dan pure authoring factory berada di domain tanpa Qt. Konversi
  mm/cm/in memakai DPI, dimensi tersimpan logical pixel; unit/DPI/background
  tetap FrameData. Orientasi menukar sisi sebelum konversi, tanpa pembulatan
  pixel. Preset cetak A4/A3 memakai asumsi awal 300 DPI, digital 96 DPI.
- Dialog artboard menghasilkan satu Create root pada page aktif, ditempatkan
  100 logical pixel di kanan root terluar (origin 0 untuk page kosong).
  Mengubah isian preset mengalihkan label ke Custom; tidak mengubah konten
  sampai diterima. Artboard root-only mengikuti kontrak sebelumnya.
- EditorCanvas menerjemahkan pointer viewport → scene → inverse world parent.
  Parent adalah frame/artboard eligible teratas pada titik awal, tanpa mengikuti
  selection atau mengubah hierarchy yang sudah ada. Tidak memasukkan anak ke
  group yang memerlukan normalisasi; group authoring tetap 08. Tidak ada parent
  eligible berarti root page. Hidden/locked ancestor menggugurkan subtree.
- Drawing drag membuat rectangle/ellipse/frame/line atau polygon N sisi (3–64,
  default 5), polygon dinormalisasi ke kotak drag. Line menyimpan kedua endpoint
  sehingga arah negatif/horizontal/vertikal sah; shape lain memakai bounds positif.
  Gesture di bawah 3 logical viewport pixel atau area nol dibatalkan.
- Preview outline adalah overlay view, tidak masuk scene/model/history/export.
  Release mengirim satu Create melalui StudioWindow.execute dan dispatcher dengan
  expected_revision saat press, action_name dan ID baru stabil. Revision/page
  berubah, read-only, Esc, right/middle click, tool/focus/tab berubah membatalkan
  preview. Konflik tidak ditulis ulang memakai revision terbaru.
- Selection adalah state sesi/tab/page tanpa revision/undo. Click memilih node
  eligible teratas dalam paint order; Shift/Ctrl click toggle, Shift/Ctrl marquee
  union; marquee memakai full containment visual path yang sudah di-clip.
  Select All mencakup seluruh node eligible pada page aktif. Child bisa dipilih
  langsung; ancestor dan child dapat berada dalam selection bersamaan.
- Hit geometry menggunakan path/transform/rounded clip renderer yang sama,
  stroke center-aligned dan toleransi 4 physical pixel /(zoom × DPR). Hidden/locked
  ancestor tidak dapat dipilih dari canvas maupun Layers. Bounding box/preview
  adalah overlay, tidak ikut Save atau export. Handles/transform tetap 08.

API Qt diperiksa pada dokumentasi resmi [QGraphicsView](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QGraphicsView.html)
dan [QPainterPathStroker](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainterPathStroker.html).
Implementasi diuji pada dependency terkunci Python 3.12.12/PySide6 dan Qt 6.10.2;
tidak menambah dependency. Bukti dan batas ada di [baseline 07](../baseline-segment07.md).
