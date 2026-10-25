# 0025 — Deterministic stack dan parent constraints

Status: accepted, segmen 13, 26 Oktober 2026 (Asia/Jakarta).

Memakai `Node.layout`, `Node.constraints`, `Layout` dan `Constraints` yang sudah
ada; native file/document schema tetap 1.0. `layout.stack/1` kini supported pada
Project boundary. Constraints memakai kontrak core existing, tanpa capability
baru. Tidak mengubah PRD, format native, dependency atau ID.

`domain/layout.py` bebas Qt/scene/font/filesystem dan mengembalikan node hasil
evaluasi. Ukuran memiliki dependency graph per sumbu; DFS menolak siklus sebelum
publikasi. Remaining-space main axis dibagi bersama agar sibling fill tidak
membentuk ketergantungan palsu satu sama lain. Stored children order menentukan
urutan stack dan paint. Hidden/locked children tetap mengambil ruang. Ukuran
dihitung sebelum posisi; tidak mengiterasi scene bounds atau mencari fixed point.

Dispatcher: apply seluruh operasi ke Draft, validasi, ukur intrinsic text melalui
port existing, evaluasi ukuran/posisi (ukur ulang auto-height setelah alokasi
width), normalisasi group ancestor, validasi aggregate/token bindings, kemudian
publish sekali. Satu revision/event/history mencakup seluruh perubahan turunan.
Undo/redo memulihkan snapshot final tanpa mengukur font lagi. Port tambahan
`text_measure(Project, Node) -> Node` memakai shared QTextLayout existing, bukan
scene. Domain-only dispatcher menolak auto text yang memerlukan metrics tanpa
port; tidak mengarang ukuran. Canvas/PNG/PDF membaca geometry/materialized text
yang sama. Save/Open/Import Project membawa layout, constraints dan geometry
editable; runtime/session state tidak ditambahkan ke file.

## Subset MVP dan resolusi

- Stack hanya frame/artboard. Horizontal/vertical; padding top/right/bottom/left
  finite nonnegative; gap finite nonnegative. Main start/center/end; cross
  start/center/end/stretch. Stretch cross berarti alokasi fill pada sumbu itu.
- `Layout.sizing_x/y` menentukan sizing frame stack sendiri. Jika juga mempunyai
  Constraints, sizing Constraints harus fixed; anchor tetap untuk parent bebas.
  Pada node tanpa stack, `Constraints.sizing_x/y` menentukan sizing. Tidak ada
  dua sumber sizing yang bertentangan. Default fixed menggunakan geometry yang
  tersimpan; auto text existing tetap memiliki intrinsic auto-width/auto-height.
- Hug stack: sum(main dimensions + gaps) atau max(cross dimensions), ditambah
  padding. Empty hug minimal 0,01 px. Hug leaf hanya text dengan auto-width untuk
  X, auto-width/auto-height untuk Y. Intrinsic shapes/nonstack frame tidak diterka.
- Fill di stack: main membagi sisa setelah padding, gaps dan non-fill children
  sama rata; cross memakai seluruh inner extent. Fixed children tidak menyusut.
  Jika ruang kurang, fill minimal 0,01 px, start alignment pada sumbu meluap,
  overflow dipertahankan dan hanya terpotong oleh `clip_content` existing.
  Tidak ada wrap, shrink-to-fit, min/max, flex weights atau automatic clipping.
- Parent bebas frame/artboard: start mempertahankan leading offset; end menambah
  delta ukuran parent; center menambah setengah delta; stretch mempertahankan
  kedua margin dengan menambah delta pada ukuran (minimal 0,01 px). Fill pada
  parent bebas memakai aturan preserve-two-margins yang sama dengan stretch.
  Baseline adalah before snapshot parent dalam transaksi; child baru/reparent
  memakai ukuran parent pada planned snapshot. Nested changes dipropagasikan.
  Anchor Constraints tidak mengatur posisi dalam stack, yang memakai align parent.
- Siklus hug/fill (termasuk cross stretch dan wrapped-text height->width), root
  fill, hug+stretch satu sumbu, fill+auto-width, fill-height+auto-height ditolak
  atomik dengan alasan terstruktur. Bukan retry/fixed-point resolution.
- Anak langsung stack/anak ber-Constraints harus rotation=0 modulo360 dan scale=1;
  parent luar boleh transformed. Group managed belum didukung; line/polygon fixed
  boleh ikut stack, tetapi intrinsic hug/fill/stretch-nya ditolak. Bounds/stroke/
  shadow tidak menjadi input ukuran layout. Transform/geometry tidak diaproksimasi.
- Ukuran hug/fill/stretch adalah derived: semantic resize/Inspector size menolak
  edit sumbu itu, dan Inspector menonaktifkan field ukuran. Pilih fixed terlebih
  dahulu; perubahan ukuran parent fixed tetap didukung dengan anchor existing.
  Stack memulihkan posisi child setelah edit posisi; operasi reparent ke stack
  dengan preserve-appearance ditolak eksplisit karena placement akan berubah.
  Pengguna dapat menonaktifkan preserve-appearance untuk memasukkan anak lewat
  Layers. Reparent tetap menghitung transform dunia existing sebelum evaluasi.
- Inspector layout untuk satu selection, Apply atomik berisi SetLayout dan
  SetConstraints dengan expected_revision. Multi-selection belum didukung.

Advanced layout segmen 28: min/max, wrap, transform managed, group intrinsic,
weighted allocation/shrink, lebih banyak constraint combinations dan UI lanjutan.
MCP tool apply_auto_layout tetap 18/28; evaluator/commands lokal sudah shared.
Physical release/DPI/assistive technology tetap acceptance 22/24, performance 23.
