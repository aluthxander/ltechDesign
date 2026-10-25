# Import image segmen12

File → Import images (`Ctrl+Shift+I`) menerima PNG/JPEG/WebP/SVG. Drag file lokal
ke canvas memakai alur staged yang sama dan selalu Copy; URL remote ditolak.
Impor multi-file atomik maksimum32file. Posisi dialog adalah pusat viewport;
drop memakai koordinat drop dalam parent frame/artboard yang ter-hit. Ukuran
awal mempertahankan aspect, maksimum640×480 logical px; Inspector dapat
mengubah geometry setelahnya. Kontainer rotated parent tetap parent-local.

Inspector menampilkan thumbnails semua image asset embedded dan dimensinya.
Scroll daftar, double click untuk menempatkan ulang aset yang sudah embedded.
Image mode menyediakan fit/fill/stretch, semua centered. Crop x/y/width/height
memakai source normalized0..1; Apply crop memvalidasi seluruh rectangle,
Reset crop kembali0,0,1,1. Crop memilih sumber sebelum fit; original bytes tetap.
Radius/opacity/rotation memakai kontrol Inspector existing (scroll ke bawah).
Replace image membuka file dialog, boleh raster↔SVG; container ID/hierarchy/
geometry/style/crop/fit tetap. Import/crop/replace/placement dapat di-undo/redo.

Save/Open/Import Project menyimpan byte sumber embedded dalam ZIP.ltechdesign1.0.
File asal boleh dipindah/dihapus; thumbnail bukan sumber restore. Tidak menyimpan
absolute path untuk mengembalikan image. PNG/JPEG/WebP diidentifikasi dari content,
bukan extension; EXIF orientation diterapkan pada tampilan/crop, byte tidak diubah.
Animasi/APNG ditolak; tidak diam-diam mengambil first frame. Malformed/truncated,
50MiB+, header40MP+, actual buffer terlalu besar atau decoder unavailable memberi
error dan tidak mengubah dokumen. Import progress/cancel ada di Inspector.
Cancel saat native codec sedang bekerja selesai sesudah codec kembali, sebelum
commit. Satu job aktif; document/page/revision yang berubah membuat hasil stale
ditolak. Pending save/open tetap memakai lifecycle existing.

SVG dipertahankan sebagai aset vektor. Subset UTF-8 (BOM/deklarasi XML1.0 opsional):

- Elemen: svg root, g, rect, circle, ellipse, line, polyline, polygon, path, title,
  desc. Nested svg, defs/use, image, text/font, CSS/style/class, gradient, filter,
  mask/clipPath, animation dan foreignObject belum didukung dan ditolak.
- Atribut: id; x/y/x1/y1/x2/y2; width/height; rx/ry/r/cx/cy; d/points; viewBox;
  preserveAspectRatio; transform; fill/stroke/stroke-width; opacity/fill-opacity/
  stroke-opacity (numeric0..1); fill-rule; stroke-linecap/linejoin/miterlimit.
  `opacity` root svg/g hanya1: group alpha internal belum didukung agar tidak
  mengubah composite atau membuat raster buffer tersembunyi di QtSvg6.10.
  Opacity node/group ltechDesign tetap tersedia melalui shared isolation. Tidak ada
  script/event/href/xml:base, DTD/entities, processing instruction selain deklarasi
  XML, atau external reference/`url(...)`/data URI. Unknown attribute ditolak.
- Width/height adalah angka atau px; viewport positif. Aspect root default
  xMidYMid meet, xMidYMid atau none; alignment/slice lainnya ditolak. Geometry
  transform/path memakai parser Qt untuk subset statis; tidak dijanjikan round-trip
  SVG universal atau node/path individual editable. Nilai nonfinite/extreme,
  complexity/depth/bytes/viewport/recording di luar limit ditolak.

Tidak ada sanitasi yang membuang konten lalu menyebutnya berhasil. Error menyebut
unsafe_svg/svg_subset/invalid_svg atau limit yang terkait; perbaiki sumber menjadi
subset di atas lalu impor ulang. Renderer tidak melakukan fetch jaringan/file SVG.
Output PDF mempertahankan vector untuk SVG opaque; opacity/shadow tertentu memakai
raster isolation yang sudah dilaporkan shared renderer, native save tetap SVG asli.

Cache prepared live+history maksimum256MiB per tab, byte store512MiB. Raster decoded
ceiling40MP/160MB; angka tersebut maksimum aman, bukan janji semua format bit-depth
atau setiap image dekat batas dapat dibuka dalam anggaran tersisa. Kontrak rinci di
[ADR0024](adr/0024-portable-media-import.md). Clipboard image lintas aplikasi belum
dikerjakan (38A); clipboard node internal existing tidak dihitung sebagai fitur itu.
