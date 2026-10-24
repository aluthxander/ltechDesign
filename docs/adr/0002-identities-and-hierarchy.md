# ADR 0002 — ID stabil dan hierarchy eksplisit

Status: accepted (desain). Tanggal: 21 Oktober 2026.

Konteks: salinan file boleh memiliki document ID sama, sementara routing, undo dan revision harus terpisah.

Keputusan: ID baru UUID4, tipe ID berbeda menurut peran; document/page/node/token/asset/font ID persisten, session/server/job ID runtime. Admission baru memberi session ID baru dan revision awal 0. File revision checkpoint bila diwajibkan format bukan counter sesi. Registry node + parent_id + children + root_ids harus konsisten; children/root order adalah z-order. Loader menolak relasi rusak/cycle/duplikat. Artboard P0 root, frame/group container, leaf tanpa children.

Alasan: tidak memakai nama/path/index sebagai identitas dan tidak memakai document ID sebagai routing runtime.

Konsekuensi: duplicate subtree/remap referensi; Duplicate Project remap semua ID isi dan document ID, Save As mempertahankannya. ID sah pada file asal dipreservasi. ADR 0010 menetapkan encoding/registry dan checkpoint manifest.saved_revision; tidak ada session/revision runtime pada document.json. Bukti implementasi: 02/03 invariants, 04 round-trip, 05/19B AT-26. Detail: architecture bagian 4.
