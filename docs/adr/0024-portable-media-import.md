# 0024 — Portable media dan staged import

Status: accepted, segmen12, 25 Oktober 2026. Native/container schema tetap1.0,
dependency tetap Python3.12.12/PySide6Qt6.10.2/Pillow12.3.0 yang benar-benar diuji.

`SetMedia(node_id, data)` adalah command domain tanpa Qt untuk fit/crop/replace.
Dispatcher menentukan discriminator image/svg dari asset registry tervalidasi,
mempertahankan ID, parent, urutan, ukuran, pivot, scale, rotation, opacity dan
style. RegisterAsset+Create/SetMedia dipublikasikan satu transaksi/revision/undo.
Crop normalized memilih source rectangle dahulu, lalu centered fit/fill/stretch
ke geometry lokal; path radius existing selalu membatasi hasil. File sumber hanya
input. Byte asli/hash tersimpan embedded; QImage/QPicture/thumbnail hanya runtime.

Raster di-decode dengan QImageReader (content sniff, EXIF orientation, header dan
actual guard), maksimum50MiB/40MP, buffer actual maksimum160juta byte per image.
Qt allocation ceiling256MiB memberi ruang RGBA40MP; cache prepared per tab
(termasuk undo/redo) dibatasi256MiB dan anggaran sisa dicek sebelum raster decode.
SVG maksimum4MiB,64level/10.000elemen/100.000numeric operands, numeric magnitude
10juta dan recording16MiB; viewport sumber juga≤40MP. Batas operasional tambahan
boleh menolak dokumen sangat berat dengan error, tidak mengubah/meraster asetnya.
Impor32file/batch; satu worker dan satu active import per window, tanpa antrean
tak terbatas. BlobStore tetap512MiB per sesi. Validation/decode di luar mutex store
agar pin/GC di GUI tidak menunggu codec. Validasi store dapat melakukan decode
kedua sementara; angka cache bukan klaim total RSS proses.

Worker membaca chunk≤1MiB, memvalidasi/decode, merekam SVG statis menjadi QPicture
vektor dan menyiapkan thumbnail. GUI menerima immutable prepared sources, bukan
QPixmap/QObject worker. Canvas/PNG/PDF memutar drawing yang sama; playback DPI
QPicture dinormalisasi terhadap target agar PDF192dpi tidak memberi scale ganda.
QPicture dibuat sendiri dari SVG tervalidasi, tidak dibaca sebagai format impor
atau serialized native. SVG opaque tetap vector PDF, opacity/shadow memakai
isolation/fallback renderer existing dan dilaporkan.

SVG opacity root/g selain1 ditolak: spike Qt6.10.2 menunjukkan dua primitive
overlap root alpha0.5 menghasilkanalpha191 (composite per primitive), sedangkan
group internal dapat memakai raster buffer tersembunyi. Subset ini membatasi
container SVG alpha, tidak mengubah byte/hasil diam-diam. Leaf opacity dan
fill/stroke-opacity numeric0..1 diterima; opacity node/group dokumen tetap memakai
shared isolation dan diuji dengan overlapping raster+SVG.

Import job menyimpan job/session/document/source_revision, progress, structured
error/result dan queued/running/succeeded/failed/cancelled. GUI menyediakan cancel
dan local status adapter; MCP tools/public generic scheduler tetap17/18C.
Cancel dicek saat membaca, di antara codec/staging dan sebelum publication;
Qt decode/record tunggal tidak dapat dipreempt, tetapi tidak berjalan di GUI.
Setelah commit, cancel tidak mengubah sukses. Revision/page/session stale,
read-only, file kedua invalid atau resource budget gagal membuang seluruh staging.
Snapshot byte lease bertahan sampai cleanup; terminal ledger32 record hanya
metadata, tidak menahan tab/decoded source. Close window meminta cancel lalu
menunggu completion secara event-driven. Tidak ada retry exactly-once lintas crash.

Registry aset tidak dipangkas sebagai efek Save/Replace. GC menahan live registry,
undo/redo dan independent snapshot/recovery/job leases. Decoded runtime sources
dipangkas setelah tidak dirujuk live/history. Disk recovery lintas restart tetap14;
tes12 membuktikan real bytes saat replace/remove/delete/GC/undo/redo dan lease.
Clipboard image dari aplikasi lain tetap P1 di38A.

Subset/rejection policy ada di [image-import.md](../image-import.md). Referensi
resmi: [QImageReader](https://doc.qt.io/qt-6/qimagereader.html),
[QSvgRenderer](https://doc.qt.io/qtforpython-6.10/PySide6/QtSvg/QSvgRenderer.html),
[QPicture/DPI](https://doc.qt.io/qt-6.10/qpicture.html). Tidak memakai contoh versi
PRD untuk menentukan dependency dan tidak menambah library/layanan AI.
