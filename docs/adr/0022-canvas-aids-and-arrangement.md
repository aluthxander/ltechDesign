# ADR 0022 — Canvas aids, screen snapping dan atomic arrangement

Accepted, 25 Oktober 2026 (Asia/Jakarta), pemilik10B. Prasyarat10A verified.
Format native1.0, dependency dan single-writer/dispatcher lifecycle tetap.

- Toleransi snap8 **physical display pixels**; konversi ke logical scene px
  `8 / (zoom × viewport.devicePixelRatioF())`. Koordinat event/widget Qt sudah
  DIP, sehingga DPR tidak diterapkan dua kali. Drag threshold3 physical px dan
  hit/handle tolerances tetap memakai kebijakan physical px. Dimensi ruler24 DIP
  dan label memakai scaling Qt, bukan ukuran konten. DPI dokumen tidak terlibat.
- Grid logical tetap (default20px, positive configurable), origin dunia(0,0).
  Saat zoom kecil renderer melewatkan garis minor dengan faktor2 sampai jarak
  tampilan12 physical px; snap tetap ke grid logical asli. Ruler menampilkan
  logical world coordinates termasuk negatif, major ticks1/2/5×10^n dan minor/5.
  Ruler mengikuti viewportTransform/pan/zoom, tidak menggeser origin dokumen.
  Bar ruler memakai margin viewport terpisah, sehingga tidak menutupi konten atau
  mengambil gesture drawing di tepi. Timer layout dimiliki view dan berhenti
  bersama view, tanpa callback tertunda pada QWidget yang sudah dihapus.
- `SnapIndex` pure-domain mengindeks edge/center geometry AABB dunia page aktif,
  dengan clipping ancestor AABB konservatif. Bukan visual stroke/shadow bounds.
  Hidden/locked node atau ancestor dikecualikan, begitu juga subtree yang sedang
  dipindah. Derived group ancestor dikecualikan agar tidak menarik anaknya sendiri;
  frame/artboard ancestor boleh menjadi referensi. Group geometry tetap mengikuti
  aturan20.2 termasuk hidden children di geometry group. Rounded clip tetap
  dirender tepat oleh shared renderer; candidate AABB bukan uji pixel silhouette.
- Indeks immutable di-cache berdasarkan document identity/page/moving roots;
  nearest lookup memakai bisect. Jarak terdekat menang, tie object sebelum grid,
  lalu coordinate/stable ID; tidak bergantung urutan registry/z-order. Dua sumbu
  move/free-corner dapat snap independen. Shift move menjaga sumbu dominan dunia.
- Move multiselect memakai satu rigid world translation dari union geometry;
  dispatcher mengonversi inverse parent setiap root. Descendant dari selected
  ancestor tidak dipindahkan dua kali. Drawing start/end snap di world, baru
  dikonversi ke parent. Resize side/uniform/group/multiselect menyelesaikan satu
  parameter pada ray handle/anchor; koreksi total handle harus dalam toleransi,
  bukan hanya dekat pada satu sumbu. Free corner memperhitungkan offset klik
  terhadap posisi ideal handle supaya pembulatan event Qt tidak menyisakan drift.
  Minimum extent/anchor/pivot/frame-vs-group dan layout13 tetap kontrak08.
- Rotasi tetap Shift15° yang sudah ada. Nudge1/10 logical px dan input angka
  Inspector adalah intent literal; snap tidak membulatkannya. Posisi final
  gesture muncul pada Inspector melalui publication yang sama.
- `ArrangeNodes` typed command: enam align ke union **world geometry** selection;
  minimum2 roots. Equal-gap distribution H/V minimum3 roots, sort minimum-axis
  lalu stable ID, first/last tetap, negative gaps sah untuk overlap. Semua delta
  dihitung sebelum mutasi dan diterapkan inverse-parent, sehingga rotation/scale,
  ID, parent dan z-order tidak berubah. Invalid/hidden/locked/cross-page target
  ditolak atomik, tidak melakukan partial skip. Normalize group tetap di draft.
  Satu aksi = satu revision/undo/event. GUI tidak mengirim arrangement no-op.
- Rulers/grid/smart-guide visibility, snap master/mode/spacing adalah state view
  per tab. Default rulers+smart guides on, grid/snap off; grid snap dan object snap
  dapat ditoggle independen dari grid visibility. Toggle membatalkan preview aktif,
  tidak menciptakan command. Guides merupakan garis ephemeral hasil snap, clear
  pada release/Escape/focus/page/selection/revision/toggle. Tidak ada manual guide
  record atau drag dari ruler; persisted undoable guides tetap38B.
- Grid/guides digambar pada QGraphicsView dan rulers pada child widget margin,
  tidak menjadi QGraphicsItem/model/aset.
  Shared scene/PNG/PDF/native serialization tetap hanya memuat konten. Save/Open
  menyimpan posisi hasil snap/arrange sebagai field node biasa, bukan setting
  mesin atau flattened preview. History/retry/asset retention tidak dipintas.
- Tidak menambah evaluator constraints13, public export UI/jobs15–17, SDK/MCP18/19
  atau klaim performance/reference hardware23. Mesin rilis bersih/multi-monitor
  fisik tetap pending. Induk10 verified hanya sesudah10A dan10B verified.

Acuan: [Qt High DPI](https://doc.qt.io/qt-6/highdpi.html),
[QGraphicsView](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QGraphicsView.html).
Qt menyediakan scale-factor test; tes10B mengalibrasi native DPR lalu menjalankan
proses baru dengan QT_SCALE_FACTOR, tidak mengubah Windows display settings.
Bukti/versi aktual: [baseline10B](../baseline-segment10b.md).
