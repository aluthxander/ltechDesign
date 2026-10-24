# ADR 0019 — Editor transform, clipboard dan history

Accepted, 24 Oktober 2026; pemilik08, integrasi layout13. Kontrak PRD20.2/20.3.
Format native1.0, hierarchy dan dispatcher lifecycle tidak berubah.

- Operasi semantic baru `TransformNodes`, `ResizeNode`, `ScaleNodes`, `EditNodes`,
  `ReparentNodes` dan `PasteNodes` melewati dispatcher yang sama. Multiselect
  membuang descendant bila ancestor dipilih; satu aksi/gesture = satu transaksi
  dan satu undo entry. Maksimum100 operasi/payload4MiB tetap ditegakkan; operasi
  selection dibatasi10.000 target, bukan memecah gesture menjadi commit parsial.
- Drag/nudge memakai delta dunia, dikonversi inverse parent masing-masing.
  Rotate memakai pivot eksplisit node tunggal atau pusat geometry selection;
  Shift membulatkan delta ke15°. Shift saat drag membatasi sumbu dunia dominan.
  Shift/Ctrl click tetap toggle selection; modifier dipasang sesudah press bila
  ingin mengubah constraint drag, bukan mengubah selection awal.
- Delapan resize handles mengikuti sumbu lokal node tunggal; multiselect memakai
  AABB geometry dunia. Shape resize mengubah geometry/pivot/translation bersama
  dengan anchor berlawanan tetap; Shift mempertahankan rasio, Alt memakai pusat
  geometry sebagai anchor. Rotasi memakai pivot eksplisit, bukan pusat tersebut.
  Minimum extent positif0,01 logical px; line mempertahankan extent nol yang sah.
- Group dan multiselect resize selalu positive uniform. Group mengubah scale,
  bukan geometry anak. `ScaleNodes` pada frame/artboard mengubah geometry dan
  posisi origin dengan scale lama; anak default fixed tetap pada koordinat lokal.
  Frame ber-constraints/layout ditolak `layout_evaluator_unavailable` sampai13;
  belum ada evaluator, sehingga checkpoint08.layout tidak boleh verified.
- Preview transform berupa wireframe/handles ephemeral, tanpa memindahkan scene
  item atau membuat history. Isi asli tetap digambar sampai release. Escape,
  tool/focus/tab/page/revision berubah membatalkan. Release memakai revision saat
  press; konflik tidak diulang memakai revision baru. Handles/preview tidak ikut
  serialization atau shared export.
- Group hanya siblings contiguous sesuai mode preserve-appearance yang sudah
  ada. Ungroup/reparent mempertahankan matriks dunia; perubahan ancestor clipping,
  isolation atau stacking yang tidak dapat dipertahankan ditolak atomik, tanpa
  flatten. Reparent tersedia pada context menu, memakai command lama di dalam
  semantic selection command. Context target mematuhi hidden/locked ancestry.
- Clipboard MIME `application/x-ltechdesign-nodes-v1` berisi native ZIP tervalidasi,
  satu page/subtree closure, world pose roots, font/token dependencies dan byte
  embedded assets. Batas64MiB compressed/expanded,64 aset; setiap paste membuat
  ID node/asset/font/token/page baru. Tidak ada path/file/database sumber wajib.
  Copy/cut mem-pin snapshot; ZIP/validation/remap/staging berlangsung pada worker,
  akses QClipboard dan dispatch hanya GUI thread. Cut menghapus sesudah clipboard
  terpasang, dengan revision sumber. Paste asset registration dan node insertion
  satu transaksi; gagal/stale membersihkan staging. Clipboard byte tidak menjadi
  aset eksternal runtime yang dibutuhkan undo atau Save.
- Paste/duplicate offset10 logical pixel dunia; paste ke frame/artboard tunggal
  yang dipilih, selain itu root page aktif. Artboard selalu root. Root geometry
  dipertahankan relatif dunia lalu dikonversi ke parent tujuan. Konteks clip/opacity
  ancestor yang tidak disalin tidak menjadi bagian subtree clipboard; copy tidak
  menjanjikan render identik setelah konteks tersebut berubah. Extension opaque
  tanpa remap adapter ditolak. Binding transform yang tidak cocok setelah detach
  juga gagal validasi, bukan dibuang atau mengubah token sumber diam-diam.
- Ctrl+C/X/V/D/G, Ctrl+Shift+G, Ctrl+Z/Shift+Z, Delete/Backspace,
  Ctrl+]/[ serta panah1px/Shift+panah10px hanya ditangani canvas dan Layers.
  QAction Edit tidak mendaftarkan global shortcut yang mengambil input teks.
  Input nama/spinbox mempertahankan editing/clipboard/undo-nya sendiri.
- Baseline08 mengukur event timer+repaint native10 detik per fase, p95/p99/max,
  freeze sebagai gap event dan excess di atas16ms, waktu release/commit, batch100
  commit tanpa subscriber GUI, GUI roundtrip/heartbeat dan resident memory.
  Tidak mengklaim mesin acuan rilis atau cold startup. Optimisasi lokal:
  cache fingerprint immutable setelah publish, scene sync identik, geometry
  overlay, bulk QItemSelection dan satu refresh per publication. Tidak melonggarkan
  validasi model, batch limit atau toleransi render.

API Qt dirujuk ke dokumentasi resmi [QClipboard](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QClipboard.html),
[QMimeData](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QMimeData.html) dan
[QItemSelectionModel](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QItemSelectionModel.html).
Dependency aktual dan hasil ada di [baseline08](../baseline-segment08.md).
