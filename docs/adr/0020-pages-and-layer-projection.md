# ADR0020 — Pages dan proyeksi hierarchy lokal

Accepted24 Oktober2026, pemilik09. Acuan FR-001/005, PRD7.3,20.2–20.3.
Tidak mengubah format native1.0 atau mengimplementasikan layout13.

- `CreatePage`, `UpdatePage`, `DuplicatePage`, `DeletePage`, `SetLayerState` dan
  `RelocateNodes` adalah typed content operations pada dispatcher yang sama.
  Seluruh validasi, normalization, revision, history/dedup dan asset retention
  tetap satu transaksi. Tidak ada mutasi domain melalui QTreeWidget.
- Create page menerima page kosong dan insertion index; rename mempertahankan ID.
  Duplicate menyisipkan sesudah sumber, membuat ID page/node baru dan meremap
  parent/children/root IDs serta token bindings. Referensi asset/font/token dalam
  dokumen yang sama tetap memakai registry immutable yang sama; tidak menggandakan
  byte atau kehilangan embedded assets. Opaque extensions tanpa remap adapter
  ditolak seperti duplicate subtree sebelumnya.
- Delete menolak page terakhir. Page nonempty memerlukan `delete_contents=True`;
  GUI meminta pilihan eksplisit untuk menghapus seluruh subtree, tanpa memindahkan
  konten diam-diam. Assets/fonts/tokens registry tetap tersedia untuk content dan
  history; binding node yang dihapus dibersihkan bersama subtree.
- Delete juga membersihkan referensi page yang tak lagi sah pada workspace.json
  opsional. Draft menghasilkan workspace yang valid; layout callback harus
  mempertahankan workspace hasil draft tersebut. Guard dispatcher membandingkan
  hasil callback dengan planned workspace, bukan workspace sebelum penghapusan.
  Pan/zoom/selection tidak menjadi content command; ini hanya sanitasi referensi
  akibat penghapusan page. Undo mengembalikan snapshot termasuk workspace aslinya.
- Page aktif runtime memakai ID stabil, dengan indeks hanya proyeksi untuk canvas.
  Insert/rename/duplicate dari caller lain tidak mengganti page aktif. Jika page
  aktif hilang, pilih page pada indeks lama yang masih sah (atau terakhir).
  Pilihan yang hilang, pindah page, hidden atau locked oleh ancestor dikeluarkan
  dari selection. Undo konten tidak mengembalikan state selection/page secara
  otomatis bila page runtime sekarang masih sah.
- Tree terurut visual atas→bawah membalik urutan siblings domain (z tertinggi di
  atas). Drop Above berarti setelah target pada urutan domain; Below berarti
  sebelum target; OnItem append sebagai child teratas, OnViewport append root.
  Indeks RelocateNodes dihitung sesudah semua selected roots dilepas, dengan
  canonical source paint order. Descendant dari ancestor yang ikut dipilih tidak
  dipindahkan dua kali. Cycle, leaf parent, nested artboard dan invalid index
  ditolak atomik. Cross-page domain relocation memperbarui page_id seluruh subtree.
- Semua relocate mempertahankan world transform dengan inverse parent baru.
  Mode default preserve appearance menolak perubahan clip/isolation context.
  Checkbox eksplisit dapat mengizinkan perubahan konteks; tidak menghilangkan
  jaminan world geometry. Domain tetap menolak shear/flip/negative scale.
- MIME drag bertipe memuat session/page/revision dan stable node IDs, dibatasi
  JSON4MiB serta target10.000 sesuai dispatcher selection boundary. Drop lama/
  sesi lain/page lain ditolak. Qt dropEvent tidak memanggil default item move;
  hanya command publication yang membangun proyeksi tree dan z-order canvas.
  Qt drag state diakhiri eksplisit tanpa memanggil mutasi model default.
- Hidden/locked ancestry tetap menggugurkan canvas/tree content selection dan
  drag. Checkbox Shown/Locked adalah administrasi own flags agar objek dapat
  ditampilkan/dibuka kuncinya tanpa harus dipilih di canvas. Tidak menulis flag
  anak secara rekursif. Read-only menonaktifkan seluruh content controls.
- Search casefold nama/tipe dan type filter adalah state per tab, bukan history.
  Ancestor dari hasil pencarian tetap ditampilkan; filter tidak mengubah domain
  atau selection. Selection canvas baru di luar filter membersihkan filter untuk
  menampilkan path. Collapse state dipertahankan menurut stable node ID.
- Selection tree→canvas memakai guarded projection tanpa memancarkan perubahan
  canvas kembali; canvas→tree memakai bulk QItemSelection dengan signals blocked.
  Artboard list memuat root artboard pada page aktif; klik memilih, double-click
  fit. Artboard hidden/locked tetap terdaftar tanpa canvas selection.
- Rename inline menangkap session/revision saat editor dibuka. Commit/checkbox
  intent dipublikasikan pada tick GUI berikutnya agar Qt selesai memakai editor/
  item sebelum rows dibangun ulang. Perubahan revision eksternal tidak boleh
  menimpa konten baru. QLineEdit editor mempertahankan clipboard/undo/arrow/Delete
  miliknya sendiri, tanpa shortcut konten dari event filter Layers.
- Nama tetap data biasa; markup dalam nama di-escape ketika ditampilkan pada
  rich tooltip atau dialog. Tidak menginterpretasikan nama sebagai resource HTML.

API Qt dirujuk pada [QTreeWidget](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QTreeWidget.html),
[QAbstractItemView](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QAbstractItemView.html) dan
[QStyledItemDelegate](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QStyledItemDelegate.html).
Nullable return createEditor sah pada Qt; targeted mypy ignore hanya menutup
kekurangan annotation PySide6.10.2, tanpa menonaktifkan pemeriksaan lain.
Versi/bukti final: [baseline09](../baseline-segment09.md).
