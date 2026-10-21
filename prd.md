# Product Requirements Document (PRD)

## Local Desktop Design Studio — Alternatif Figma & Paper.design berbasis Python

Python + PySide6

Windows Desktop

MCP Server

AI-Ready

Nama proyek: ltechDesign Studio. Versi PRD: 1.2. Tanggal revisi: 21 Oktober 2026. Target platform: Windows 10/11, dengan arsitektur yang memungkinkan dukungan Linux dan macOS. Model aplikasi: Desktop lokal untuk satu pengguna, offline-first, tanpa kolaborasi, login atau cloud wajib. Integrasi AI: Codex, ChatGPT, dan MCP-compatible AI clients.

Revisi 1.1 menerapkan hasil `review_prd_dan_prompt.md`: kontrak pada bagian 20, FR-027–FR-033, dan AT-21–AT-30 melengkapi requirement sebelumnya. Perubahan dokumen ini belum berarti fitur sudah diimplementasikan. Versi PRD terpisah dari versi schema file proyek.

Revisi 1.2 menetapkan `.ltechdesign` sebagai format proyek lokal portabel, menggantikan nama format rencana `.pydesign`. Spesifikasi file berada di `docs/ltechdesign-file-format.md`; restore penuh diuji melalui AT-31–AT-34. Format dan contoh file disediakan sebelum implementasi aplikasi, sehingga pemulihan melalui UI masih harus dibuktikan pada segmen implementasi.

### 1. Ringkasan Eksekutif

ltechDesign Studio adalah aplikasi desain desktop berbasis Python yang menggabungkan kemampuan desain antarmuka web seperti Figma dan Paper.design dengan fitur desain grafis seperti editor poster, banner, infografis, dan konten media sosial.

Aplikasi memiliki visual canvas, layer management, vector drawing, typography, reusable components, serta sistem ekspor berbagai format.

Keunggulan utamanya adalah integrasi Model Context Protocol (MCP) Server, yang memungkinkan AI membaca struktur proyek, membuat desain, mengatur posisi elemen, mengubah styling, dan mengekspor hasil melalui perintah bahasa alami.

Contoh perintah melalui Codex:

> Buat desain landing page website Program Studi Pendidikan Profesi Apoteker UNISSULA yang modern, menggunakan hijau #006633, aksen #A41C66, font Inter, terdiri dari navbar, hero, daftar keunggulan, profil dosen, dan CTA pendaftaran.

AI akan menggunakan MCP Server untuk membuat objek desain di aplikasi lokal. Pengguna dapat melihat, mengedit, menyimpan, atau mengekspornya melalui antarmuka visual.

### 2. Tujuan Produk

| ID   | Tujuan              | Hasil yang diharapkan                                                    |
| ---- | ------------------- | ------------------------------------------------------------------------ |
| G-01 | Desain UI/UX        | Membuat mockup halaman web desktop dan mobile                            |
| G-02 | Desain grafis       | Membuat poster, banner, infografis, dan konten sosial media              |
| G-03 | Local-first         | Seluruh file dan proyek tersimpan di komputer pengguna                   |
| G-04 | AI integration      | Codex dapat membaca, membuat, dan mengedit desain melalui MCP            |
| G-05 | Multi-format export | PDF, PNG, JPG/JPEG, dan WebP                                             |
| G-06 | Editable document   | Proyek dapat disimpan dan dibuka kembali tanpa kehilangan struktur layer |
| G-07 | Developer handoff   | Menyediakan struktur desain yang bisa dikonversi menjadi HTML/CSS        |
| G-08 | Extensibility       | Arsitektur modular untuk menambahkan fitur pada masa mendatang           |

### 3. Referensi Konsep Antarmuka

[Change the background color of the canvas – Figma Learn - Help Center](https://images.openai.com/static-rsc-4/DxEmn4zzZ0JnFJCmzqfHndcROKjRW5D-8bxt3Oeay78U3cuvaGTLJP9cbruMYyixmeHDkRtGg-XJRGwM5zBkv2lDdp3MUATFMnEuh-Iuzblc0aOUYCnZ_aT_1nTndQ_POHauBhVImRj-G1WLbRvusKr_EQ-6TpoThtgtJS-ZvNU?purpose=inline)

Referensi: Figma

Canvas, layer tree, component, frame, inspector, dan design properties.

[MCP • Paper](https://images.openai.com/static-rsc-4/h4J3A5Ls80I2Bf_CKmv9zx3CVMI_bxPsdSkpTSuGEFhDgSi5FUlSv8CLBk2AZr4iJddbTbz32PkqoaeA9BW2t5AR7AoUSWwmQypjNrDum4X_o6NwfWJLIxee4uU3-sT1i_iheBAjm_9LyiATJGSGrHQXZ_dR480g80kdh95V-fw?purpose=inline)

Referensi: Paper.design

Workflow desain web berbasis visual dengan dukungan AI.

Target produk bukan menyalin antarmuka atau implementasi proprietary Figma/Paper.design, melainkan mengadopsi prinsip workflow yang relevan dan mengembangkan editor dengan identitas, implementasi, serta format proyek sendiri.

### 4. Ruang Lingkup Produk

Produk dibagi menjadi tiga kategori:

- UI Design Editor: Membuat wireframe, halaman web, antarmuka mobile, dashboard, komponen, dan prototipe visual.
- Graphic Design Editor: Membuat desain publikasi digital dan cetak dengan teks, shape, gambar, efek, serta pengaturan layout.
- AI Design Automation: Membaca dan memodifikasi dokumen desain melalui AI menggunakan MCP Server.

Aplikasi ditujukan untuk satu pengguna di komputer lokal. Tidak ada kolaborasi multiuser, edit bersama, presence/cursor pengguna lain, komentar tim, sharing workspace, sinkronisasi cloud atau akun organisasi dalam roadmap ini. Pemindahan proyek dilakukan melalui file `.ltechdesign` secara manual. GUI dan MCP adalah dua jalur kendali lokal milik pengguna yang sama; proteksi penulisan antarproses tidak merupakan fitur kolaborasi.

Aplikasi bukan pengganti penuh Photoshop, Illustrator, atau Figma dalam versi awal. Pengeditan foto kompleks dan kompatibilitas penuh file `.fig` tidak termasuk cakupan awal. Integrasi AI opsional tidak menjadi dependensi untuk menyimpan, membuka atau mengedit proyek.

# PRD Teknis — ltechDesign Studio

**Versi:** 1.2\
**Jenis dokumen:** Product Requirements Document\
**Prioritas:** Desktop lokal Windows, Python, AI-native design workflow\
**Status:** Spesifikasi pengembangan setelah review, implementasi belum dimulai

## 5. Kebutuhan Fungsional

### 5.1 Sistem Proyek dan Dokumen

**FR-001 — Project Management (P0)**

Aplikasi wajib menyediakan pengelolaan proyek dengan kemampuan:

- New Project, Open Project, Save, Save As, dan Close.
- Membuka beberapa dokumen melalui tab.
- Recent Projects.
- Autosave dengan interval yang dapat dikonfigurasi.
- Recovery saat aplikasi tertutup tidak normal.
- Menyimpan beberapa page dan artboard dalam satu proyek.
- Membuat duplikat proyek.
- Mempertahankan seluruh layer dan aset saat proyek dibuka kembali.

**FR-002 — Native File Format (P0)**

Format proyek utama menggunakan **`.ltechdesign`**, dengan identitas format `ltechdesign.project` dan versi container awal `1.0`. Format bersifat lokal, portabel dan dapat diedit kembali; bukan PNG/PDF yang sudah di-flatten. Spesifikasi normatif: `docs/ltechdesign-file-format.md`.

File ini berupa container ZIP yang berisi:

- `manifest.json`: metadata, versi format, ID proyek.
- `document.json`: struktur page, artboard, node, style, dan relasi.
- `assets/index.json`: ID, path relatif, media type, ukuran dan SHA-256 aset; byte aset berada di `assets/data/`.
- `tokens.json`: token store termasuk nilai/binding yang digunakan dokumen.
- `fonts.json`: daftar font dan resolusi/fallback; byte font yang disertakan menggunakan asset store.
- `workspace.json`: state tampilan opsional, seperti page aktif/zoom/pan; bukan identitas sesi atau state koneksi.
- `thumbnails/`: preview proyek opsional, bukan sumber data desain.
- `extensions/`: payload fitur lanjutan yang dideklarasikan; unsupported required capability menolak edit yang berisiko kehilangan data.

Struktur dokumen internal menggunakan JSON bertipe, bukan serialisasi langsung objek Qt. Hal ini memungkinkan proyek dibaca dan dimanipulasi oleh MCP tanpa membuka antarmuka aplikasi.

**Acceptance criteria:** Save/Open atau Save/Import Project mengembalikan seluruh desain editable yang didukung, termasuk page/artboard, ID/urutan layer, transform, text, style, layout, tokens dan byte aset. Proyek tidak memerlukan file asal, database/settings mesin sebelumnya, login atau internet. Font hilang dilaporkan tanpa mengganti metadata asli diam-diam. Undo history, job, lock dan session ID tidak menjadi bagian kontrak file portabel. Validasi dan staging selesai sebelum tab aktif diganti; file gagal tidak merusak pekerjaan terbuka.

### 5.2 Canvas Editor

**FR-003 — Infinite Workspace (P0)**

Aplikasi mempunyai area kerja visual dengan:

- Canvas luas yang mendukung panning dan zoom.
- Zoom melalui Ctrl + mouse wheel atau kontrol zoom.
- Zoom to Selection dan Fit to Artboard.
- Ruler horizontal dan vertikal.
- Grid dan snapping.
- Smart guides dan alignment.
- Multiselect dan bounding box.
- Drag, resize, rotate, duplicate, dan delete objek.
- Copy, paste, cut, undo, dan redo.
- Pengaturan foreground/background.
- Lock dan hide layer.
- Context menu berdasarkan objek terpilih.
- Nudge dengan tombol panah: 1 logical pixel, Shift + panah: 10 logical pixels; tidak aktif sebagai shortcut canvas saat mengedit teks.
- Bring Forward/Send Backward melalui menu dan shortcut yang tidak konflik, dalam urutan sibling.

**FR-004 — Artboard & Frame (P0)**

Artboard dapat memiliki ukuran preset atau custom:

| Kategori           | Preset                              |
| ------------------ | ----------------------------------- |
| Web desktop        | 1440 × 900, 1920 × 1080             |
| Tablet             | 768 × 1024                          |
| Mobile UI          | 390 × 844, 430 × 932                |
| Instagram Portrait | 1080 × 1350                         |
| Instagram Square   | 1080 × 1080                         |
| Story/Reels/TikTok | 1080 × 1920                         |
| Presentasi         | 1920 × 1080                         |
| Cetak              | A4, A3, custom dalam mm             |
| Custom             | Lebar, tinggi, unit, orientasi, DPI |

Setiap artboard mempunyai ID unik, nama, ukuran, warna latar, dan daftar node anak.

**FR-005 — Layer Tree (P0)**

Panel Layers mendukung:

- Nested layers, group, ungroup.
- Drag-and-drop untuk mengubah urutan.
- Rename dan duplicate.
- Hide/Show dan Lock/Unlock.
- Pencarian berdasarkan nama dan tipe.
- Pemilihan objek tersinkron antara canvas dan layer tree.
- Reorder layer memengaruhi z-index rendering.

### 5.3 Object Drawing System

**FR-006 — Drawing Tools (P0)**

Objek dasar yang harus tersedia:

| Objek     | Fungsi                   |
| --------- | ------------------------ |
| Rectangle | Shape, container, card   |
| Ellipse   | Circle, avatar, dekorasi |
| Line      | Garis, separator         |
| Polygon   | Objek geometris          |
| Text      | Typography               |
| Image     | Raster image             |
| SVG       | Aset vektor              |
| Group     | Pengelompokan            |
| Frame     | Layout container         |

**FR-007 — Advanced Vector Tools (P1)**

- Pen tool dan Bézier paths.
- Node/path editing.
- Boolean operations: Union, Subtract, Intersect, Exclude.
- Stroke cap, join, dash.
- Clipping masks.
- Path flattening.

**FR-008 — Properties Inspector (P0)**

Saat objek dipilih, panel kanan menampilkan properti sesuai jenis objek:

- Position X/Y.
- Width/Height.
- Rotation.
- Opacity.
- Fill dan stroke.
- Border radius.
- Shadow.
- Alignment.
- Text properties.
- Layer hierarchy.
- Constraints.
- Export settings.

Perubahan pada Inspector wajib langsung memperbarui canvas dan document model.

### 5.4 Typography System

**FR-009 — Text Editor (P0)**

Mendukung:

- Font lokal yang terinstal di Windows.
- Font family, size, weight, italic.
- Text alignment.
- Line height, letter spacing.
- Fill, opacity.
- Multiline text.
- Text box resizing.
- Auto width/height.
- Unicode.
- Emoji mengikuti kemampuan font dan text renderer.

**FR-010 — Advanced Typography (P1)**

- Rich text styling per karakter/span.
- Text styles global.
- Auto-fit text.
- Font fallback.
- Font substitution saat font tidak ditemukan.
- Text on path.
- Variabel font.

Untuk mencegah perbedaan tampilan, sistem ekspor harus menggunakan renderer teks yang konsisten dengan canvas dan memberikan peringatan jika font tidak tersedia.

### 5.5 Image Editor

**FR-011 — Image Handling (P0)**

- Import PNG, JPG/JPEG, WebP.
- Import SVG sebagai objek vektor bila didukung.
- Drag-and-drop gambar.
- Crop.
- Fit, Fill, Stretch.
- Rotation dan opacity.
- Clipping menggunakan rectangle atau rounded rectangle.
- Replace image tanpa mengubah posisi atau ukuran container.

**FR-012 — Image Adjustment (P1)**

- Brightness/Contrast.
- Saturation.
- Hue.
- Blur.
- Grayscale.
- Drop shadow.
- Masking dasar.
- Background removal melalui plugin opsional.

Semua adjustment harus non-destructive selama proyek masih dalam format native.

### 5.6 UI/UX Design Features

**FR-013 — Layout System (P0/P1)**

- Frame dan container.
- Stack horizontal/vertical.
- Padding dan gap.
- Alignment.
- Fixed size dan hug content.
- Fill available space.
- Constraints terhadap parent.
- Layout recalculation saat ukuran frame berubah.

MVP mencakup stack layout dan constraints dasar. Auto Layout yang kompleks diprioritaskan untuk tahap lanjutan.

**FR-014 — Reusable Components (P1)**

- Create Component.
- Component Instance.
- Master Component.
- Override properti instance.
- Update master dan propagasi perubahan.
- Detach Instance.
- Component Library lokal.

**FR-015 — Design System (P1)**

P0 menyediakan token store minimum dengan ID stabil, nilai bertipe, serialization dan operasi MCP baca/tulis. UI pengelolaan, binding properti, alias dan theme variables lengkap tetap P1.

- Color tokens.
- Typography tokens.
- Spacing tokens.
- Radius dan shadow tokens.
- Theme variables.
- Komponen seperti Button, Input, Card, Navbar, Sidebar, Badge, Modal, dan Table.

Desain token disimpan dengan ID stabil sehingga dapat diakses dan diubah melalui MCP Server.

**FR-016 — Prototyping (P2)**

- Interaksi click.
- Navigation antarframe.
- Hover states.
- Simple transitions.
- Preview mode.

### 5.7 Graphic Design Features

**FR-017 — Graphic Composition (P0)**

Mendukung pembuatan:

- Poster digital.
- Banner kegiatan.
- Konten Instagram/Facebook.
- Thumbnail video.
- Infografis.
- Brosur sederhana.
- Sertifikat.
- Dokumen presentasi visual.

**FR-018 — Creative Tools (P1)**

Color picker, solid fill/stroke, basic shadow dan alignment/distribution dasar termasuk P0. Daftar berikut memperluas kemampuan dasar tersebut pada P1; jangan menunda kontrol dasar editor ke P1.

- Gradient linear/radial.
- Color picker.
- Eyedropper.
- Shadow dan blur.
- Image masking.
- Blending modes dasar.
- Shape presets.
- SVG/icon library.
- Alignment/distribution.
- Templates.

**FR-019 — Print Design (P1)**

- Satuan mm, cm, dan inch.
- Konversi ukuran berdasarkan DPI.
- Bleed dan safe margin.
- Pengaturan print lanjutan untuk PDF multipage; ekspor PDF multipage dasar sudah wajib P0 melalui bagian 6.1 dan AT-10.
- Export PDF dengan teks dan vektor yang dipertahankan sejauh didukung renderer.
- Pengaturan resolusi raster.

Konversi CMYK, ICC color management, dan PDF/X tidak termasuk MVP. Dukungan percetakan profesional menjadi pengembangan lanjutan.

## 6. Export & Import

### 6.1 Export Engine (P0)

Format ekspor wajib:

| Format   | Spesifikasi                                                       |
| -------- | ----------------------------------------------------------------- |
| PNG      | Transparansi, scaling 1x/2x/3x, resolusi custom                   |
| JPG/JPEG | Quality 1–100, background solid                                   |
| WebP     | Quality dan opsi lossless jika encoder mendukung                  |
| PDF      | Single/multipage, ukuran halaman, ekspor vektor bila memungkinkan |

**FR-020 — Export Options**

Pengguna dapat memilih:

- Entire artboard, selected objects, atau seluruh artboard.
- Export scale.
- Target dimensions.
- Output DPI.
- Background transparent/solid.
- File naming pattern.
- Quality/compression.
- Output folder.
- Export progress dan error report.

JPG tidak mendukung transparansi. Sistem wajib melakukan flattening dengan background yang dipilih. PDF single/multipage dasar wajib P0; bleed, safe margin dan pengaturan print lanjutan P1.

Untuk WebP, kemampuan encoder harus diperiksa saat runtime dan fallback menggunakan Pillow apabila diperlukan.

**FR-021 — Batch Export (P1)**

Mengekspor banyak artboard dalam satu operasi, termasuk preset export dan nama file otomatis.

### 6.2 Import (P0/P1)

MVP wajib mendukung import gambar raster dan SVG yang kompatibel, serta membuka `.ltechdesign`.

**Open Project** dan **Import Project (.ltechdesign)** memakai validator/loader yang sama dan membuka file sebagai dokumen/tab lengkap; tidak memasukkannya sebagai satu gambar atau menggabungkan layer ke proyek aktif. Import Project mempertahankan identitas konten dan mengikuti ownership path sumber; pengguna dapat Save As untuk salinan lokal. Penggabungan layer ke dokumen aktif bukan bagian P0. Preview PNG/PDF tidak dapat dipakai untuk mengklaim restore editable. Pembaca memeriksa manifest/versi, bukan hanya ekstensi ZIP yang diganti nama.

Import PDF sebagai gambar/pratinjau, PDF multipage, dan konversi PDF menjadi objek editable termasuk cakupan lanjutan. Membuka file Figma native tidak menjadi persyaratan kompatibilitas MVP.

### 6.3 Export UI to Code (P1)

Menyediakan:

- Export HTML.
- Export CSS.
- Assets folder.
- Design tokens berupa CSS variables.
- Struktur semantic element sederhana.
- Responsive layout dasar berbasis Auto Layout/constraints.

Hasil ekspor HTML/CSS adalah **starting point frontend**, bukan jaminan kode production-ready. AI dapat membantu melakukan refactoring ke Bootstrap atau framework lain melalui Codex.

## 7. MCP Server & AI Integration

### 7.1 Konsep Arsitektur

ltechDesign Studio menyediakan MCP Server lokal yang dapat diakses oleh AI client yang mendukung Model Context Protocol.

Ada dua mode operasi:

1. **Attached mode:** MCP terhubung pada instance desktop yang sedang berjalan. Perubahan AI ditampilkan langsung pada canvas.
2. **Headless mode:** MCP memanipulasi file proyek tanpa menjalankan graphical editor. Rendering dan ekspor dapat dikerjakan melalui backend terpisah.

MCP adalah interface untuk tools, resources, dan prompts. Ia bukan model AI itu sendiri. Proses generasi desain dan reasoning dijalankan oleh AI client, sedangkan ltechDesign Studio mengelola dokumen dan rendering.

### 7.2 MCP Transport

**FR-022 — MCP Connectivity (P0)**

- Transport `stdio` untuk client lokal yang meluncurkan subprocess.
- Transport Streamable HTTP pada loopback `127.0.0.1` sebagai opsi.
- Start/Stop MCP Server.
- Connection status.
- Log akses dan operasi.
- Daftar tool yang tersedia.

**FR-023 — Project Inspection (P0)**

AI dapat membaca:

- Metadata proyek.
- Page dan artboard.
- Layer hierarchy.
- Node properties.
- Design tokens.
- Asset manifest.
- Selection aktif bila tersedia.
- Preview/screenshot canvas.

**FR-024 — Design Manipulation (P0)**

AI dapat melakukan:

- Create, edit, delete node.
- Create frame/artboard.
- Move/resize/rotate.
- Set fill, stroke, opacity.
- Set typography.
- Group/ungroup.
- Reorder layers.
- Import/local-link assets dengan pembatasan path.
- Save project.
- Export project.

**FR-025 — Transaction Management (P0)**

Setiap permintaan perubahan harus:

- Melakukan validasi input.
- Mengidentifikasi proyek dan versi dokumen.
- Dijalankan sebagai satu transaksi logis.
- Mengembalikan success/error terstruktur.
- Mencatat riwayat operasi.
- Dapat dibatalkan melalui Undo.

Untuk batch perubahan konten, jika terdapat kegagalan, seluruh perubahan dalam batch dibatalkan secara atomik. Pan/zoom/selection adalah state sesi, tidak masuk undo konten atau menaikkan content revision. Save/export adalah side effect di luar transaksi perubahan konten; lifecycle job, retry dan asset staging mengikuti bagian 20.3–20.5.

### 7.3 MCP Tool Registry

Daftar tool minimum:

| MCP Tool            | Fungsi                                |
| ------------------- | ------------------------------------- |
| `get_app_status`    | Status aplikasi, versi, dokumen aktif |
| `create_project`    | Membuat proyek                        |
| `open_project`      | Membuka proyek                        |
| `get_document_tree` | Membaca struktur node dengan filter, depth/fields, limit dan cursor terikat revision |
| `get_node`          | Membaca detail node                   |
| `get_selection`     | Membaca selection                     |
| `create_artboard`   | Membuat artboard                      |
| `create_node`       | Membuat objek                         |
| `update_node`       | Memperbarui properti                  |
| `delete_node`       | Menghapus objek                       |
| `batch_operations`  | Melakukan multioperasi atomik         |
| `set_text`          | Mengatur teks                         |
| `set_style`         | Mengatur tampilan                     |
| `move_node`         | Mengubah posisi/hierarchy             |
| `get_design_tokens` | Membaca token                         |
| `set_design_token`  | Mengubah token                        |
| `render_preview`    | Menghasilkan pratinjau                |
| `export_design`     | Ekspor ke PDF/PNG/JPG/WebP            |
| `save_project`      | Menyimpan perubahan                   |

Tool seperti `create_component`, `apply_auto_layout`, `export_html_css`, dan `analyze_design` menjadi prioritas P1.

`analyze_design` P1 memeriksa bounds/overflow, aset/font hilang dan token reference rusak tanpa mengubah dokumen. Audit aksesibilitas desain yang lebih luas tetap P2; aksesibilitas UI aplikasi sendiri adalah kebutuhan dasar P0 dan audit P1.

Kontrak P0 juga wajib menyediakan operasi berikut. Gunakan nama tool ini agar discovery jelas; group/ungroup/reorder/page mutations juga tersedia sebagai operasi batch bertipe yang memakai dispatcher yang sama.

| MCP Tool | Fungsi dan batas |
| --- | --- |
| `list_documents`, `get_document_info` | Identitas sesi terbuka, document ID persisten, revision, mode dan read-only status |
| `create_page`, `update_page`, `delete_page` | Pengelolaan page dengan undo; pemindahan/penghapusan isi harus eksplisit |
| `import_asset`, `list_assets` | Import tervalidasi ke asset store dan pembacaan metadata; path dibatasi |
| `group_nodes`, `ungroup_nodes`, `reorder_nodes` | Menjaga hierarchy, urutan sibling dan transform visual |
| `set_selection` | State sesi attached; headless mengembalikan `selection_unavailable` kecuali sesi selection eksplisit didukung |

Pencarian nama/tipe/subtree dilakukan melalui filter `get_document_tree`, sehingga `find_nodes` terpisah tidak wajib. Semua tool yang menargetkan dokumen menggunakan `session_id`; mutasi konten menyertakan `expected_revision` dan `request_id`. Shape input/output, batch operation union, error codes dan examples harus ditulis serta diuji sebelum tool dinyatakan selesai.

### 7.4 MCP Resources

| Resource                    | Konten           |
| --------------------------- | ---------------- |
| `pydesign://project/active` | Proyek aktif     |
| `pydesign://document/tree`  | Struktur dokumen |
| `pydesign://tokens`         | Design tokens    |
| `pydesign://selection`      | Objek terpilih   |
| `pydesign://artboards`      | Daftar artboard  |

Resource menggunakan format terstruktur yang dapat dipahami AI dan mencantumkan revision number.

URI `active` adalah alias konteks UI. Respons menyertakan `session_id`, `document_id` dan `revision`; pembacaan/perubahan konsisten memakai sesi eksplisit. Sediakan resource template `pydesign://sessions/{session_id}/...` untuk tree, tokens, selection dan artboards. Pagination daftar resource tidak menggantikan pagination isi tree; batas query dan preview mengikuti bagian 20.4. Invalidation berbasis revision wajib P0; notifikasi/subscription opsional hanya jika didukung versi protokol dan client yang diuji.

### 7.5 AI Workflow

**Skenario A: Create from Prompt**

1. Pengguna memberikan instruksi kepada Codex.
2. Codex membaca spesifikasi tool MCP.
3. Codex meminta pembuatan proyek dan artboard.
4. Codex membuat objek berdasarkan layout dan design tokens.
5. Engine memvalidasi serta memperbarui document model.
6. Canvas memperlihatkan desain.
7. Pengguna dapat melakukan revisi manual.
8. Codex menerima revisi berikutnya dan mengedit node yang relevan.

**Skenario B: Edit Existing Design**

1. Pengguna memilih frame atau objek.
2. AI membaca dokumen/selection.
3. AI mengajukan perubahan properties.
4. Engine menerapkan transaksi.
5. Pengguna meninjau perubahan visual.
6. Undo tersedia jika hasil tidak sesuai.

**Skenario C: Generate Design and Export**

Perintah:

> Buat poster ukuran 1080 × 1350 tentang penerimaan mahasiswa baru PSPPA, lalu ekspor ke PNG kualitas tinggi dan PDF.

AI memanggil tool desain, meminta preview untuk memeriksa hasil, lalu menggunakan `export_design` menghasilkan file lokal.

### 7.6 MCP Security

**FR-026 — Security Controls (P0)**

- Bind HTTP hanya ke loopback secara default.
- Autentikasi/token untuk endpoint lokal HTTP.
- Validasi `Origin` dan `Host`.
- Path allowlist dan canonical-path validation.
- Tidak menyediakan shell execution arbitrer.
- Tidak menyediakan akses database arbitrer.
- Pembatasan ukuran payload dan aset.
- Confirmation untuk operasi destruktif atau akses di luar direktori kerja yang diizinkan.
- Audit log.
- MCP dapat dinonaktifkan.

AI client tidak otomatis memperoleh akses tak terbatas ke filesystem lokal.

**Batasan konektivitas ChatGPT:** Kompatibilitas langsung dengan ChatGPT bergantung pada kemampuan MCP/client, paket, dan lingkungan yang digunakan. Desktop MCP pada Codex dapat menjadi target awal. Akses dari ChatGPT berbasis cloud ke MCP pada localhost memerlukan mekanisme yang didukung secara resmi atau perantara yang aman; localhost tidak dapat diasumsikan langsung dapat dijangkau dari cloud.

## 8. Software Architecture

### 8.1 Technology Stack

| Lapisan           | Teknologi                      | Status                            |
| ----------------- | ------------------------------ | --------------------------------- |
| Bahasa            | Python 3.12+                   | Utama                             |
| Desktop GUI       | PySide6 / Qt 6                 | Utama                             |
| Canvas            | QGraphicsScene + QGraphicsView | MVP                               |
| Vector rendering  | QPainter, QPainterPath         | Utama                             |
| Document Model    | Python dataclasses / Pydantic  | Utama                             |
| File format       | JSON + ZIP                     | Utama                             |
| Raster processing | Pillow                         | Utama                             |
| PDF               | Qt PDF writer/painting         | Utama                             |
| MCP Server        | Official MCP Python SDK        | Utama                             |
| HTTP service      | MCP SDK transport              | Opsional                          |
| Internal storage  | SQLite                         | Cache, history metadata, settings |
| Tests             | pytest + pytest-qt             | Utama                             |
| Packaging         | PyInstaller atau Nuitka        | Windows distribution              |

Pemilihan Qt sangat sesuai untuk MVP karena menyediakan framework desktop, graphics scene, input event, drawing, text, dan export primitives.

Untuk optimisasi di kemudian hari, rendering layer dapat dimigrasikan secara parsial ke sistem grafis yang lebih canggih tanpa mengganti document model.

### 8.2 Architectural Pattern

Menggunakan **Document Model + Command Pattern + Rendering Adapter**.

Pembagian modul:

- **Domain Model:** Objek desain dan aturan dokumen.
- **Command Engine:** Semua perubahan node dilakukan melalui command terstruktur.
- **Rendering Engine:** Mengubah state dokumen menjadi canvas visual.
- **Desktop UI:** Menangani user interactions.
- **Export Engine:** Menghasilkan PDF dan raster.
- **MCP Adapter:** Menerjemahkan AI tool calls menjadi command.
- **Persistence Layer:** Save/load/autosave.
- **Asset Manager:** Penyimpanan media dan manajemen referensi.
- **Undo/Redo History:** Riwayat command.
- **Event Bus:** Sinkronisasi perubahan model, canvas, dan MCP.

GUI tidak menjadi sumber utama data. **Document Model merupakan single source of truth.**

### 8.3 Synchronization & Thread Safety

Semua perubahan dokumen harus melewati satu command dispatcher.

Jika MCP Server berjalan pada thread/proses berbeda:

- Permintaan divalidasi.
- Command ditempatkan dalam queue.
- Document engine menerapkannya secara serial.
- Revision number diperbarui.
- Event dikirim ke canvas.
- Respons MCP dikembalikan setelah transaksi selesai.

Qt GUI state hanya boleh dimanipulasi dari GUI thread. MCP tidak boleh mengubah objek QGraphicsScene secara langsung dari worker thread.

Document revision digunakan sebagai optimistic concurrency check untuk mencegah perubahan AI menimpa edit manual yang lebih baru.

Revision tidak menggantikan lock file antarproses. Kepemilikan file, identitas sesi dan penanganan perubahan eksternal mengikuti bagian 20.1. Hanya pemilik dokumen yang menerapkan mutasi; headless tidak boleh menulis salinan stale dari proyek yang sedang dimiliki GUI.

### 8.4 Struktur Direktori Proyek Source Code

```
ltechDesign/
├── pyproject.toml
├── README.md
├── src/
│   └── ltechdesign/
│       ├── main.py
│       ├── app/
│       ├── domain/
│       │   ├── document.py
│       │   ├── nodes.py
│       │   ├── styles.py
│       │   ├── layout.py
│       │   └── commands/
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── canvas/
│       │   ├── panels/
│       │   ├── dialogs/
│       │   └── widgets/
│       ├── renderer/
│       ├── exports/
│       │   ├── raster.py
│       │   ├── pdf.py
│       │   └── web.py
│       ├── mcp_server/
│       │   ├── server.py
│       │   ├── tools/
│       │   ├── resources/
│       │   └── security.py
│       ├── persistence/
│       ├── assets/
│       ├── services/
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── gui/
│   ├── mcp/
│   └── exports/
├── examples/
├── resources/
└── scripts/
```

## 9. Document Schema

Semua objek menggunakan skema konsisten.

Contoh:

```
{
  "schema_version": "1.0",
  "document_id": "doc-001",
  "revision": 1,
  "name": "Landing Page",
  "pages": [
    {
      "id": "page-001",
      "name": "Home",
      "nodes": [
        {
          "id": "frame-001",
          "type": "frame",
          "name": "Desktop Home",
          "parent_id": null,
          "x": 0,
          "y": 0,
          "width": 1440,
          "height": 900,
          "rotation": 0,
          "visible": true,
          "locked": false,
          "opacity": 1,
          "style": {
            "fill": "#FFFFFF"
          },
          "children": [
            "rect-001"
          ]
        },
        {
          "id": "rect-001",
          "type": "rectangle",
          "name": "Primary Button",
          "parent_id": "frame-001",
          "x": 40,
          "y": 80,
          "width": 180,
          "height": 48,
          "rotation": 0,
          "visible": true,
          "locked": false,
          "opacity": 1,
          "style": {
            "fill": "#006633",
            "radius": 8
          },
          "children": []
        }
      ]
    }
  ]
}
```

Koordinat objek dalam contoh bersifat relatif terhadap parent. Semua renderer, export engine, dan MCP tools harus menggunakan konvensi yang sama.

Contoh JSON di atas bersifat ilustratif, bukan keseluruhan schema final. Implementasi wajib menambahkan urutan `root_ids` per page, pivot/scale dan `clip_content` sesuai bagian 20.2, serta memvalidasi konsistensi daftar nodes, root dan parent/children. `session_id` hanya runtime dan tidak disimpan sebagai identitas portabel proyek. Schema final dibekukan dengan fixture di segmen 02; contoh ini tidak boleh dipakai sebagai alasan melewatkan field kontrak.

### Aturan Schema

- Setiap node memiliki ID unik dan stabil.
- Setiap type memiliki schema properties yang jelas.
- Z-order ditentukan dari urutan anak parent atau daftar root.
- Parent-child relationship harus valid tanpa siklus.
- Perubahan memiliki revision.
- Unknown properties tidak boleh menyebabkan crash.
- Upgrade schema harus melalui migration.
- Asset direferensikan menggunakan ID/hash, bukan absolute path mesin pengguna.
- Nilai numerik dan warna harus divalidasi.
- Format internal dibuat independen dari library GUI.

## 10. User Interface Specification

### 10.1 Main Window

**Top Navigation**

- Menu: File, Edit, View, Object, Arrange, Plugins, AI/MCP, Help.
- Project name.
- Save status.
- Undo/Redo.
- Preview dan Export.

**Left Sidebar**

- Pages.
- Layers.
- Assets.
- Components.

**Left/Top Tool Palette**

- Select.
- Frame.
- Rectangle.
- Ellipse.
- Line.
- Pen.
- Text.
- Image.
- Hand.
- Zoom.

**Center Workspace**

- Canvas.
- Artboards.
- Ruler.
- Smart guides.
- Selection controls.
- Grid.

**Right Sidebar**

- Design properties.
- Layout.
- Appearance.
- Typography.
- Image adjustment.
- Export settings.

**Bottom Status Bar**

- Zoom.
- Canvas size.
- Selection details.
- Snap status.
- MCP connection status.

### 10.2 Keyboard Shortcuts

| Shortcut         | Operasi          |
| ---------------- | ---------------- |
| Ctrl + N         | New              |
| Ctrl + O         | Open             |
| Ctrl + S         | Save             |
| Ctrl + Shift + S | Save As          |
| Ctrl + Z         | Undo             |
| Ctrl + Shift + Z | Redo             |
| Ctrl + C / V / X | Copy/Paste/Cut   |
| Ctrl + G         | Group            |
| Ctrl + Shift + G | Ungroup          |
| Ctrl + D         | Duplicate        |
| Ctrl + A         | Select all       |
| V                | Select           |
| F                | Frame            |
| R                | Rectangle        |
| O                | Ellipse          |
| T                | Text             |
| Space + Drag     | Pan              |
| Delete           | Remove selection |

Shortcut yang konflik saat text editing harus dinonaktifkan sementara atau diarahkan ke text editor.

## 11. Non-Functional Requirements

### NFR-001 — Performance

Target awal untuk hardware desktop kelas menengah:

- Startup aplikasi maksimal 5 detik pada SSD setelah instalasi normal.
- Interaksi dasar canvas menargetkan 60 FPS untuk dokumen ringan.
- Mendukung minimal 1.000 objek sederhana dalam satu dokumen dengan interaksi yang masih responsif.
- Batch 100 command sederhana diproses tanpa mengunci main UI secara berkepanjangan.
- Export ukuran standar dapat berjalan tanpa hang; tugas panjang menampilkan progress.

Target divalidasi melalui benchmarking dan dapat disesuaikan terhadap kompleksitas SVG, teks, gambar, dan efek.

### NFR-002 — Reliability

- Autosave dan crash recovery.
- Atomic file saving menggunakan temporary file dan rename/replace.
- Undo/Redo terintegrasi.
- Validasi file dan schema.
- Backup versi sebelum migrasi format.

### NFR-003 — Security

- Berjalan offline tanpa akun.
- Tidak melakukan upload aset secara otomatis.
- Asset path dibatasi.
- File impor dianggap tidak tepercaya.
- Tidak menjalankan script embedded.
- MCP akses dapat dibatasi per proyek.

### NFR-004 — Maintainability

- Arsitektur modular.
- Type hints pada public interfaces.
- Unit tests untuk model dan commands.
- Integration tests untuk save/load/export/MCP.
- Structured logging.
- CI untuk lint, test, dan build.
- Versioned file schema dan MCP tool contracts.

### NFR-005 — Distribution

- Build installer Windows x64.
- Dependensi runtime dibundel.
- Tidak memerlukan instalasi Python oleh pengguna akhir.
- Penyimpanan proyek tidak terikat pada lokasi instalasi.
- Settings disimpan pada folder konfigurasi pengguna.
- Build executable minimal dibuktikan sejak fondasi; installer penuh dan uji tanpa Python development tetap syarat rilis.

## 12. Prioritas MVP

### Phase 1 — Editor Core (P0)

- Main window desktop.
- Project creation.
- Canvas pan/zoom.
- Artboard dan frame.
- Basic shape/text/image.
- Layers.
- Properties inspector.
- Multiselect.
- Undo/Redo.
- Save/load native format.

### Phase 2 — Export and Styling (P0)

- PNG, JPG, WebP, PDF.
- Export artboard/selection.
- Typography.
- Fill, stroke, opacity, radius.
- Basic shadows.
- Snapping dan alignment.
- Autosave/recovery.

### Phase 3 — MCP Integration (P0)

- MCP Server local.
- Read project and document tree.
- Create/update/delete nodes.
- Batch operations.
- Preview rendering.
- Save/export via MCP.
- Integration test menggunakan Codex.

### Phase 4 — Advanced Design (P1)

- Auto Layout lanjutan.
- Design tokens.
- Components.
- Vector pen/boolean operations.
- Image adjustments.
- Templates.
- HTML/CSS export.
- Batch export.

### Phase 5 — Advanced Capabilities (P2)

- Interactive prototyping.
- Plugin API.
- PDF import.
- Advanced raster editing.
- UI accessibility inspection.
- Advanced code generation.
- Optional AI design assistant interface di dalam desktop.

**Definisi MVP selesai:** Pengguna dapat membuat desain dengan minimal 1 artboard dan berbagai layer, menyimpan/membukanya kembali, memanipulasinya secara visual atau via MCP, dan mengekspor ke keempat format wajib tanpa kehilangan data proyek.

MVP fungsional mencakup seluruh P0, AT-01–AT-29 dan AT-31–AT-34. Rilis distribusi pertama juga mensyaratkan AT-30 serta installer dan pemeriksaan Windows bersih. Fitur terimplementasi yang belum dapat diverifikasi diberi status `implemented_pending_verification`, bukan lulus. Blocker mesin uji rilis tidak menghalangi pekerjaan fitur independen, tetapi melarang klaim siap rilis.

P1 mengikuti dependensi teknis, bukan urutan daftar: tokens + layout lanjutan dapat langsung menuju HTML/CSS export; jalur pen/path → boolean, typography, image adjustment dan print dapat dikerjakan terpisah. PDF import tidak memerlukan plugin API kecuali memang dipaketkan sebagai plugin. Fitur produktivitas P1 ada pada FR-030–FR-033; tidak menjadi prasyarat MVP.

## 13. Acceptance Test Scenarios

| Test ID | Skenario                               | Hasil wajib                                                               |
| ------- | -------------------------------------- | ------------------------------------------------------------------------- |
| AT-01   | Buat artboard 1080×1350                | Dimensi akurat                                                            |
| AT-02   | Buat rectangle dan text                | Tampil di canvas                                                          |
| AT-03   | Resize dan rotate objek                | Properti dan canvas sinkron                                               |
| AT-04   | Group dan ungroup                      | Hierarki valid                                                            |
| AT-05   | Save dan reopen                        | Struktur tetap sama                                                       |
| AT-06   | Undo setelah delete                    | Objek kembali                                                             |
| AT-07   | Ekspor PNG transparan                  | Alpha channel benar                                                       |
| AT-08   | Ekspor JPG                             | Tidak ada alpha                                                           |
| AT-09   | Ekspor WebP                            | File dapat dibuka kembali                                                 |
| AT-10   | Ekspor PDF multipage                   | Ukuran dan jumlah halaman sesuai                                          |
| AT-11   | Codex membaca layer                    | Struktur node dikembalikan                                                |
| AT-12   | Codex membuat objek                    | Objek muncul pada proyek                                                  |
| AT-13   | Codex mengubah warna                   | Model dan renderer sinkron                                                |
| AT-14   | MCP batch gagal                        | Transaksi rollback                                                        |
| AT-15   | Simulasi revision conflict             | Tidak menimpa perubahan terbaru                                           |
| AT-16   | MCP export file                        | File tercipta di lokasi yang diizinkan                                    |
| AT-17   | Aplikasi crash sebelum save manual     | Recovery tersedia                                                         |
| AT-18   | Buka file malformed                    | Error terkendali, tanpa crash                                             |
| AT-19   | MCP mencoba akses path tidak diizinkan | Akses ditolak                                                             |
| AT-20   | Headless rendering                     | Output konsisten dengan desktop dalam toleransi rendering yang ditetapkan |
| AT-21 | GUI dan headless membuka file sama | Writer kedua read-only/ditolak atau diarahkan attached; tidak menimpa pemilik |
| AT-22 | File berubah di luar aplikasi | Save mendeteksi konflik; Reload/Save As tersedia tanpa overwrite diam-diam |
| AT-23 | Timeout lalu retry request AI | Request sama tidak menggandakan operasi; payload berbeda dengan ID sama ditolak |
| AT-24 | Group/reparent pada parent berotasi | Tampilan visual tetap; undo mengembalikan hierarchy dan transform |
| AT-25 | Replace/delete image lalu cleanup dan undo | Aset yang masih dirujuk history/recovery tersedia |
| AT-26 | Multi-tab dan salinan dengan document ID sama | Routing session_id tepat dan history terpisah |
| AT-27 | Skala Windows 100/150/200% dan pindah monitor | UI, handles dan hit-testing tepat; ukuran ekspor tidak ikut skala layar |
| AT-28 | Pagination tree saat revision berubah | Cursor lama ditolak dengan error yang mengarahkan client memulai query ulang |
| AT-29 | Cancel job impor/ekspor berat | UI responsif, konten utuh dan staging/output sementara ditangani |
| AT-30 | Paket pada Windows bersih tanpa Python dev | Startup, file proyek, font, codecs, SVG, PDF dan stdio MCP bekerja |
| AT-31 | Save lalu Import Project lengkap | Page/artboard/layer, ID, urutan, transform, teks, style, layout dan tokens dipulihkan editable; edit lanjutan dapat disimpan ulang |
| AT-32 | Pindahkan satu file proyek, hapus sumber aset, matikan internet | Desain/aset embedded tetap terbuka; font hilang dilaporkan tanpa menimpa metadata asli |
| AT-33 | Hash/manifest rusak, aset hilang, versi/capability tidak didukung | Error terstruktur; tab aktif tetap utuh; preview tidak dipakai untuk memalsukan restore |
| AT-34 | Load → Save → Load berulang | Semantic equality konten dan hash byte aset sama; runtime IDs/lock/history tidak tersimpan; preview konsisten dalam toleransi renderer |

## 14. Risiko dan Mitigasi

| Risiko                                   | Tingkat | Mitigasi                                      |
| ---------------------------------------- | ------- | --------------------------------------------- |
| Rendering lambat pada dokumen kompleks   | Tinggi  | Caching, dirty-region redraw, profiling       |
| Layout yang dihasilkan AI berantakan     | Tinggi  | Constraint engine, validation, preview-revise |
| Sinkronisasi MCP dan GUI                 | Tinggi  | Command queue + revision check                |
| Perbedaan hasil visual dan PDF           | Sedang  | Shared drawing primitives, golden-image tests |
| WebP tidak didukung encoder Qt bawaan    | Sedang  | Pemeriksaan kemampuan + fallback              |
| Missing fonts                            | Sedang  | Font validation dan substitution warning      |
| Proyek rusak akibat crash                | Tinggi  | Atomic save + autosave                        |
| Scope creep mendekati fitur Figma penuh  | Tinggi  | Pembagian MVP/P1/P2                           |
| Penggunaan MCP oleh client tak tepercaya | Tinggi  | Access controls + audit + consent             |
| Ekspor HTML/CSS tidak responsif sempurna | Sedang  | Pemetaan dari layout model + AI refinement    |

## 15. Indikator Keberhasilan

Pengukuran keberhasilan awal:

- 100% acceptance tests kritis P0 lulus.
- Keempat format ekspor wajib berfungsi.
- Operasi save/load tidak mengubah semantik dokumen.
- MCP dapat melakukan end-to-end create/edit/save/export.
- Undo bekerja untuk semua mutasi penting melalui GUI maupun AI.
- Pengguna dapat menyelesaikan satu poster dan satu mockup halaman web tanpa menggunakan software desain eksternal.
- Tidak ada data proyek yang hilang dalam skenario recovery yang diuji.

## 16. Ketentuan Pengembangan

1. Python menjadi bahasa utama untuk engine, desktop UI, persistence, dan MCP.
2. Aplikasi harus bisa berjalan tanpa koneksi internet.
3. Tidak boleh membuat MCP Server sebagai satu-satunya jalur perubahan desain; editor manual tetap berfungsi penuh.
4. Semua perubahan AI wajib menggunakan command engine yang sama dengan GUI.
5. Setiap fitur baru yang mengubah dokumen harus menyediakan dukungan serialization, rendering, undo, dan export.
6. Kode dikembangkan menggunakan modular architecture, bukan satu file monolitik.
7. Implementasi harus dilengkapi pengujian dan dokumentasi.
8. Perubahan skema harus mempertahankan kompatibilitas semaksimal mungkin melalui versioned migrations.
9. Komunikasi MCP harus menggunakan schema yang stabil dan eksplisit.
10. Fitur P1/P2 tidak boleh memblokir penyelesaian fungsi inti MVP.

## 17. Deliverables

Paket pengembangan akhir minimal memuat:

- Source code Python.
- Installer Windows x64.
- Native desktop UI.
- Visual design editor.
- Save/load `.ltechdesign`.
- Export PDF/PNG/JPG/WebP.
- MCP Server lokal.
- Dokumentasi tool MCP.
- Contoh konfigurasi Codex.
- Contoh desain poster dan web UI.
- Automated tests.
- Developer setup guide.
- User guide.

**Kesimpulan:** ltechDesign Studio dikembangkan sebagai aplikasi desain desktop offline-first dengan editing visual yang kuat dan arsitektur AI-native. Komponen inti produk adalah document model yang independen, renderer konsisten, command engine transaksional, serta MCP Server yang memungkinkan Codex melakukan operasi desain secara terstruktur dan aman.

## 18. Gambaran Arsitektur yang Direkomendasikan

Codex / ChatGPT / AI Client

Prompt desain, membaca proyek, melakukan revisi

Model Context Protocol (MCP)

Python MCP Server

Tool Registry · Resource Provider · Access Control

Document Model + Command Engine

Single Source of Truth · Validation · Undo/Redo

PySide6 Desktop UI

Canvas · Layers · Inspector

Rendering & Export

PNG · JPG · WebP · PDF

File Persistence

.ltechdesign · Assets

Layout & Components

Frames · Styles · Tokens

## 19. Rekomendasi Teknis untuk Mulai Pengembangan

Saya merekomendasikan PySide6 + QGraphicsScene/QGraphicsView untuk MVP, dengan document model terpisah dari renderer. Pendekatan ini lebih realistis daripada langsung membangun graphics engine setara Figma dari nol.

Gunakan dokumentasi resmi versi Qt dan MCP SDK yang benar-benar dipilih, lalu catat versi dependency yang kompatibel dan telah diuji. Dukungan WebP, font, offscreen rendering dan plugin Qt perlu dibuktikan pada paket distribusi Windows; nomor versi contoh tidak menjadi pin dependency otomatis.

Untuk perubahan desain oleh AI, gunakan MCP tools yang membuat dan mengubah objek secara langsung dalam document model. Hasilnya dapat divalidasi, direproduksi, diuji, dan di-undo.

Untuk pengembangan melalui VS Code dan Codex, urutan implementasi yang paling efektif adalah:

1. Bangun document model, canvas, dan layer management.
2. Selesaikan penyimpanan `.ltechdesign` beserta undo/redo.
3. Implementasikan rendering dan empat format ekspor.
4. Buat MCP Server yang menggunakan command engine yang sama.
5. Uji workflow: prompt Codex → MCP → perubahan canvas → revisi → export.
6. Setelah stabil, baru tambahkan Auto Layout, komponen, design tokens, dan HTML/CSS export.

Dengan pendekatan tersebut, aplikasi akan memiliki fondasi desain yang dapat berkembang menjadi editor visual profesional sekaligus platform desain yang dapat dikendalikan AI, tanpa mengorbankan kemampuan bekerja sepenuhnya secara lokal.

## 20. Kontrak Tambahan dan Produktivitas — Revisi 1.1

Bagian ini menetapkan keputusan hasil review. Jika uraian umum di bagian terdahulu ambigu, kontrak khusus di sini menjadi acuannya. Perubahan kontrak berikutnya dicatat sebagai ADR dan disertai migration bila memengaruhi file.

### 20.1 FR-027 — File Ownership, Sessions dan External Changes (P0)

- Satu writer untuk satu file proyek dengan path kanonis. Gunakan lock antarproses, misalnya adapter QLockFile di persistence; domain tetap independen dari Qt. Seluruh proses aplikasi harus mengikuti kebijakan yang sama.
- Open kedua menggunakan read-only atau menolak write dengan alasan jelas. MCP memakai attached mode jika GUI sudah menjadi pemilik dan bridge tersedia; tidak membuka writer kedua secara diam-diam.
- Baseline fingerprint file (hash isi dan metadata relevan) dicatat saat open/save. Sebelum replace, cek perubahan eksternal; jika berubah, batalkan save dan tawarkan Reload atau Save As. File watcher membantu notifikasi, tetapi tidak menggantikan cek saat save. Lock aplikasi tidak menjamin koordinasi dengan program asing yang mengabaikannya; batas ini harus didokumentasikan.
- `document_id` persisten mengidentifikasi dokumen portabel. `session_id` runtime unik mengidentifikasi instance terbuka, meski dua salinan memiliki document ID sama. Content revision adalah counter monoton per sesi, termasuk commit undo/redo; client baru mengambil revision terkini dan tidak memakai revision lintas sesi sebagai urutan global.
- Save As memperoleh lock target dan memeriksa baseline sebelum menulis, lalu memindahkan ownership setelah sukses. Lock sumber dipertahankan selama save target belum berhasil. Duplicate Project menghasilkan document ID baru serta remap ID sesuai kebijakan clone; Save As boleh mempertahankan document ID.
- Close melepaskan lock; stale lock setelah crash hanya dipulihkan setelah pemeriksaan pemilik. Read-only tidak menimpa file asal; Save As ke file baru tetap tersedia. Routing serta history selalu berbasis session ID.

### 20.2 Kontrak Geometri dan Rendering (P0)

- Unit internal logical pixel pada bidang 2D; x ke kanan, y ke bawah, sudut derajat positif mengikuti rotasi visual searah jarum jam. DPI untuk konversi ukuran fisik/ekspor; device pixel ratio layar hanya urusan UI.
- Tiap node memiliki x/y relatif parent, geometry lokal, `rotation`, pivot lokal eksplisit dan positive uniform `scale` (default 1). Transform titik adalah `T(x,y) × T(pivot) × R(rotation) × S(scale) × T(-pivot)`; transform scene merupakan komposisi ancestor. x/y adalah translasi lokal, bukan scene bounding-box minimum.
- Pivot default pusat geometry saat create; command resize memperbarui pivot dan translasi sebagai satu transaksi untuk mempertahankan anchor yang dipilih. Group pivot dan geometry dihitung dari isi dan dinormalisasi tanpa menggeser tampilan anak. Formula reparent memakai inverse transform parent baru untuk mempertahankan transform dunia.
- P0 tidak mendukung shear, flip atau scale negatif. Resize melewati ukuran nol ditahan sesuai minimum tipe node, bukan dibalik diam-diam. Line memakai endpoints dan dapat memiliki bounds nol pada satu sumbu; aturan dimensi tidak boleh melarang garis horizontal/vertikal.
- Resize group P0 mempertahankan rasio dan mengubah positive uniform scale, sehingga isi ikut terskala. Nonuniform group scaling adalah backlog di luar komitmen MVP/P1 inti; jika dijadwalkan, perlu ADR representasi affine/migrasi dan prompt tersendiri, bukan perkiraan x/y/rotation yang mengubah tampilan. Resize frame mengubah geometry dan menjalankan constraints/layout anak; bukan otomatis menskalakan seluruh isi.
- Bedakan geometry bounds, visual bounds (stroke/shadow setelah transform dan clipping) serta hit-test bounds dengan toleransi layar. Selection export memakai visual bounds final; overlay editor tidak termasuk.
- `clip_content` default true untuk artboard dan false untuk frame/group; dapat diubah lewat UI/command. Rounded frame memakai radius yang sama untuk fill dan clip. Stroke P0 center-aligned; radius dibatasi ke geometry yang sah.
- Opacity group P0 memakai komposit terisolasi: render children dengan opacity masing-masing lalu terapkan opacity group sekali. Jika backend memerlukan raster offscreen, gunakan fallback yang sama pada preview/export dan laporkan rasterisasi PDF untuk group tersebut. Jangan menggantinya dengan opacity turunan per child yang menghasilkan overlap berbeda.
- `root_ids` dan `children` adalah urutan render eksplisit. Node registry + parent_id + daftar children/root wajib konsisten. Hanya dispatcher mengubah relasi; loader menolak kontradiksi daripada memilih hierarchy secara diam-diam.
- Shared drawing mencakup transform, text layout, clipping, stroke, shadow dan alpha. Fixture minimum memuat nested rotation, group opacity dengan anak overlap, rounded clip, teks multiline, gambar transparan dan beberapa artboard.

### 20.3 FR-028 — Transaction Boundaries, Retry dan History (P0)

- Semua perubahan **konten** melalui dispatcher; validasi menghasilkan rencana transaksi sebelum commit. Recalculation layout menjadi bagian commit yang sama. Satu transaksi berhasil menaikkan revision sekali dan menerbitkan event setelah commit.
- Undo/redo hanya konten. Selection, active page, viewport dan status job adalah state sesi; perubahan tersebut tidak mengubah content revision. Event sesi terpisah dari event konten.
- Save/export tidak boleh berada di batch perubahan node. Import aset mandiri adalah transaksi asset store; asset ID hasilnya dapat dipakai command berikutnya. Batch gabungan import+create memakai staging sampai commit; gagal/cancel membersihkan staging tanpa menyisakan aset terdaftar.
- Setiap mutasi MCP memerlukan `request_id`, `session_id`, `expected_revision`. Deduplication discope oleh identitas client terautentikasi/bridge, session dan request ID. Simpan digest payload kanonis dan hasil operasi: ID sama/payload sama mengembalikan hasil lama tanpa commit ulang; payload berbeda mengembalikan `request_id_conflict`.
- Pengecualian target baru: `create_project` belum memiliki session/revision, sehingga request ID dideduplikasi pada scope client + server instance dan hasilnya mengembalikan session ID baru. `open_project` membaca/mendaftarkan sesi serta mengikuti ownership; tidak dianggap mutasi konten. `set_selection` tidak memerlukan expected content revision, tetapi wajib session ID. Save/export/job cancellation mempunyai kontrak side effect terpisah; save/export menyebut snapshot revision yang dimaksud dan request ID agar retry mengembalikan job/hasil yang sama selama masa retensi.
- Pemeriksaan deduplication dilakukan sebelum menolak expected revision lama untuk retry yang sudah sukses. Request in-flight yang sama bergabung/menunggu hasil, bukan dieksekusi dua kali. Retensi hasil minimum 30 menit dalam sesi hidup dengan kapasitas terkonfigurasi; jika kapasitas penuh untuk entry yang belum boleh kedaluwarsa, tolak request baru secara terstruktur. Setelah retensi atau restart, client tidak boleh mengulang mutasi buta: baca ulang state/revision dan rekonsiliasi dahulu. Tidak menjanjikan exactly-once melintasi crash tanpa journal persisten.
- Undo history memiliki batas memori terkonfigurasi; budget awal 128 MiB per dokumen, divalidasi dengan benchmark. Eviction hanya membuang entry utuh dan memberi tahu batas undo. Asset GC mempertahankan referensi dari konten aktif, history, snapshot, recovery dan job yang sedang berjalan; cleanup tidak membuat undo rusak.
- History metadata menyimpan nama aksi, sumber GUI/AI, timestamp dan request ID bila ada; UI history lengkap P1.

### 20.4 FR-029 — Bounded Inspection, Preview dan Jobs (P0)

- `get_document_tree` menerima filter page/subtree/name/type, depth, fields, limit dan cursor; default 100 dan maksimum 500 node per halaman. Urutan deterministik dan cursor terikat session, revision serta digest query. Revision berubah menghasilkan `stale_cursor`; client memulai ulang query. Resource tree menggunakan service query yang sama.
- Preview menargetkan artboard/selection/region dan mencantumkan session, revision, bounds, dimensions, mime type. Dimensi maksimum default 2048 px per sisi; request lebih besar harus dibatasi atau ditolak dengan batas yang jelas. Output lama tetap diberi revision sumber, bukan dilabeli revision terbaru.
- Artifact preview sementara memiliki opaque ID dan TTL default 30 menit; dihapus setelah tidak dipakai job/resource. Hasil export yang diminta disimpan pengguna tidak dihapus hanya karena TTL preview.
- Gunakan image content/resource yang didukung client atau jalur file lokal untuk client lokal yang benar-benar memiliki akses. File path lokal bukan bukti client cloud dapat membaca artifact. Capabilities dan batas transfer dicatat; kegagalan akses dilaporkan eksplisit.
- Impor/ekspor/render/save berat memakai lifecycle `queued/running/succeeded/failed/cancelled` dengan job ID, progress, cancellation dan error terstruktur. Operasi kecil boleh selesai sinkron. Sediakan `get_job_status` dan `cancel_job` sebagai tool P0; log dan hasil menyertakan revision snapshot sumber.
- Job menahan snapshot/aset yang diperlukan. Cancellation sebelum commit membatalkan staging; sesudah commit tidak dilabeli cancelled seolah side effect hilang. Ekspor memakai temporary output dan replace per file; batch export P1 dapat sukses parsial dengan laporan per output.
- Batas awal: payload JSON 4 MiB, batch 100 operasi, asset 50 MiB/file, raster terdecode 40 megapixel, archive 10.000 entry/512 MiB total uncompressed, render 64 megapixel/output. Tolak sebelum alokasi besar bila memungkinkan. Semua batas configurable dalam rentang aman, terdokumentasi dan diuji. Fixture di luar batas menguji penolakan; dokumen 1.000 node tetap dapat dibaca bertahap.
- Timeout bridge awal 30 detik untuk request biasa; job panjang tetap dapat dipoll dan tidak dianggap gagal commit hanya karena koneksi client terputus. Ukuran output/resource dan queue diberi backpressure yang diuji.

### 20.5 Verification Gates dan Benchmark

- Segmen 01 membuktikan executable minimal dapat menampilkan window tanpa fitur editor. Sesudah 04 uji dua proses dan file ownership. Sesudah 06 buktikan fixture kecil melalui canvas, PNG, PDF dan offscreen; text fixture boleh memakai primitive shared renderer awal sebelum inline editing tersedia.
- Sebelum memperluas MCP, buktikan satu command subprocess → dispatcher → GUI → respons revision. Ukur baseline ringan setelah segmen 08, 12 dan 19; bukan baru setelah seluruh MVP selesai.
- Benchmark acuan awal: Windows x64, CPU 4 core, RAM 16 GiB, SSD; catat model hardware, OS, display scale, dependency, artifact dan warm/cold run aktual. Target divalidasi di perangkat acuan, bukan dijamin untuk seluruh PC.
- Dokumen ringan: 100 shape sederhana tanpa efek, satu artboard. Target sekitar 60 FPS dan p95 frame time ≤20 ms saat pan/drag 10 detik; catat p95/p99 serta freeze terpanjang, bukan hanya rata-rata.
- Fixture 1.000 objek deterministik: pan/selection tidak membeku >100 ms. Batch 100 perubahan properti sederhana menargetkan commit ≤500 ms dan UI tetap dapat merespons dalam 100 ms. Catat waktu commit terpisah dari IPC dan render.
- Budget awal resident memory untuk satu fixture 1.000 shape ≤512 MiB di luar asset raster besar; lakukan beberapa putaran open/close untuk mendeteksi pertumbuhan. Budget adalah target ukur awal dan hanya berubah melalui ADR dengan bukti.
- Font visual tests dipaketkan hanya jika izinnya sesuai; font/metrik sama dipakai untuk baseline deterministik. Perbandingan lintas OS menggunakan toleransi yang dijelaskan; geometry/alpha tidak boleh lolos hanya karena toleransi gambar terlalu longgar.
- Simpan fixture schema lama, migration tests dan artifacts diff. `scripts/check.ps1` memilih pemeriksaan sesuai subsistem dan mengembalikan exit code gagal; `scripts/run.ps1` serta generator fixture memudahkan reproduksi. Tidak perlu menjalankan suite berat yang tidak relevan setiap edit.
- Status requirement/segmen: `not_started`, `in_progress`, `implemented_pending_verification`, `verified`, `blocked`, `not_included`. P0 wajib tidak dapat ditandai `not_included`; HTTP opsional boleh. Catat implementasi, hasil otomatis, inspeksi visual dan verifikasi manual secara terpisah. `verified` adalah bukti selesai lingkup, bukan otomatis siap rilis.

### 20.6 FR-030 — Produktivitas Editor (P1, kecuali dasar P0)

- Nudge/step besar dan forward/backward dasar P0 mengikuti FR-003. Tambahkan duplicate-in-place dan paste-in-place P1 dengan ID/aset benar dan undo tunggal.
- Paste image dari clipboard Windows P1 awal: prioritaskan MIME gambar yang didukung, validasi batas decoding dan masukkan ke asset store; jangan bergantung pada file sementara yang hilang setelah restart.
- Guides manual dengan drag posisi, lock/hide dan snapping; tersimpan per page dengan aturan apakah ikut history konten yang jelas. Guides dan overlay tidak diekspor.
- Command palette dengan pencarian aksi; preferences tema, default unit dan shortcut tersimpan per pengguna. Interval autosave configurable tetap P0. Uji konflik shortcut dan pemulihan defaults.
- Aksesibilitas UI dasar P0: focus keyboard, urutan tab, label kontrol, kontras dan indikator state yang tidak bergantung pada warna saja, serta layout High DPI. Audit keyboard/screen reader menyeluruh P1; terpisah dari `analyze_design` dan aksesibilitas desain P2.

### 20.7 FR-031 — Recovery dan Riwayat Produktif (P1)

- Session restore menyimpan daftar dokumen/tab dan recovery yang relevan; tidak diam-diam mengambil alih writer eksternal ketika restore.
- Missing asset/font manager menjelaskan substitusi dan menyediakan relink yang dapat dibatalkan. Relink memperbarui asset store serta semua referensi yang dipilih tanpa mengganti geometry tanpa izin.
- History panel memperlihatkan nama aksi dan sumber GUI/AI; memilih beberapa langkah undo menggunakan engine yang sama. Named local snapshots terpisah dari undo, portabel dalam penyimpanan snapshot yang terdokumentasi, dengan retensi/jatah disk configurable dan konfirmasi penghapusan snapshot pengguna.

### 20.8 FR-032 — Preview AI dan Handoff Vektor (P1)

- `preview_operations`/dry-run memvalidasi batch pada snapshot terisolasi lalu mengembalikan ringkasan diff, base revision dan preview. Tidak mengubah live content/history/assets permanen. Apply mengirim operasi yang sama dengan expected revision dan request ID; jika state berubah, preview diulang. Dry-run bukan transaksi yang menahan lock UI sambil menunggu pengguna.
- Export SVG untuk subset shape/path/text/image/transform/clipping yang didukung dengan capability report. Unsupported feature diberi warning dan fallback eksplisit; tidak boleh silently dropped. Embedded asset menjaga portabilitas, batas ukuran serta kebijakan font dijelaskan. Import SVG yang sudah ada tetap harus kompatibel dengan subsetnya, bukan janji round-trip SVG universal.

### 20.9 FR-033 — Diagnostics dan Pengelolaan Pengembangan (P1; fondasi development P0)

- Diagnostic bundle lokal berisi versi, capabilities, log terpilih dan informasi lingkungan dengan preview/redaksi path/identitas pengguna. Konten desain, aset dan secret tidak disertakan default; tidak ada upload otomatis.
- ADR singkat menyimpan keputusan schema, thread/IPC, rendering, ownership, dependency dan packaging. Handoff mencantumkan ID segmen, kontrak, perintah verifikasi, blocker dan revision kode/commit bila tersedia; jangan membuat commit otomatis tanpa kebijakan pengguna.
- Progress dibaca ringkas sesuai segmen untuk membatasi konteks. Perubahan dependency/rendering/packaging memicu ulang spike terkait, bukan rewrite seluruh aplikasi.
- Penerimaan fitur P1 memerlukan tes khusus: clipboard bertahan setelah reopen, guide tidak ikut export, relink/restore/history benar, preview AI tidak memutasi sumber, SVG dapat dibuka viewer independen dan diagnostics tidak berisi secret/desain default. Pemilik prompt dan bukti dicatat pada requirements matrix.
