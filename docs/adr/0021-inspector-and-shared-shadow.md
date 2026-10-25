# ADR 0021 — Inspector properties, history grouping dan shared shadow

Accepted, 25 Oktober 2026 (Asia/Jakarta); pemilik 10A. PRD 20.2/20.3,
format native 1.0 tetap. Tidak menambah snapping, constraints atau public export UI.

- `SetProperties`: satu property pada explicit selection, maksimum 10.000 target,
  satu validasi aggregate/commit/revision/event. Pure `domain.inspector` dipakai
  planner dan validasi awal GUI. Field sesuai tipe; command tetap memvalidasi.
  Binding token yang bertentangan ditolak, bukan dilepas diam-diam.
- X/Y persis translasi relatif parent, bukan minimum AABB dunia. Width/height
  shape/frame merupakan geometry lokal. Resize memakai helper08 dengan anchor
  local (0,0), pivot baru dan kompensasi translasi sebagai satu transaksi. Anak
  default fixed tidak diskalakan. Frame dengan layout/constraints memerlukan
  evaluator13. Group menampilkan extent geometry × uniform scale; edit satu
  dimensi mengubah scale positif dan dimensi lainnya proporsional, bukan isi anak.
  Sumbu nol line dipertahankan; mengubahnya menjadi nonnol ditolak eksplisit.
- Radius all-corners mempertahankan authored value; path bersama melakukan clamp
  proporsional untuk fill/clip. Existing radius berbeda pada empat sudut menjadi
  Mixed sampai diganti eksplisit. Stroke tetap center-aligned dengan cap/join06.
  Qt stroker menghitung local bounds sesuai square-cap/miter-limit2; domain bounds
  memakai line cap corners, transformed rectangle padding dan konservatif polygon
  miter agar stroke tebal tidak terpotong pada isolation/selection export.
- Mixed berbeda dari `none`/unsupported. Commit menolak NaN/infinity, rentang
  salah/input kosong; warna #RRGGBB/#RRGGBBAA dinormalisasi RGBA. `none` menghapus
  paint/background. Color picker alpha: Cancel tanpa commit. Shadow fields
  mengedit efek pertama dan mempertahankan lainnya; `shadow_enabled=0` secara
  eksplisit mengosongkan stack, dapat di-undo.
- Palette foreground/background adalah state sesi aplikasi, tidak masuk revision,
  history/file. Foreground menjadi fill shape/frame dan stroke line baru;
  background menjadi background frame/artboard baru. Field Frame background
  merupakan konten melalui dispatcher/native codec. Konten baru menyimpan warna
  materialized; restore tidak bergantung pada palette sesi.
- `Request.history_group` optional GUI lokal, discope bersama client ID. Hanya
  commit berturutan dengan group sama digabung; setiap commit tetap mempunyai
  revision/event/receipt sendiri. Typing satu commit; Up/Down selama edit dan
  satu drag slider merupakan satu Undo. Enter, focus/selection/revision/tab,
  history action, command/client lain serta snapshot/completion Save memutus
  penggabungan. Undo memakai before pertama/after terakhir; asset roots/budget
  dihitung ulang. Dedup tetap mendahului revision check; bukan crash exactly-once.
  Kontrak internal; schema publik MCP tetap18A.
- Focus/picker memegang selection/session/revision asal. Perubahan dispatcher luar
  membatalkan input lama, termasuk selama dialog nested event loop. Sync publication
  sendiri mempertahankan group edit, tanpa mutasi rekursif.
- Shadow mengambil alpha shared subtree body sebelum opacity node: fill,
  background, centered stroke, teks/resources yang tersedia dan child clip.
  Spread berupa max morphology persegi pada grid target: native image passes
  O(log radius), zero padding dan interpolasi subpixel. Blur Gaussian sigma
  logical px × target scale, buffer konservatif3 sigma. Offset dipetakan transform
  node. Tint shadow lalu source dilapis sekali; opacity node diterapkan sekali
  pada seluruh komposit. Ancestor clip tetap pada painter akhir. Multiple shadow
  bounds adalah union dari source sama, bukan ekspansi shadow sebelumnya.
- Pillow12.3.0 dependency filter lokal, tanpa network/login runtime. Buffer
  device-aligned06A dengan accounting enam buffer dalam budget64 juta pixel;
  input ekstrem gagal terstruktur sebelum alokasi. PDF melaporkan node shadow
  sebagai rasterized. Perbandingan PDF10A memakai sampling2× sama dengan
  QPdfWriter06A; downsampling1× dapat mengubah coverage antialias. Throughput besar
  tetap23, jobs berat tetap15–17, tanpa klaim benchmark baru.

Acuan API: [QColorDialog](https://doc.qt.io/qt-6/qcolordialog.html),
[Pillow ImageFilter](https://pillow.readthedocs.io/en/stable/reference/ImageFilter.html),
[ImageChops](https://pillow.readthedocs.io/en/stable/reference/ImageChops.html).
Versi dan bukti aktual di [baseline10A](../baseline-segment10a.md).
