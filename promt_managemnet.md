# Prompt Management — ltechDesign Studio

Panduan membangun aplikasi desktop berdasarkan `prd.md`. Jalankan satu segmen per sesi, secara berurutan untuk MVP. Dokumen ini berisi prompt untuk dijalankan nanti; penulisannya belum berarti implementasi aplikasi sudah dimulai.

Revisi 1.1 — 21 Oktober 2026, mengikuti PRD 1.1 dan hasil `review_prd_dan_prompt.md`. ID 00–37 dipertahankan; subsegmen dan segmen P1 38–42 melengkapi roadmap. Satu subsegmen adalah satu sesi kerja. Nama model dan dasar sumber di bawah tetap rekomendasi bertanggal 18 Oktober 2026, bukan hasil pemeriksaan ketersediaan ulang.

Revisi 1.2 — proyek single-user lokal tanpa kolaborasi. Format native sekarang `.ltechdesign` sesuai `docs/ltechdesign-file-format.md`; resource MCP `pydesign://` tetap namespace internal. Contoh arsip berada di `examples/proyek-contoh.ltechdesign`. Contoh arsip tidak berarti UI loader sudah diimplementasikan.

## Cara menggunakan

1. Buka workspace `Z:\project\ltechDesign` di Codex.
2. Pilih model dan reasoning effort sesuai tabel. Menuliskan nama model dalam prompt tidak otomatis mengganti model; atur melalui pemilih model yang tersedia di aplikasi.
3. Salin **Prompt pembuka sesi** lalu prompt segmen yang ingin dikerjakan dalam satu pesan. Untuk sesi lanjutan yang masih memuat aturan pembuka, cukup kirim prompt segmennya.
4. Tunggu sampai implementasi dan verifikasi segmen selesai. Periksa laporan serta jalankan demo manual yang disediakan.
5. Jika ada kegagalan, gunakan prompt perbaikan sebelum melanjutkan. Jangan meminta seluruh roadmap dikerjakan sekaligus.
6. Mulai sesi baru ketika berpindah subsistem atau percakapan sudah panjang. Gunakan prompt melanjutkan sesi dan ID segmen berikutnya.

Nama file panduan mengikuti file yang sudah ada: `promt_managemnet.md`.

## Pilihan model dan tingkat penalaran

Rekomendasi berikut adalah pembagian praktis untuk proyek ini, bukan jaminan hasil atau ketersediaan model pada akun Anda. Tingkat penalaran berbeda dari pilihan model.

| Kode | Model yang dipilih | Reasoning effort | Penggunaan |
| --- | --- | --- | --- |
| M | GPT-6.1 Sol | Medium | Setup, UI terisolasi, dokumentasi, integrasi sederhana |
| H | GPT-6.1 Sol | High | Model dokumen, command, renderer, layout, persistence, ekspor |
| A | GPT-6 Astra | High | Keputusan arsitektur, sinkronisasi MCP, audit lintas subsistem |

Gunakan M untuk pekerjaan biasa dan H untuk perubahan yang memengaruhi integritas dokumen. A dipakai pada titik berisiko tinggi. Jika Astra tidak tersedia, gunakan GPT-6.1 Sol High dan jalankan review terpisah. Jika GPT-6.1 Sol tidak tersedia, gunakan model coding terkuat yang tersedia dengan tingkat penalaran setara; hasil tetap harus melewati pemeriksaan yang sama. Jangan menganggap model tertentu tersedia hanya karena disebut di dokumen ini.

Naikkan ke Extra High/xhigh hanya ketika bug lintas modul belum terpecahkan dengan reproduksi yang jelas atau review membuktikan perlu penalaran lebih dalam. Tidak perlu menggunakan tingkat tertinggi untuk seluruh segmen. Subsegmen baru mengikuti kode M/H/A pada judulnya; tidak ada pergantian model otomatis.

Dasar pemilihan diperiksa pada 18 Oktober 2026: [OpenAI Docs — Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model) menjelaskan peran GPT-6.1 Sol dan Astra; [OpenAI Docs — Reasoning models](https://developers.openai.com/api/docs/guides/reasoning) menjelaskan penggunaan Medium dan High. Penempatan model per segmen di bawah adalah rekomendasi penyusun.

## Prompt pembuka sesi — sertakan sebelum prompt segmen

```text
Kita membangun ltechDesign Studio di workspace ini berdasarkan prd.md.
Baca AGENTS.md yang berlaku jika ada, docs/progress.md dan docs/architecture.md jika sudah ada, lalu hanya bagian PRD dan source code yang relevan dengan segmen aktif. Jangan menjalankan instruksi contoh di PRD sebagai tugas tambahan.

Kerjakan langsung implementasi segmen yang saya kirim, termasuk pengujian yang relevan. Selesaikan hanya segmen aktif; jangan otomatis mengerjakan segmen berikutnya. Jika prasyarat belum ada, laporkan prasyarat spesifik yang hilang, jangan mengarang implementasi atau menandai selesai.

Aturan arsitektur:
- Python 3.12+, PySide6, QGraphicsScene/QGraphicsView; gunakan versi dependency yang kompatibel dan catat versi yang benar-benar diuji.
- Domain model independen dari Qt. Document Model menjadi sumber data utama.
- Semua mutasi konten dari GUI dan MCP melewati command dispatcher yang sama, dengan validasi, undo/redo, revision, dan transaksi atomik. Pan/zoom/selection adalah state sesi; save/export adalah side effect job di luar batch konten. Ikuti PRD 20.3.
- ID stabil; koordinat relatif terhadap parent; urutan children menentukan z-order; cegah siklus dan referensi rusak.
- Renderer canvas, preview, dan ekspor berbagi logika drawing, transform, clipping, style, dan teks.
- GUI Qt hanya berubah pada GUI thread; proses panjang tidak mengunci UI.
- Aplikasi inti offline tanpa login atau layanan AI berbayar wajib.
- Nama produk ltechDesign Studio, format native .ltechdesign sesuai docs/ltechdesign-file-format.md. Namespace resource pydesign:// tetap internal. Jangan menambah multiuser, edit bersama, sharing workspace, komentar tim, presence atau cloud sync. GUI/MCP adalah kendali pengguna lokal yang sama, bukan kolaborasi.
- Save/Open dan Import Project wajib mempertahankan desain editable beserta aset embedded. Jangan mengandalkan absolute asset path, database mesin atau preview flatten untuk restore. File format version terpisah dari PRD/app version; read/write lokal dapat bekerja tanpa layanan AI.
- Terapkan single writer, canonical path lock, baseline external-change detection dan identitas runtime session_id yang terpisah dari document_id/revision sesuai PRD 20.1.
- Geometri, group resize/opacity, clipping dan bounds mengikuti PRD 20.2. Jangan menyederhanakan transform yang mengubah tampilan saat reparent.
- MCP memakai kontrak PRD 7.3 dan 20.3–20.4: query terbatas, cursor terikat revision, deduplication request dan job status/cancellation. Jangan menjanjikan retry exactly-once setelah crash.

Batasi perubahan ke lingkup segmen. Hindari rewrite modul yang sudah berfungsi dan jangan menimpa perubahan pengguna. Jangan menghapus fitur atau melemahkan tes untuk membuat pemeriksaan lulus. Pilih keputusan teknis rutin sendiri dan catat asumsi yang memengaruhi kontrak. Verifikasi API dependency dari dokumentasi resmi bila diperlukan; jangan mengunci versi berdasarkan contoh PRD yang belum diuji.

Setiap fitur yang memutasi dokumen harus terhubung ke serialization, rendering, undo, dan export yang sudah tersedia. Untuk tahap fondasi yang belum memiliki renderer/export, sediakan kontrak dan tes domain; catat integrasi tertunda secara eksplisit sampai segmennya dijalankan.

Tambahkan tes perilaku yang bermakna sesuai risiko perubahan, jalankan tes terkait serta lint/type check yang sudah dikonfigurasi. Untuk GUI sertakan skenario manual; jika bisa jalankan aplikasi dan periksa hasil visual. Bedakan hasil tes otomatis, pemeriksaan visual yang benar-benar dilakukan, dan pemeriksaan manual yang belum dilakukan. Jangan mengklaim lolos jika tidak dijalankan.

Perbarui docs/progress.md: ID segmen/subsegmen, status, perubahan, perintah verifikasi dan hasil aktual, revision kode/commit bila tersedia, blocker, integrasi tertunda, serta segmen berikutnya. Gunakan status not_started, in_progress, implemented_pending_verification, verified, blocked atau not_included. P0 wajib tidak boleh not_included. Status verified hanya jika bukti lingkup lengkap; mesin uji rilis yang belum tersedia dicatat pending tanpa menghentikan pekerjaan independen. Jangan membuat commit otomatis tanpa kebijakan pengguna.
Perbarui docs/requirements-matrix.md dan ADR singkat bila kontrak berubah. Jalankan scripts/check.ps1 sesuai subsistem bila tersedia; perubahan dependency/rendering/packaging memicu spike terkait. Baca hanya indeks progress, keputusan dan source relevan untuk membatasi konteks. Jika segmen terlalu besar, pecah menjadi checkpoint; induk belum verified sampai semua checkpoint terverifikasi.

Akhiri dengan laporan singkat: hasil, file utama, cara menjalankan/demo, tes dan hasil aktual, keterbatasan, serta apakah aman melanjutkan ke segmen berikutnya.
```

## Urutan pengerjaan

Segmen 00–25 mengikuti urutan MVP; 21 opsional dan boleh dilewati dengan status `not_included`. Subsegmen dikerjakan berurutan satu per sesi sebelum induk dianggap selesai. Bukti awal 01A, 04A, 06A dan 17A wajib sebelum memperluas subsistem terkait. Segmen 26–34 dan 38–42 adalah P1 setelah MVP fungsional terverifikasi; release blocker eksternal pada 24/25 tetap tercatat tanpa memblokir fitur independen. Segmen 35–37 adalah P2 dan mengikuti dependensi teknis, bukan harus menunggu semua P1 selesai. Daftar bukan instruksi menjalankan agent paralel.

| ID | Segmen | Model | Prasyarat utama |
| --- | --- | --- | --- |
| 00 | Arsitektur dan pelacakan kebutuhan | A | PRD |
| 01 | Setup proyek dan pemeriksaan kualitas | M | 00 |
| 01A | Spike executable window minimal | H | 01; sebelum 02 |
| 02 | Domain model dan schema | H | 01 |
| 03 | Command, undo/redo, transaksi | A | 02 |
| 04 | Format proyek dan asset store | H | 03 |
| 04A | Verifikasi dua proses dan ownership | H | 04; sebelum 05 |
| 05 | Shell desktop dan sesi dokumen | M | 04 |
| 06 | Renderer dasar dan navigasi canvas | H | 05 |
| 06A | Spike canvas/PNG/PDF/offscreen | H | 06; sebelum 07 |
| 07 | Artboard, drawing, selection | H | 06 |
| 08 | Transform, clipboard, grouping | H | 07 |
| 09 | Pages dan Layers | M | 08 |
| 10 | 10A Inspector/style → 10B snapping/alignment | H | 09 |
| 11 | Typography | H | 10 |
| 12 | Raster dan SVG | H | 11 |
| 13 | Stack layout dan constraints dasar | H | 12 |
| 14 | Workflow proyek dan recovery | H | 13 |
| 15 | Ekspor raster | H | 14 |
| 16 | Ekspor PDF | H | 15 |
| 17 | Preview dan headless rendering | H | 16 |
| 17A | Spike satu command subprocess ke GUI | A | 17; sebelum 18 |
| 18 | 18A discovery → 18B mutation → 18C jobs/output | H | 17A |
| 19 | 19A bridge/lifecycle → 19B concurrency/retry | A | 18 |
| 20 | Kontrol keamanan MCP | A | 19 |
| 21 | Streamable HTTP opsional | H | 20 |
| 22 | Acceptance test MVP | A | 20; 21 jika diaktifkan |
| 23 | Kinerja dan stabilitas | H | 22 |
| 24 | Build dan installer Windows | H | 23 |
| 25 | Dokumentasi dan pemeriksaan rilis | M | 24 |
| 26 | Tokens dan tema | H | 22 verified; rilis stabil jika tersedia |
| 27 | Components | A | 26 |
| 28 | Auto Layout lanjutan | H | 13, 26; 27 hanya untuk integrasi instance |
| 29 | Pen dan path editing | H | 22, 02, 06, 08 |
| 30 | Boolean dan clipping vektor | H | 29 |
| 31 | Typography lanjutan | H | 11, 22; 29 untuk text on path |
| 32 | Image adjustment dan creative tools | H | 10, 12, 22 |
| 33 | Print, template, batch export | H | 04, 14–16, 22 |
| 34 | HTML/CSS export | H | 26, 28; 27 jika mengekspor instances |
| 38 | Clipboard, in-place, guides, palette/preferences | H | 08–12, 22; pecah 38A/38B |
| 39 | Recovery manager, history dan snapshots | H | 03, 04, 14, 22; pecah 39A/39B |
| 40 | Dry-run AI dan analyze_design P1 | A | 18–20, 22; pecah 40A/40B |
| 41 | SVG export subset | H | 16, 22; 29/30 hanya untuk path/boolean yang diaktifkan |
| 42 | Diagnostic bundle dan audit aksesibilitas UI | M | 05, 20, 22; pecah 42A/42B |
| 35 | Prototyping | H | 22; 27 jika memakai component states |
| 36 | 36A Plugin API / 36B PDF import | A | 22; keduanya independen kecuali PDF dijadikan plugin |
| 37 | Raster, aksesibilitas desain, codegen, AI UI | A | 37A: 12/32; 37B: 40B; 37C: 34; 37D: 19/20/40A |

Jalur cepat developer handoff: **22 → 26 → 28 → 34**. Component instances menambah prasyarat 27 jika dipakai. Jalur vektor **29 → 30** tidak menghalangi handoff. Untuk segmen 37 juga wajib MVP 22 verified. Setelah tiap fitur P1/P2, ulangi build/release checks yang terdampak sebelum mendistribusikan versi baru.

### Pemetaan hasil review ke implementasi

PRD 1.1 adalah kontrak terbaru; dokumen review merupakan catatan evaluasi historis. Matriks berikut melacak penutupan temuan melalui implementasi nanti, bukan menyatakan fitur sudah selesai.

| Temuan review | Acuan PRD | Pemilik segmen utama |
| --- | --- | --- |
| R-01 ownership dan sesi | FR-027, 20.1, AT-21/22/26 | 00, 04/04A, 05, 14, 19B |
| R-02 geometri/rendering | 20.2, AT-24/27 | 00, 02, 06/06A, 08, 13 |
| R-03 kelengkapan operasi MCP | 7.3, FR-024 | 18A–18C, 19A |
| R-04 transaksi/retry/history | FR-028, 20.3, AT-23/25 | 03, 04, 14, 18B, 19B |
| R-05 pembuktian awal | 20.5 | 01A, 04A, 06A, 17A; baseline 08/12/19B |
| R-06 prioritas selaras | FR-015/018/019, 6.1, 7.3 | 00, 10A/B, 16, 18A/B, 21, 40B |
| R-07 dependensi/subsegmen | 12 dan roadmap ini | 10A/B, 18A/B/C, 19A/B, jalur P1 |
| R-08 inspection terbatas | FR-029, 7.4, AT-28 | 17, 18A/C, 19A |
| R-09 kualitas terukur | 20.5, AT-29/30 | 01, 06A, 22, 23, 24/25 |
| Produktivitas tambahan | FR-030–FR-033 | dasar 05/08; P1 38–42 |

Tambahkan verifikasi spesifik P1 ke requirements matrix: 38 clipboard/in-place/guides/preferences, 39 relink/restore/history/snapshots, 40 preview tanpa side effect/analysis, 41 SVG viewer independen, 42 redaksi diagnostics dan audit keyboard/screen reader. Fitur P1 yang masuk rilis tidak boleh dinyatakan verified hanya karena P0 lulus.

## Fondasi dan editor inti

### 00 — Keputusan arsitektur dan matriks kebutuhan

Model: **A**. Referensi: PRD bagian 8, 9, 12, 13, 16.

```text
Kerjakan segmen 00: periksa isi repository dan susun fondasi keputusan teknis tanpa membangun seluruh aplikasi.
Buat docs/architecture.md dan ADR singkat untuk batas modul, skema ID/hierarchy, kontrak geometri PRD 20.2, single writer dan session identity PRD 20.1, rendering bersama, batas konten/state sesi/job, retry/asset retention, lifecycle dokumen, attached/headless MCP dan strategi thread/IPC. Jangan meninggalkan keputusan ownership/pivot/group opacity sampai implementasi renderer.
Putuskan nama package Python yang valid (default ltechdesign), entry point, serta alasan pemilihan dataclasses atau Pydantic. Gunakan .ltechdesign dan kontrak docs/ltechdesign-file-format.md; resource pydesign:// tetap internal. Aplikasi single-user lokal tanpa collaboration; IPC/lock untuk GUI dan MCP pengguna yang sama.
Buat docs/requirements-matrix.md yang memetakan FR-001–FR-033, NFR-001–NFR-005, AT-01–AT-34, kontrak PRD bagian 20, import/export dan deliverable ke ID segmen/subsegmen serta status aktual. PDF multipage dasar dan token store minimum adalah P0; UI design system P1. analyze_design diagnostik P1 masuk 40B, audit aksesibilitas desain P2 masuk 37B. HTTP opsional default-off dapat not_included. Bedakan gate MVP, selesai lingkup fitur dan siap rilis.
Buat docs/progress.md dengan urutan roadmap dan keputusan yang masih terbuka. Jangan menandai kebutuhan terpenuhi hanya karena sudah didokumentasikan.
Selesai jika kontrak inti konsisten, seluruh kebutuhan memiliki pemilik segmen, dan tidak ada keputusan thread, revision, atau persistence yang diserahkan tanpa rencana.
```

### 01 — Setup proyek Python

Model: **M**. Referensi: PRD 8.1, 8.4, NFR-004.

```text
Kerjakan segmen 01: buat struktur src package, pyproject.toml, environment development lokal, .gitignore, logging dasar, entry point desktop dan CLI yang terpisah, serta konfigurasi pytest, pytest-qt, lint dan type check yang realistis. Pilih satu alur dependency yang terdokumentasi dan dapat direproduksi.
Siapkan CI Windows untuk pemeriksaan yang sudah bisa berjalan. Tambahkan README berisi perintah PowerShell setup, test, lint, dan menjalankan aplikasi. Jangan menambahkan modul kosong untuk seluruh fitur atau mengimplementasikan canvas sekarang.
Tambahkan scripts/check.ps1 dengan mode pemeriksaan subsistem dan exit code yang benar, scripts/run.ps1, serta generator fixture deterministik yang dilengkapi sesuai subsistem tersedia. Catat hardware/OS/display scale/dependency untuk baseline. Siapkan font uji dengan izin distribusi jelas dan direktori fixture schema/migration/visual. CI tidak mengklaim inspeksi GUI yang tidak dilakukan.
Selesai jika package dapat diinstal, entry point dapat dijalankan, smoke test dasar lulus, dan dependency yang diuji tercatat. Jika dependency tidak dapat diunduh, laporkan hasil aktual dan perintah yang belum berhasil.
```

### 01A — Spike executable minimal

Model: **H**. Wajib setelah 01 sebelum memperluas fondasi. Referensi: PRD 20.5.

```text
Kerjakan hanya 01A: gunakan dependency setup segmen 01 untuk membangun executable Windows minimal yang menampilkan window Qt berjudul ltechDesign Studio, lalu dapat ditutup dengan bersih. Pilih tool packaging awal dan catat perintah/versi/plugin yang diperlukan sebagai ADR; tidak perlu installer atau UI editor lengkap.
Jalankan artifact aktual dan catat bukti startup/shutdown. Bedakan keberhasilan pada mesin development dari uji Windows bersih yang masih syarat rilis. Simpan smoke-build script yang akan digunakan ulang pada 24. Jangan menandai verified dari file spec saja; jika build tidak dapat dijalankan, catat blocker konkret sebelum memperluas UI.
```

### 02 — Domain model dan schema

Model: **H**. Referensi: FR-002, FR-004, FR-006, PRD 9.

```text
Kerjakan segmen 02: implementasikan model project, document, page, artboard/frame, rectangle, ellipse, line, polygon, text, image, SVG, group, style, referensi aset dan metadata font tanpa import Qt.
Tetapkan schema_version, revision, ID stabil, parent/children yang konsisten, properti bertipe dan nilai default. Validasi angka finite, dimensi, warna, ID duplikat, node hilang, siklus, parent salah, dan urutan root. Definisikan kebijakan unknown properties serta migration registry untuk versi berikutnya.
Bekukan schema sesuai PRD 20.2: root_ids, pivot lokal, positive uniform scale, transform order, clip_content dan geometry/visual/hit-test bounds. P0 tidak mendukung flip/shear/nonuniform group resize. Tangani line dengan extent nol pada satu sumbu. Session ID runtime terpisah dari file schema. Fixture JSON final menggantikan contoh PRD yang ilustratif dan harus mempertahankan backward compatibility yang diklaim.
Lengkapi JSON schema/typed validators format docs/ltechdesign-file-format.md untuk manifest, document, tokens, fonts, assets index dan workspace; tentukan payload data per node serta unit typography sebelum writer dibuat. Format contoh menggunakan data.text/data.typography, font IDs dan property-path token bindings; jika kontrak dibetulkan saat freeze, perbarui generator/contoh/spec bersama, bukan membiarkan fixture menyimpang. Unsupported required capability harus ditolak tanpa silent data loss.
Implementasikan JSON round-trip dan fixture dokumen bertingkat. Uji round-trip mempertahankan makna, transform relatif, validasi dokumen rusak, dan penolakan versi yang belum didukung dengan error terstruktur.
Selesai jika model bisa digunakan tanpa GUI dan semua invariants memiliki tes perilaku.
```

### 03 — Command engine dan transaksi

Model: **A**. Referensi: FR-025, PRD 8.2–8.3, AT-06, AT-14–AT-15.

```text
Kerjakan segmen 03: implementasikan satu dispatcher untuk create/update/delete, move/reparent/reorder, group/ungroup, duplicate, dan perubahan style/text. Tambahkan undo/redo per dokumen, event perubahan, dirty state, expected_revision, dan error terstruktur.
Definisikan revision sebagai counter monoton termasuk undo/redo; tentukan satu kenaikan per transaksi berhasil. Batch harus tervalidasi dan atomik, termasuk pemulihan state dan history jika satu operasi gagal. Emit event hanya setelah commit. Tentukan clean/save checkpoint terpisah dari revision dan cara satu drag menjadi satu undo entry.
Terapkan batas PRD 20.3: selection/viewport bukan history konten, save/export bukan batch atomik, layout bagian commit yang sama. Buat staging/retention contract aset dan history metadata nama aksi/sumber GUI-AI. Implementasikan history memory budget, cleanup aman dan deduplication request dengan digest payload, retensi minimum serta error request_id_conflict/capacity. Uji retry sukses sebelum stale-revision check dan jelaskan batas restart, bukan mengklaim exactly-once tanpa journal.
Uji rollback pada kegagalan di tengah batch, redo invalidation, stale revision, delete subtree, duplicate dengan remapping ID, dan undo yang mengembalikan hierarchy/style. Jangan memakai mutasi QGraphicsItem sebagai sumber data.
Selesai jika semua perubahan domain melewati jalur yang sama dan transaksi gagal tidak menyisakan perubahan atau event sukses.
```

### 04 — Penyimpanan .ltechdesign dan asset store

Model: **H**. Referensi: FR-002, NFR-002–003, AT-05, AT-18.

```text
Kerjakan segmen 04: implementasikan writer/reader .ltechdesign sesuai docs/ltechdesign-file-format.md: manifest.json, document.json, assets/index.json, assets/data/, tokens.json, fonts.json dan workspace.json/thumbnails opsional. Contoh examples/proyek-contoh.ltechdesign dan scripts/New-LtechDesignExample.ps1 adalah fixture format, bukan loader produksi; jangan mengganti persistence aplikasi dengan generator contoh.
Validasi format_id, versi/capabilities, file inventory, SHA-256/ukuran, JSON schema dan referensi lintas dokumen. Embedded assets wajib untuk native project; fonts mengikuti aturan resolusi manifest. Simpan data fitur yang sudah tersedia, termasuk layout/tokens dan extension yang didukung; jangan flatten atau membuang unknown required capability diam-diam. Runtime session/undo/job/lock tidak ikut file.
Gunakan atomic save dengan temporary file di filesystem tujuan dan replace. Validasi sebelum mengganti file lama; siapkan mekanisme backup sebelum migrasi. Tangani ZIP rusak, path traversal, anggota duplikat, ukuran ekstraksi berlebihan, aset hilang dan versi tak didukung secara terkendali. Thumbnail boleh belum dirender sampai segmen renderer tersedia; catat integrasinya.
Implementasikan PRD 20.1: canonical path, lock satu writer, read-only open, stale-lock check, fingerprint baseline dan conflict-on-save. Save As memegang lock sumber sampai target berhasil, Duplicate Project punya document ID baru. Jangan melakukan overwrite jika file berubah eksternal. Hormati limit archive/asset PRD 20.4 dan pertahankan aset yang diperlukan undo/recovery/jobs saat cleanup.
Uji round-trip termasuk nested nodes dan byte aset, kegagalan save yang mempertahankan file lama, serta file malformed. Selesai jika tidak bergantung pada working directory atau instalasi aplikasi.
Uji AT-31–AT-34 fondasi: semantic round-trip termasuk token bindings, byte aset, dua page dan object editable; pindahkan satu file lalu hapus sumber aset dan muat offline. Rusak hash/manifest dan cek tab/model lama tetap utuh. Fixture fitur lanjutan ditambahkan pada segmennya; belum boleh mengklaim UI restore sampai 05/14/22.
```

### 04A — Bukti ownership dua proses

Model: **H**. Referensi: FR-027, AT-21–AT-22, AT-26.

```text
Kerjakan hanya 04A: jalankan dua proses persistence yang benar-benar membuka file .ltechdesign sama. Buktikan writer kedua ditolak/read-only, lock dilepas saat close dan stale lock setelah crash ditangani tanpa mengambil alih writer aktif.
Uji file diganti proses eksternal setelah open, Save As gagal/sukses, source lock lifecycle dan dua salinan dengan document_id sama. Baseline conflict harus mencegah overwrite diam-diam. Gunakan adapter/service nyata, tanpa GUI lengkap dan tanpa MCP server penuh. Simpan command reproduksi dan hasil sebagai AT-21/22/26 fondasi; pengujian integrasi GUI/MCP tetap di 19B/22.
```

### 05 — Main window dan sesi dokumen

Model: **M**. Referensi: FR-001, PRD 10.

```text
Kerjakan segmen 05: buat QMainWindow dengan menu, toolbar tool dasar, panel Pages/Layers, Inspector, status bar, area canvas dan tab dokumen. Hubungkan New/Open/Save/Save As/Close ke domain dan persistence. Kelola selection, history, dirty state dan path per dokumen.
Tambahkan dialog unsaved changes, nama proyek dan status penyimpanan. Area yang belum berfungsi harus jelas dinonaktifkan, tanpa tombol yang memberi kesan fitur sudah tersedia. Gunakan layout Qt yang dapat di-resize dan tampil wajar pada skala Windows berbeda.
Tambahkan Import Project (.ltechdesign) sebagai jalur loader yang sama dengan Open Project: buka tab dokumen lengkap dengan unsaved-change handling, bukan satu gambar flatten atau merge layer. Ikuti staging/validation dan ownership sumber. Uji file invalid tidak mengganti state dokumen aktif.
Tampilkan read-only/ownership/external-change conflict dan Reload/Save As yang aman. Kelola session_id unik per dokumen terbuka termasuk dua file dengan document_id sama. Terapkan focus/tab order, label kontrol dan kontras dasar; uji High DPI 100/150/200% sesuai AT-27, dan jangan mengubah ukuran ekspor berdasarkan display scale.
Verifikasi dua tab memiliki state/history terpisah, cancel close tidak kehilangan edit, dan save error ditampilkan. Selesai jika aplikasi nyata dapat membuka lalu menyimpan proyek dengan UI yang responsif.
```

### 06 — Renderer dasar dan navigasi canvas

Model: **H**. Referensi: FR-003, PRD 8, AT-20.

```text
Kerjakan segmen 06: implementasikan rendering adapter domain ke QGraphicsScene/QGraphicsView dan shared drawing primitives yang bisa dipakai preview/ekspor. Render shape, frame, group dan style dasar beserta hierarchy transform, z-order, visibility, opacity dan clipping. Text/image akan dilengkapi di segmen khusus.
Tambahkan pan, Ctrl+wheel zoom berjangkar kursor, zoom control, fit artboard dan zoom selection dengan batas zoom yang aman. Pisahkan overlay selection/grid dari konten dokumen agar tidak ikut ekspor.
Uji transform nested dan urutan layer, lalu jalankan demo visual fixture. Selesai jika update domain memperbarui item tanpa rebuild seluruh scene pada setiap edit dan navigasi tidak mengubah data dokumen.
Terapkan kontrak PRD 20.2 termasuk group opacity isolated compositing, bounds terpisah dan rounded clip; jangan mengandalkan default QGraphicsItem yang berbeda semantiknya. Fixture harus memuat overlap anak dalam group transparan. Sesudah ini jalankan 06A sebelum tool drawing diperluas.
```

### 06A — Spike shared renderer dan headless

Model: **H**. Referensi: PRD 20.2, 20.5.

```text
Kerjakan hanya 06A: gunakan satu fixture kecil nested rotation, rounded clipping, group opacity dengan overlap dan primitive text untuk membuktikan shared drawing di canvas, PNG, PDF dan QGuiApplication/offscreen. Jangan membuat pipeline renderer kedua atau UI export lengkap; API service awal dikembangkan lanjut pada 15–17.
Render artifact nyata, bandingkan geometri/alpha/font layout, periksa PDF fallback raster bila diperlukan dan catat keterbatasan. Text primitive awal tidak perlu inline editing yang baru datang di 11. Ulangi smoke-build 01A jika plugin/dependency renderer berubah. Selesai jika pendekatan renderer terbukti, mismatch penting diperbaiki dan tidak disembunyikan dengan toleransi berlebihan.
```

### 07 — Artboard, drawing dan selection

Model: **H**. Referensi: FR-004, FR-006, AT-01–AT-02.

```text
Kerjakan segmen 07: buat preset artboard PRD dan custom width/height/unit/DPI, serta tool frame, rectangle, ellipse, line dan polygon. Hubungkan gesture drawing ke command create node dengan preview sementara yang tidak mencemari history.
Tambahkan hit-testing, click selection, modifier multiselect, marquee, bounding box dan select all. Hormati layer hidden/locked dan coordinate space parent ketika zoom/pan aktif. Tool text/image cukup dihubungkan saat segmen 11/12, bukan dibuat dummy.
Uji artboard 1080x1350, ukuran objek pada beberapa zoom, nested frame, pembatalan gesture, dan satu aksi drawing menghasilkan satu undo entry. Selesai jika objek dapat dibuat, dipilih, disimpan dan dibuka kembali dengan posisi sama.
```

### 08 — Transform, clipboard dan grouping

Model: **H**. Referensi: FR-003, FR-005, AT-03–AT-06.

```text
Kerjakan segmen 08: implementasikan drag/move, resize handles, rotate, delete, duplicate, cut/copy/paste, group/ungroup serta context menu. Tentukan perilaku multiselect, transform parent berotasi, aspect ratio dan keyboard modifier secara konsisten.
Gunakan transaksi tunggal per gesture; Escape membatalkan preview. Clipboard memakai data terstruktur tervalidasi dengan ID baru dan referensi aset yang benar. Group/ungroup dan reparent mempertahankan posisi visual dunia ketika semestinya.
Terapkan positive uniform group resize dan frame resize berbasis layout sesuai PRD 20.2. Tambahkan nudge 1 px, Shift+panah 10 px, bring forward/send backward dan shortcut aman saat text editing. Uji AT-24 serta baseline ringan 100/1.000 shape PRD 20.5; simpan p95/p99/freeze sebagai pembanding, jangan menunggu segmen 23.
Uji transform nested, undo/redo setelah drag dan delete subtree, paste antar dokumen, redo setelah command baru, dan shortcut yang tidak mengambil alih input teks. Selesai jika hierarchy dan history tetap konsisten setelah rangkaian edit.
```

### 09 — Pages dan Layers

Model: **M**. Referensi: FR-001, FR-005.

```text
Kerjakan segmen 09: implementasikan create/rename/duplicate/delete page, artboard list, layer tree bertingkat, pencarian nama/tipe, rename, duplicate, hide/show, lock/unlock dan drag-and-drop reorder/reparent melalui commands.
Sinkronkan selection canvas dan tree dua arah tanpa event loop berulang. Reorder memperbarui z-order, pindah parent memvalidasi siklus, dan perubahan page mengelola selection yang sudah tidak relevan. Tindakan perubahan struktur harus bisa di-undo.
Uji nested layer drag, selection dua arah, page duplication dengan ID/aset benar, hidden/locked node serta pencarian. Selesai jika tree mencerminkan domain, termasuk perubahan yang berasal dari command di luar panel.
```

### 10 — Inspector, styling dan alignment

Model: **H** untuk 10A dan 10B. Referensi: FR-003, FR-008, FR-018 dasar P0. Jalankan satu prompt per sesi.

#### 10A — Inspector dan style

```text
Kerjakan hanya 10A: hubungkan Inspector X/Y, width/height, rotation, opacity, fill, stroke center-aligned, radius dan basic shadow; X/Y mengikuti translasi parent PRD 20.2. Tambahkan color picker dan foreground/background. Mixed values pada multiselect harus jelas dan input tervalidasi.
Gabungkan edit interaktif secara wajar dalam undo history. Style harus masuk shared renderer, serialization dan export service yang sudah tersedia dari 06A. Inspector constraints/export lengkap menyusul segmennya. Uji nested transform, undo style dan group opacity; tidak membuat snapping sekarang. Selesai jika UI/domain/render sinkron dan bukti tersimpan.
```

#### 10B — Rulers, snapping dan alignment

```text
Kerjakan hanya 10B setelah 10A verified: tambahkan rulers, grid, grid/object snapping, smart guides, align/distribute dan toggle snap. Semua toleransi menggunakan satuan layar yang dipetakan benar pada zoom/DPI, sedangkan posisi konten tetap logical pixel. Guides manual P1 berada di 38B.
Uji objek dalam parent berotasi, multiselect, hidden/locked nodes, zoom berbeda dan skala layar. Alignment/reorder yang mengubah konten masuk command undo, visibility overlay sesi tidak mencemari history/ekspor. Selesai jika perilaku konsisten di canvas dan Inspector; tandai induk 10 verified hanya jika 10A serta 10B selesai.
```

### 11 — Text dan typography dasar

Model: **H**. Referensi: FR-009, FR-010 fallback, AT-02.

```text
Kerjakan segmen 11: buat tool text dan inline editing multiline; font family lokal, size, weight, italic, alignment, line height, letter spacing, warna, opacity, text box resize dan auto width/height.
Gunakan text layout/drawing bersama untuk canvas dan output. Definisikan satuan line height/letter spacing serta serialisasinya. Tangani Unicode, font fallback, warning font hilang dan emoji sesuai renderer; jangan menjanjikan tampilan emoji yang tidak didukung. Ctrl+C/V/X dan Delete ketika mengetik harus bekerja sebagai edit teks.
Uji wrapping, metrik, font hilang, Unicode, edit text undo/redo dan save/reopen. Selesai jika text dapat diedit lewat UI dan command dengan hasil layout yang konsisten.
```

### 12 — Image dan SVG

Model: **H**. Referensi: FR-011, import bagian 6.2.

```text
Kerjakan segmen 12: import PNG/JPEG/WebP dan subset SVG yang kompatibel melalui file dialog serta drag-and-drop. Tambahkan asset thumbnails, fit/fill/stretch, crop non-destructive, rounded clipping, opacity, rotation dan replace image tanpa mengubah container.
Gunakan asset store, batas dimensi/ukuran serta decoding yang terkendali. SVG harus tetap berupa aset vektor yang dirender bila didukung; node/path editable penuh bukan syarat tahap ini. Tolak atau sanitasi script dan external references; dokumentasikan batas subset.
Uji proyek tetap dapat dibuka setelah file asal dipindah, crop dan replace bisa di-undo, gambar malformed ditangani dan transform/clipping sama di shared renderer. Selesai jika semua asset reference portabel.
Terapkan limit decoded pixels/asset size PRD 20.4, asset retention AT-25, serta cancellation/staging impor berat. Ulangi baseline ringan setelah image rendering aktif dan smoke-build jika codec/plugin berubah. Clipboard image lintas aplikasi P1 baru dikerjakan di 38A, bukan dianggap selesai oleh clipboard node internal.
```

### 13 — Stack layout dan constraints MVP

Model: **H**. Referensi: FR-013 P0, FR-008 constraints.

```text
Kerjakan segmen 13: implementasikan stack horizontal/vertical dengan padding, gap, alignment serta fixed/hug/fill dasar, dan constraints sederhana terhadap parent saat frame di-resize. Definisikan batas kombinasi yang didukung serta penanganan ukuran tidak cukup dan dependensi siklik hug/fill.
Layout engine menghitung hasil secara deterministik tanpa bergantung pada QGraphicsScene; hasil perubahan layout harus mengikuti transaksi yang sama, bisa di-undo dan terserialisasi. Hubungkan kontrol Inspector dan recalculation setelah edit text, child atau parent.
Uji resize parent, nested stacks, text berubah, padding/gap dan undo. Selesai jika layout dasar berfungsi lewat commands dan GUI; fitur lanjutan tetap dicatat untuk segmen 28.
```

## Penyimpanan, ekspor dan MCP

### 14 — Project workflow dan recovery

Model: **H**. Referensi: FR-001, NFR-002, AT-17.

```text
Kerjakan segmen 14: lengkapi recent projects, duplicate project, multi-page/multi-artboard workflow, save checkpoint, thumbnail proyek dan metadata font. Implementasikan autosave configurable ke recovery area, termasuk dokumen belum bernama, tanpa menimpa file sumber secara tidak terduga.
Tawarkan restore/discard recovery saat startup dengan timestamp yang jelas, dan backup sebelum migrasi. Pastikan multi-tab, save manual, autosave dan close tidak saling menimpa snapshot baru; gunakan revision/snapshot yang tepat.
Integrasikan ownership/external-change policy, read-only dan session identity PRD 20.1, serta GC yang mempertahankan history/recovery AT-25. Autosave tidak boleh memaksa overwrite file eksternal. Session restore lengkap, named snapshots dan recovery manager lanjutan P1 berada di 39; autosave dan crash recovery dasar tetap wajib P0.
Uji recovery dengan proses aplikasi terpisah yang dihentikan terkontrol, kegagalan I/O, dokumen belum disimpan, dan file autosave rusak. Selesai jika skenario crash tidak kehilangan snapshot terakhir yang berhasil tersimpan dan restore bisa disimpan menjadi file normal.
Lengkapi workflow Save/Save As/Open/Import Project .ltechdesign dengan AT-31–AT-34: tutup aplikasi, pindahkan hanya file, hapus folder sumber aset, buka offline dan pastikan desain tetap editable. Missing-font warning mempertahankan metadata font; jangan mengklaim pixel-identical bila font tidak tersedia. Undo history lama tidak dipersist ke proyek normal, session ID baru saat reopen.
```

### 15 — Export PNG, JPG dan WebP

Model: **H**. Referensi: FR-020, AT-07–AT-09, AT-16.

```text
Kerjakan segmen 15: buat export service dan dialog untuk artboard, selected objects atau semua artboard ke PNG/JPG/WebP, menggunakan shared drawing. Sediakan scale 1x/2x/3x, dimensi custom, DPI, quality, transparent/solid background, output folder, naming, progress dan error report.
Flatten JPG dengan background pilihan. Periksa encoder WebP saat runtime dan gunakan Pillow fallback bila diperlukan. Definisikan selection bounds termasuk stroke/shadow serta clipping yang benar. Render dari snapshot konsisten; pekerjaan berat tidak memanipulasi scene dari worker thread.
Gunakan lifecycle job, progress/cancellation, temporary output dan limit megapixel PRD 20.4. Cancel setelah commit harus melaporkan output yang sudah terjadi, bukan mengklaim rollback. Save/export tidak dimasukkan ke batch mutasi node.
Uji file output benar-benar dapat didecode, dimensi/alpha sesuai, JPG tanpa alpha, WebP fallback dan kegagalan write terkendali. Selesai jika UI dan API service menghasilkan output yang sama tanpa overlay editor.
```

### 16 — Export PDF

Model: **H**. Referensi: FR-020, FR-019 sebagian, AT-10.

```text
Kerjakan segmen 16: implementasikan PDF single/multipage lewat Qt painting/PDF writer, termasuk artboard dengan ukuran berbeda, urutan halaman, unit fisik dan DPI raster yang terdokumentasi. Hubungkan dialog export.
Pertahankan text dan vector sejauh renderer mendukung, jelaskan fallback raster per fitur tanpa menjadikan seluruh PDF gambar secara diam-diam. Gunakan transform/clipping dan text layout bersama dengan canvas.
Uji jumlah serta ukuran halaman dengan pembaca PDF, periksa text/vector pada fixture yang mendukung, dan render hasil PDF untuk inspeksi visual terhadap preview. Selesai jika AT-10 terpenuhi walaupun fitur print lanjutan tetap P1.
```

### 17 — Preview dan headless renderer

Model: **H**. Referensi: FR-023, PRD 7.1, AT-20.

```text
Kerjakan segmen 17: sediakan render_preview dan CLI headless yang membuka proyek, menghasilkan preview serta mengekspor tanpa graphical editor terbuka. Jika renderer Qt memerlukan QGuiApplication/offscreen, inisialisasikan secara eksplisit dan dokumentasikan prasyaratnya.
Gunakan snapshot revision yang jelas; preview menyertakan metadata dimensions, document ID dan revision. Pastikan render worker tidak menyentuh QGraphicsScene milik GUI.
Lengkapi session ID, region/bounds, maximum dimensions, opaque artifact ID dan TTL preview PRD 20.4. Uji artifact expired, client capability transfer serta job cancel AT-29; jangan menganggap local path dapat dibaca client cloud.
Bandingkan canvas/offscreen/PNG/PDF pada fixture shape, nested transforms, clipping, shadow, image dan multiline text. Tetapkan toleransi visual dengan alasan, sertakan diff saat gagal, dan perbaiki mismatch bermakna. Selesai jika proses headless terpisah berhasil dan AT-20 memiliki bukti.
```

### 17A — Spike command subprocess ke GUI

Model: **A**. Referensi: PRD 20.5, 8.3. Wajib sebelum memperluas MCP.

```text
Kerjakan hanya 17A: buktikan bridge/IPC lokal yang akan dipakai attached mode dengan satu command create rectangle dari subprocess menuju dispatcher dokumen GUI. Kembalikan session ID, revision hasil commit dan node ID; perubahan harus terlihat di canvas, lalu dapat di-undo dari GUI.
Uji satu stale request, proses disconnect dan shutdown. Gunakan kontrak produksi yang kecil, bukan jalur mutasi bypass dispatcher atau server lengkap dengan semua tools. Catat thread ownership, transport, autentikasi lokal dan lifecycle sebagai ADR. Selesai jika spike lintas proses nyata berhasil dan bisa diperluas pada 19A.
```

### 18 — MCP headless melalui stdio

Model: **H** untuk 18A–18C. Referensi: FR-022–FR-029, PRD 7.3–7.4, 20.3–20.4. Induk selesai setelah ketiga subsegmen terverifikasi. Satu subsegmen per sesi; jangan mengklaim tools yang belum ada sebagai implemented.

#### 18A — Discovery dan bounded read

```text
Kerjakan hanya 18A: gunakan official MCP Python SDK dan catat versi protokol/SDK yang diuji. Buat stdio server; stdout hanya protokol, logs ke stderr/file. Definisikan input/output/error contracts dan examples untuk seluruh tools PRD 7.3, termasuk operasi batch bertipe dan job tools, tetapi daftarkan hanya tool yang sudah bekerja.
Implementasikan get_app_status, open_project, list_documents, get_document_info, get_document_tree, get_node, get_selection, list_assets dan get_design_tokens. Opening menaati single writer/read-only. Query tree punya page/subtree/name/type/depth/fields, limit dan cursor terikat session/revision/query; uji stale_cursor AT-28. Buat resource pydesign:// dan session templates dengan invalidation revision; selection headless unavailable dinyatakan eksplisit.
Token store minimum bertipe, ID stabil dan serialization sudah ada; UI binding/tema lengkap tetap 26. Terapkan path allowlist dan payload limit sejak awal. Uji client MCP subprocess nyata initialize, discovery, read, resource templates, dua dokumen dengan ID sama dan error. Selesai jika discovery/read berfungsi tanpa JSON besar tak terbatas.
```

#### 18B — Mutation, pages, assets dan batch

```text
Kerjakan hanya 18B setelah 18A: implementasikan create_project, create_artboard, create_node, update_node, delete_node, set_text, set_style, move_node, set_design_token, create_page, update_page, delete_page, import_asset, group_nodes, ungroup_nodes, reorder_nodes dan batch_operations sesuai kontrak PRD 7.3.
Gunakan dispatcher yang sama, session_id/expected_revision/request_id dan deduplication PRD 20.3. Batch typed operations wajib mencakup page/group/reorder/import staging; save/export/job/session state dilarang masuk batch konten. Import mandiri mendaftarkan aset secara transaksi; kegagalan membersihkan staging. Terapkan file ownership dan path/payload/asset/batch limits.
Uji create/edit/delete/reparent, grouping visual, page operations, import+create atomik, batch gagal, stale revision, retry sukses tidak terduplikasi, request_id_conflict, retention capacity dan cleanup aset yang masih diperlukan undo. Selesai jika AT-14/15/23/25 jalur headless mempunyai bukti, tanpa stub.
```

#### 18C — Preview, save, export dan jobs

```text
Kerjakan hanya 18C setelah 18B: hubungkan render_preview, save_project, export_design, get_job_status dan cancel_job ke service nyata 14–17. Ikuti snapshot revision, progress, queue/backpressure, timeout dan cancellation PRD 20.4.
Sediakan artifact/resource transfer sesuai capabilities client, region/size bounds dan TTL; local path hanya untuk client yang memiliki akses. Uji preview expired, export empat format, read-only save conflict, job cancel sebelum/sesudah commit, malformed output path dan stdout tetap bersih.
Jalankan alur MCP subprocess lengkap create → import/group/edit → preview → save/reopen → export. Verifikasi daftar tools PRD termasuk semua tambahan 7.3/20.4 benar-benar tersedia; set_selection attached menyusul 19A dan tidak didaftarkan sebagai berhasil di headless. Induk 18 verified hanya setelah 18A–18C serta matriks tools lengkap pada mode yang didukung.
save_project/open_project memakai codec .ltechdesign yang sama dengan GUI dan bekerja offline; tidak ada codec/cloud project terpisah untuk MCP. Uji file hasil MCP dapat dibuka/diimpor lewat GUI dan sebaliknya pada integrasi 19/22.
```

### 19 — MCP attached dan sinkronisasi GUI

Model: **A** untuk 19A/19B. Referensi: PRD 7.1, 8.3, 20.1–20.4, AT-11–AT-15, AT-21–AT-26.

#### 19A — Bridge dan lifecycle

```text
Kerjakan hanya 19A: perluas bridge 17A untuk seluruh MCP service 18 tanpa salinan dokumen yang menyimpang. Dispatcher pemilik menerapkan request serial dan respons sukses setelah commit; GUI diubah hanya GUI thread. Hubungkan session registry, get/set_selection attached, status/start/stop/log MCP dan mode read-only.
MCP memilih attached saat file dimiliki GUI jika bridge tersedia; jika tidak, write ditolak/read-only, bukan memaksa membuka lock. Tangani timeout, disconnect, shutdown/cancellation, close tab saat request dan routing dua salinan document ID sama melalui session ID. Uji happy path serta lifecycle sebelum concurrency stress di 19B. Selesai jika AI edit langsung terlihat dan history GUI yang sama dapat undo.
```

#### 19B — Concurrency, retry dan ownership integration

```text
Kerjakan hanya 19B setelah 19A: uji GUI edit bersamaan dengan stale request AI, dua client pada sesi sama, batch rollback, respons hilang sesudah commit lalu retry, request_id sama dengan payload berbeda, close/reopen dan server restart. Terapkan deduplication sebelum revision rejection untuk request yang pernah sukses dan dokumentasikan batas retensi/restart.
Uji file ownership dua proses, external replacement, source/target lock Save As, read-only, document ID bersalin dan GC aset yang masih diperlukan undo/recovery. Verifikasi selection tidak mengubah content revision; save/export tidak masuk batch. Perbaiki bug yang terkonfirmasi, ulangi benchmark ringan PRD 20.5 setelah bridge aktif. Induk 19 verified jika 19A/19B lulus dengan bukti AT-21–AT-26 integrasi, tanpa klaim exactly-once lintas crash.
```

### 20 — Kontrol keamanan MCP

Model: **A**. Referensi: FR-026, NFR-003, AT-19.

```text
Kerjakan segmen 20: audit dan lengkapi boundary akses proyek, import aset, save/export, bridge IPC dan resources. Terapkan canonical path validation serta allowlist yang benar pada Windows termasuk .., alternate path spelling, symlink/junction dan UNC sesuai kebijakan; jangan hanya mengandalkan string prefix.
Tambahkan batas payload/aset, audit log tanpa membocorkan token, project permissions, MCP disable dan konfirmasi aplikasi untuk operasi destruktif sesuai PRD. Bedakan delete node yang bisa di-undo dari penghapusan file proyek. Akses di luar allowlist harus ditolak atau melalui approval UI eksplisit dengan scope terbatas. Jangan sediakan shell/database arbitrer.
Uji jalur penolakan, input malformed, revision conflict dan atomicity setelah request ditolak. Selesai jika pembatasan ditegakkan service layer dan tidak bisa dilewati melalui tool alternatif. HTTP khusus diselesaikan pada segmen 21.
```

### 21 — Streamable HTTP lokal, opsional

Model: **H**. Referensi: FR-022, FR-026.

```text
Kerjakan segmen 21 hanya jika transport HTTP lokal akan disertakan; stdio tetap transport utama. Gunakan transport Streamable HTTP official MCP SDK dan bagikan tool/dispatcher yang sama.
Bind default hanya 127.0.0.1, gunakan token autentikasi, validasi Host/Origin sesuai kebijakan client lokal, lifecycle session, payload limit dan stop/start UI. Simpan secret secara layak dan jangan menuliskannya ke log. Jangan membuka public tunnel atau mengasumsikan ChatGPT cloud dapat mengakses localhost.
Uji client lokal sah, token salah/hilang, Host/Origin terlarang, session disconnect dan shutdown. Selesai jika fitur default-off terdokumentasi dan tes boundary HTTP lulus. Jika ditunda, catat opsional/tidak disertakan tanpa menandainya terimplementasi.
```

## Verifikasi dan rilis MVP

### 22 — Acceptance MVP dan perbaikan integrasi

Model: **A**. Referensi: AT-01–AT-29 serta AT-31–AT-34, FR-017, FR-027–FR-029, definisi MVP. AT-30 gate rilis pada 24/25.

```text
Kerjakan segmen 22: audit matriks kebutuhan terhadap implementasi nyata dan jalankan AT-01–AT-29 serta AT-31–AT-34. Tambahkan integration tests yang belum ada, lalu perbaiki kegagalan dalam scope MVP tanpa memperluas ke P1/P2. Gunakan fixture lintas segmen, font uji dan schema lama, bukan membuat fixture berbeda yang menyembunyikan regresi.
Buat dua contoh proyek editable: poster 1080x1350 dan landing page desktop dengan artboard, shape, text dan gambar. Verifikasi create/edit manual, save/reopen, undo/redo, create/edit lewat MCP, preview, dan ekspor keempat format. Coba satu workflow melalui Codex sebagai client jika koneksi tersedia; jika tidak, bedakan tes MCP client otomatis dari verifikasi Codex yang masih pending.
Tuliskan bukti tiap AT di docs/acceptance-report.md: otomatis/manual, perintah/langkah, hasil, revision kode, artifact dan blocker. Jangan tandai MVP fungsional selesai jika P0/AT-01–AT-29 serta AT-31–AT-34 belum terpenuhi. AT-30 tetap pending sampai paket/lingkungan rilis diuji pada 24/25; tidak menghalangi fitur independen setelah MVP fungsional. Jangan menyamakan tes MCP otomatis dengan verifikasi Codex yang belum dilakukan.
```

### 23 — Kinerja dan stabilitas

Model: **H**. Referensi: NFR-001–004, PRD 14.

```text
Kerjakan segmen 23: buat benchmark startup, interaksi dokumen 1.000 objek, batch 100 command, memory saat buka/tutup proyek, dan ekspor besar. Ukur pada mesin aktual; catat hardware, versi, kondisi warm/cold dan metode pengukuran frame responsiveness.
Gunakan acuan, metode p95/p99/freeze, target waktu batch, response UI dan memory budget PRD 20.5. Bandingkan baseline yang sudah diambil setelah 08/12/19; ini pengukuran lengkap dan optimisasi, bukan eksperimen kinerja pertama. Uji payload/asset/render limits dan cancellation PRD 20.4 termasuk AT-29.
Profilkan sebelum mengoptimalkan. Perbaiki bottleneck dominan melalui caching, incremental scene update, dirty region atau pembagian pekerjaan tanpa mengubah semantik command. Uji cancellation, font/aset hilang, corrupt project dan shutdown saat autosave/export.
Bandingkan hasil dengan target 5 detik startup dan sekitar 60 FPS dokumen ringan; jangan mengklaim target tercapai dari perkiraan. Selesai jika regresi terkendali dan gap target memiliki bukti serta keputusan tindak lanjut yang jelas.
```

### 24 — Build dan installer Windows

Model: **H**. Referensi: NFR-005, PRD 17.

```text
Kerjakan segmen 24: lanjutkan tool packaging dan script smoke-build yang sudah dibuktikan di 01A/06A; ubah pilihan hanya jika ada bukti dan ADR. Buat build Windows x64 yang menyertakan Qt plugins, image codecs, fonts/resource yang boleh didistribusikan, dependency MCP dan entry point headless.
Buat installer dengan tool Windows yang tersedia dan script build reproducible. Konfigurasi/settings/recovery berada pada direktori pengguna, bukan folder instalasi. Sertakan metadata produk ltechDesign Studio, versi, third-party notices dan dokumentasi signing jika sertifikat belum tersedia.
Smoke-test paket hasil build: startup, open/save, recovery, PNG/JPG/WebP/PDF, stdio MCP dan offscreen render tanpa Python development. Verifikasi pada lingkungan bersih bila tersedia; jika belum, catat sebagai release blocker. Selesai jika artifact installer benar-benar terbentuk dan verifikasi paket dicatat, bukan hanya file konfigurasi build.
Pakai AT-30 untuk bukti lingkungan bersih dan AT-27 untuk display scale. Bila artifact terbentuk tetapi uji wajib belum dapat dilakukan, status implemented_pending_verification; jangan memblokir penyusunan docs atau fitur P1 independen dan jangan mengklaim siap rilis.
```

### 25 — Dokumentasi dan pemeriksaan rilis

Model: **M**; gunakan **A** jika audit menemukan masalah lintas modul.

```text
Kerjakan segmen 25: tulis user guide, developer setup, arsitektur terbaru, format file/schema migration, keyboard shortcuts, troubleshooting font/codec/recovery, MCP tool/resource reference dan contoh konfigurasi Codex sesuai paket yang benar-benar dibangun.
Sediakan contoh poster/web UI, perintah build/test dan release checklist. Jelaskan stdio, attached/headless, HTTP opsional serta batas konektivitas ChatGPT berdasarkan kemampuan client yang diverifikasi; jangan mengasumsikan localhost dapat diakses cloud.
Cocokkan dokumentasi dengan CLI, UI dan installer aktual. Jalankan pemeriksaan final yang relevan dan rangkum known issues. Pisahkan status MVP fungsional (P0 dan AT-01–AT-29 serta AT-31–AT-34) dari siap rilis (ditambah AT-30, artifact installer dan verifikasi Windows bersih). Catat release blocker konkret tanpa menandai rilis siap atau melarang pekerjaan fitur independen. Selesai jika panduan dapat dipakai tanpa konteks chat dan seluruh bukti docs diverifikasi; gate rilis tetap pending jika lingkungannya belum tersedia.
```

## Pengembangan lanjutan P1

Setiap segmen lanjutan mengikuti pembuka sesi, termasuk serialization, rendering, undo, export dan schema migration bila diperlukan. Jalankan tes regresi yang dipengaruhi. Ubah kontrak secara kompatibel dan perbarui MCP ketika fitur perlu dapat dikendalikan AI.

### 26 — Design tokens dan theme variables

Model: **H**. Referensi: FR-015.

```text
Kerjakan segmen 26 setelah MVP stabil: perluas token minimum MCP menjadi color, typography, spacing, radius dan shadow tokens dengan ID stabil, binding properti, theme variables dan UI pengelolaan. Tentukan resolusi alias, cegah siklus dan tetapkan fallback token hilang.
Uji update token memengaruhi seluruh node terikat, undo mengembalikan nilai/binding, save/reopen mempertahankan ID, dan ekspor menggunakan nilai tema aktif. Selesai jika MCP dan UI memakai token store yang sama serta dokumen lama tetap terbuka.
```

### 27 — Reusable components

Model: **A**. Referensi: FR-014.

```text
Kerjakan segmen 27: implementasikan master component, instances, override properti, propagasi update, detach dan library lokal. Definisikan identitas master/instance, referensi lintas dokumen/library, serta kebijakan master hilang dan siklus instance.
Tambahkan UI dan MCP create_component serta operasi instance yang diperlukan. Uji perubahan master tetap mempertahankan override, duplicate/remap ID benar, detach mempertahankan tampilan, undo atomik dan round-trip. Selesai jika instances bukan salinan statis yang kehilangan hubungan dengan master.
```

### 28 — Auto Layout lanjutan

Model: **H**. Referensi: FR-013 P1.

```text
Kerjakan segmen 28: kembangkan stack layout MVP untuk nested fixed/hug/fill, min/max, alignment dan constraints lebih lengkap sesuai batas yang didokumentasikan. Tetapkan penanganan overflow, transform dan text measurement secara deterministik.
Hubungkan Inspector dan tool apply_auto_layout. Uji resize parent, nested frame, text berubah, undo dan hasil headless. Jika 27 sudah tersedia, uji nested component instance juga; jika belum, catat integrasi tersebut sebagai pemilik bersama 27/28 dan jangan menghalangi exporter non-instance 34. Selesai jika layout yang tersedia identik untuk state sama di GUI/MCP/export dan ketergantungan ukuran siklik ditangani dengan error atau aturan resolusi yang jelas.
```

### 29 — Pen tool dan path editing

Model: **H**. Referensi: FR-007 sebagian.

```text
Kerjakan segmen 29: tambahkan schema path, Pen tool Bézier, open/closed paths, node selection, anchor/handle editing serta stroke cap/join/dash. Pakai path primitives bersama untuk canvas dan PDF.
Pisahkan gesture preview dari command commit dan sediakan undo yang masuk akal per edit. Uji transform nested, save/load path, cancel gesture, stroke rendering dan round-trip. Selesai jika path dapat dibuat dan diedit kembali tanpa flatten raster.
```

### 30 — Boolean, masking dan flattening

Model: **H**. Referensi: FR-007 lanjutan.

```text
Kerjakan segmen 30: implementasikan Union/Subtract/Intersect/Exclude, clipping masks dan path flattening di atas model path yang sudah ada. Definisikan fill rule, transform, hasil kosong dan kebijakan operasi terhadap node selain path.
Uji overlapping/rotated/self-intersecting paths, clipping bertingkat, undo yang mengembalikan sumber, serta hasil PNG/PDF. Selesai jika hasil merupakan objek domain editable yang tersimpan dan tidak bergantung pada state item Qt tersembunyi.
```

### 31 — Typography lanjutan

Model: **H**. Referensi: FR-010.

```text
Kerjakan hanya checkpoint yang saya pilih: 31A rich text spans/text styles/auto-fit atau 31B variable fonts/text on path. 31A membutuhkan 11/22; 31B juga membutuhkan 29 untuk path. Jika ID subsegmen belum dipilih, mulai 31A saja dan berhenti setelah checkpoint tersebut. Catat progress keduanya; induk 31 hanya verified jika keduanya selesai.
Tentukan model span, selection/editing, font fallback/substitution serta capabilities renderer untuk variable fonts dan text on path. Jangan mengekspos kontrol yang diam-diam diabaikan renderer. Uji campuran style Unicode, perubahan span, font hilang, undo, save/reopen dan kesamaan canvas/export. Selesai jika kedua checkpoint terverifikasi atau keterbatasan eksplisit masih dicatat sebagai belum selesai.
```

### 32 — Image adjustment dan creative tools

Model: **H**. Referensi: FR-012, FR-018.

```text
Kerjakan hanya checkpoint yang saya pilih: 32A adjustment raster atau 32B styling/creative UI. Jika belum dipilih, mulai 32A saja; jangan mengerjakan keduanya dalam satu sesi. Pada 32A tambahkan brightness/contrast, saturation, hue, blur, grayscale dan masking dasar secara non-destructive dengan sumber aset tetap utuh. Gunakan cache hasil berdasarkan asset+parameter.
Pada 32B tambahkan gradient linear/radial, eyedropper, blending modes dasar yang didukung, shape presets dan SVG/icon library dengan sumber serta lisensi tercatat. Background removal hanya plugin opsional tanpa layanan wajib. Uji alpha, urutan efek, undo, save/reopen, hasil shared renderer dan PDF fallback sesuai checkpoint aktif. Selesai induk jika kedua checkpoint mempunyai bukti; fitur belum didukung dicatat, bukan dibuat no-op.
```

### 33 — Print, templates dan batch export

Model: **H**. Referensi: FR-019, FR-021, FR-018 templates.

```text
Kerjakan hanya checkpoint yang saya pilih: 33A print/unit, 33B template lokal atau 33C preset/batch export. Jika belum dipilih, mulai 33A saja dan berhenti setelah itu. Pada 33A lengkapi mm/cm/inch, DPI, bleed dan safe margin di atas konversi dasar MVP; jangan mengganti definisi logical pixel.
Pada 33B template menghasilkan dokumen baru dengan ID/aset benar. Pada 33C batch menangani banyak artboard, naming collisions, progress, cancellation dan laporan error parsial tanpa merusak dokumen. Pertahankan PDF multipage yang sudah ada; CMYK/ICC/PDF-X tetap di luar scope.
Uji konversi unit, dimensi fisik PDF, duplikasi template dan batch dengan satu output gagal. Selesai jika semua checkpoint terverifikasi dan pengaturan bertahan setelah restart bila sesuai.
```

### 34 — Export HTML/CSS

Model: **H**. Referensi: PRD 6.3.

```text
Kerjakan segmen 34: ekspor HTML semantic sederhana, CSS, asset folder dan token CSS variables. Gunakan stack/constraints untuk layout responsif dasar; jelaskan fallback absolute positioning untuk komposisi bebas. Sertakan warning fitur yang tidak dapat direpresentasikan dengan baik.
Tambahkan tool export_html_css, UI serta contoh hasil. Escape text/attribute dan jangan memasukkan script dari data dokumen. Uji struktur, asset paths portabel, breakpoint dasar dan bandingkan hasil browser dengan referensi desain. Selesai jika output dapat dibuka lokal dan dinyatakan sebagai starting point frontend dengan batas kompatibilitas yang jelas.
```

## Produktivitas dan Dukungan P1 — pilih sesuai dependensi

Segmen 38–42 sengaja ditempatkan sebelum P2 dalam dokumen walaupun ID lebih besar. Seluruhnya opsional untuk kelulusan MVP; jika disertakan dalam suatu rilis, fitur itu memerlukan bukti verifikasi dan regression checks yang dipengaruhi. Pertahankan model/effort dari tabel.

### 38 — Clipboard, guides dan preferences

Model: **H**. Referensi: FR-030. Dua sesi terpisah.

#### 38A — Clipboard Windows dan in-place actions

```text
Kerjakan hanya 38A: tambahkan paste gambar dari clipboard Windows melalui MIME/image decoding tervalidasi dan asset store permanen. Tangani clipboard kosong/tidak didukung, ukuran berlebihan serta gambar transparan. Tambahkan duplicate-in-place dan paste-in-place untuk node terstruktur dengan ID baru dan satu undo entry.
Uji screenshot dari aplikasi lain, crop/replace, paste antar dokumen, save/reopen setelah clipboard/file sumber hilang dan undo setelah asset cleanup. Jangan mengganti node-copy yang sudah berfungsi atau bergantung pada temporary image yang tak tersimpan. Selesai jika kasus pengguna dan jalur penolakan terbukti.
```

#### 38B — Guides, command palette dan preferences

```text
Kerjakan hanya 38B; pecah lagi bila perlu: guides manual dengan posisi logical pixel, lock/hide dan snapping; guide definitions tersimpan per page dan perubahan posisi/lock masuk undo konten, visibility overlay adalah state sesi, guides tidak diekspor. Tambahkan command palette yang menggunakan registry aksi menu yang sama.
Tambahkan preferences tema, unit default dan shortcut configurable dengan persistensi per pengguna, conflict detection dan reset defaults. Autosave settings P0 tetap berfungsi. Uji DPI/zoom, guide save/reopen, palette focus/keyboard dan shortcut saat mengetik. Induk 38 verified setelah 38A/38B, bukan hanya kontrol UI tanpa wiring.
```

### 39 — Recovery manager, history dan snapshots

Model: **H**. Referensi: FR-031. Dua sesi terpisah.

#### 39A — Session restore dan missing dependencies

```text
Kerjakan hanya 39A: perluas recovery P0 dengan restore daftar tab/dokumen/session workspace setelah restart. Peroleh session ID baru dan ownership lock yang sah; file yang dimiliki proses lain tetap read-only/ditolak tanpa force takeover. Jangan menghidupkan kembali job lama seolah belum commit.
Buat missing font/asset manager: tunjukkan substitusi/error, relink aset dan pemilihan referensi yang diperbarui dengan undo serta geometry tetap. Uji sumber hilang, relink salah, restore campuran saved/unsaved/read-only dan portable save. Jangan menandai autosave P0 tertunda hanya karena manager P1 belum ada.
```

#### 39B — History panel dan named snapshots

```text
Kerjakan hanya 39B: tampilkan history berdasarkan metadata command yang sama, nama aksi, waktu serta sumber GUI/AI. Multi-step undo/redo harus memakai engine yang ada, menghormati history budget dan batas entry yang sudah di-evict.
Tambahkan named local snapshots dengan retensi dan quota disk configurable. Tentukan lokasi snapshot yang dapat dipindahkan bersama proyek, cara restore sebagai transaksi atau dokumen baru, serta cleanup yang mempertahankan aset history/recovery. Jangan memasukkan session IDs lama ke sesi baru. Uji snapshot sebelum edit AI besar, restore/save/reopen, quota penuh dan cleanup; snapshot pengguna tidak dihapus tanpa aturan/konfirmasi yang jelas. Induk 39 verified setelah kedua checkpoint.
```

### 40 — Preview batch AI dan analisis desain dasar

Model: **A**. Referensi: FR-032, PRD 7.3 analyze_design P1. Dua sesi independen setelah MVP.

#### 40A — Preview/dry-run sebelum apply

```text
Kerjakan hanya 40A: implementasikan preview_operations pada snapshot terisolasi menggunakan validator/commands/layout yang sama. Kembalikan diff ringkas, base session/revision, bounds/preview dan operasi kanonis yang akan diterapkan. Jangan mengubah konten live, history atau asset store permanen selama preview.
Tambahkan UI review/apply/cancel untuk batch besar. Apply memakai request_id dan expected_revision, memvalidasi payload yang dipreview dan menolak stale state dengan tawaran preview ulang. Tidak menahan GUI lock selama pengguna meninjau. Uji dry-run gagal, cancel, aset staging expired, perubahan GUI di antara preview/apply dan retry commit. Selesai jika preview tidak memiliki side effect permanen dan apply bisa di-undo sebagai satu transaksi.
```

#### 40B — analyze_design P1

```text
Kerjakan hanya 40B: implementasikan tool analyze_design dan panel laporan untuk overflow/bounds terhadap artboard atau frame clip, aset/font hilang dan token reference rusak. Gunakan bounded query/snapshot revision; hasil berisi node ID, severity, bukti dan saran, tanpa mutasi otomatis.
Jangan menyebut pemeriksaan ini audit aksesibilitas lengkap. Transparansi di luar frame non-clipping bisa disengaja; klasifikasikan warning berdasarkan konteks, bukan semua dianggap error. Uji fixture normal/bermasalah, broken references dan revision berubah. Kontrak laporan akan diperluas 37B untuk aksesibilitas desain; independen dari aksesibilitas UI editor 42B.
```

### 41 — Export SVG untuk subset vektor

Model: **H**. Referensi: FR-032. Path/boolean hanya wajib bila fiturnya sudah diaktifkan.

```text
Kerjakan segmen 41: tetapkan capability table lalu implementasikan SVG export untuk shape, text/image, transform, clipping dan path yang sudah didukung editor. Embed aset untuk portabilitas, escape konten dan jangan mengekspor script/external reference tak tepercaya.
Jelaskan batas font, stroke, shadow/group opacity serta fallback raster secara eksplisit; fitur yang tidak dapat dipertahankan harus menghasilkan warning, bukan hilang diam-diam. Uji beberapa artboard/selection, buka hasil dengan viewer independen dan bandingkan visual. 29/30 tidak wajib untuk shape-only exporter; ketika path/boolean tersedia, tambah tes dan capability sebelum menyatakan dukungan.
```

### 42 — Diagnostics dan audit aksesibilitas UI

Model: **M**; gunakan **H** untuk perbaikan GUI yang kompleks. Referensi: FR-030, FR-033.

#### 42A — Diagnostic bundle lokal

```text
Kerjakan hanya 42A: buat export diagnostic bundle lokal berisi versi aplikasi/dependency, OS/display scale/capabilities dan log terpilih. Sediakan preview isi serta redaksi path/identitas. Jangan menyertakan secret, token MCP, konten desain atau aset secara default dan jangan upload otomatis.
Gunakan error terstruktur untuk menghubungkan laporan ke request/job tanpa membocorkan payload privat. Uji log yang sengaja berisi secret/path sensitif, bundle tanpa dokumen terbuka, write error dan cancellation. Perbarui troubleshooting guide; selesai jika artifact dapat diinspeksi dan tes redaksi lulus.
```

#### 42B — Audit aksesibilitas UI editor

```text
Kerjakan hanya 42B: audit keyboard navigation, focus/tab order, accessible names/roles, screen reader pada lingkungan yang tersedia, kontras dan indikator selain warna pada UI editor. Dasar focus/label/High DPI sudah P0; ini memperluas audit dan memperbaiki gap tanpa mengubah content model.
Uji workflow New → drawing/property edit → Save → Export lewat keyboard, palette bila 38B tersedia, serta skala Windows berbeda. Catat inspeksi screen reader yang belum benar-benar dilakukan sebagai pending. Ini berbeda dari analisis aksesibilitas dokumen 37B. Selesai setelah bukti dan perbaikan relevan tersedia; induk 42 memerlukan 42A/42B.
```

## Pengembangan P2 — setelah MVP dan prasyarat fitur terkait stabil

### 35 — Prototyping

Model: **H**. Referensi: FR-016.

```text
Kerjakan segmen 35: tambahkan interaction model click/navigation antarframe, hover states, simple transitions dan preview mode terpisah dari edit mode. Jangan menjalankan script pengguna.
Uji target frame dihapus, undo interaksi, save/reopen dan preview yang tidak memutasi desain sumber. Jelaskan static export tidak menyertakan semua perilaku prototipe. Selesai jika alur beberapa frame bisa dimainkan dan diedit ulang secara konsisten.
```

### 36 — Plugin API dan PDF import

Model: **A**. Referensi: PRD 12 Phase 5, 6.2. Jalankan 36A atau 36B sebagai sesi terpisah sesuai kebutuhan. Tidak ada dependensi wajib di antaranya kecuali PDF importer memang dijadikan plugin.

```text
Kerjakan hanya checkpoint 36A: desain dan implementasikan extension API berversi, registrasi plugin, enable/disable, lifecycle, capability permissions, error isolation dan contoh plugin lokal sederhana. Tetapkan threat model; jangan mengklaim Python plugin tersandbox jika masih menjalankan kode Python di proses tepercaya. Semua mutasi desain lewat command engine. Uji plugin gagal, API tak cocok dan disable tanpa merusak proyek. Selesai jika kontrak dan batas kepercayaannya dapat diverifikasi.
```

```text
Kerjakan hanya checkpoint 36B: implementasikan PDF import multipage sebagai preview/raster terlebih dahulu, dengan batas ukuran dan penanganan PDF rusak/terenkripsi. 36A hanya prasyarat jika importer sengaja dipaketkan sebagai plugin; selain itu gunakan service import yang sudah ada. Buat spike terpisah konversi PDF ke objek editable, catat library/lisensi dan fidelity teks/path/gambar. Implementasikan subset yang dinyatakan didukung; jangan mengklaim full PDF editing dari raster import. Uji dokumen beberapa halaman, ukuran, aset portabel dan undo import. Catat konversi editable sebagai belum selesai jika fidelity belum terverifikasi.
```

### 37 — Raster lanjutan, aksesibilitas, codegen dan AI UI

Model: **A**. Referensi: PRD 12 Phase 5. Empat prompt berikut dijalankan dalam sesi terpisah. PRD belum merinci fitur ini, sehingga masing-masing dimulai dari spesifikasi kecil yang dapat diuji.

```text
Kerjakan checkpoint 37A advanced raster editing: baca image pipeline, definisikan scope awal berupa brush/erase dengan edit yang bisa dibatalkan dan preservasi sumber. Catat keputusan ukuran tile/layer, memory budget dan format penyimpanan sebelum implementasi. Selesaikan satu vertical slice brush sampai save/reopen, undo dan export. Daftarkan fitur raster lain sebagai backlog, jangan menjanjikan pengganti Photoshop. Selesai jika slice memiliki tes serta demo nyata.
```

```text
Kerjakan checkpoint 37B accessibility inspection setelah 40B: perluas kontrak laporan analyze_design dengan kontras teks, ukuran teks dan metadata semantik yang dapat ditentukan dari model. Gunakan inspector yang sama dengan lokasi node, bukti perhitungan dan saran tanpa perubahan otomatis. Bedakan analisis desain statis dari jaminan aksesibilitas aplikasi hasil implementasi dan audit UI editor 42B. Uji fixture lulus/gagal dan transparansi/background bertumpuk. Selesai jika laporan dapat diulang dan batas analisis terdokumentasi.
```

```text
Kerjakan checkpoint 37C advanced code generation: pilih satu target output yang jelas di atas exporter HTML/CSS, tetapkan mapping komponen, tokens dan layout serta fidelity yang akan diuji. Implementasikan satu contoh alur lengkap dengan assets dan build output yang benar-benar dapat dijalankan. Jangan menambahkan beberapa framework sekaligus. Selesai jika proyek output bisa dibangun dan visual diverifikasi; target lain menjadi backlog.
```

```text
Kerjakan checkpoint 37D optional AI assistant UI: definisikan adapter provider yang dapat dinonaktifkan, credential storage, consent pengiriman konten, preview perubahan, cancellation dan eksekusi tool melalui command engine. Aplikasi utama tetap bisa dipakai offline tanpa API key. Jangan mengirim aset atau dokumen secara otomatis. Implementasikan satu provider hanya setelah dokumentasi integrasi diverifikasi dan credential tersedia; gunakan mock hanya untuk tes, bukan klaim integrasi nyata. Selesai jika alur prompt-preview-apply-undo diuji dan biaya/koneksi/error ditampilkan secara layak.
```

## Prompt bantuan antarsegmen

### Melanjutkan pada sesi baru

Gunakan model sesuai segmen yang dituju. Ganti `[ID]` dengan ID nyata.

```text
Lanjutkan pengembangan ltechDesign Studio pada segmen [ID] dari promt_managemnet.md. Terapkan Prompt pembuka sesi dari dokumen tersebut. Baca docs/progress.md, docs/architecture.md, requirements matrix, dan source yang relevan; cocokkan status dengan kode dan hasil tes aktual.
Jangan mengulang segmen yang sudah selesai. Jika ada sisa prasyarat yang menghalangi, selesaikan sisa itu dahulu dalam lingkup terbatas dan laporkan; jangan diam-diam memperluas fitur. Setelah prasyarat valid, kerjakan hanya segmen yang saya pilih sampai kriteria selesainya terpenuhi.
```

### Memperbaiki segmen yang gagal

Mulai dengan **H**; gunakan **A** untuk bug lintas subsistem. Sertakan ID dan error aktual.

```text
Perbaiki kegagalan segmen [ID] ltechDesign Studio. Terapkan Prompt pembuka sesi. Reproduksi error dari log/tes yang saya sertakan, telusuri penyebab pada source terkait, dan buat perbaikan terkecil yang memulihkan perilaku sesuai PRD.
Tambahkan regression test untuk penyebab yang ditemukan; jalankan tes tersebut dan pemeriksaan yang dipengaruhi. Jangan menghapus tes, menonaktifkan validasi atau mengurangi fitur agar status menjadi hijau. Perbarui progress dengan penyebab, solusi, hasil aktual dan pekerjaan tersisa. Jangan pindah ke segmen berikutnya sampai kriteria segmen ini terpenuhi.
```

### Review sebelum berpindah tahap

Model: **A**, atau **H** bila Astra tidak tersedia.

```text
Review tahap yang baru selesai pada ltechDesign Studio. Baca progress dan requirements matrix, lalu periksa implementasi dan bukti tes aktual untuk risiko: integritas hierarchy/aset, jalur mutasi di luar dispatcher, undo/redo, revision, atomic save, Qt thread safety, rendering/export mismatch dan path access.
Laporkan temuan dengan severity, lokasi file dan skenario reproduksi. Perbaiki bug yang terkonfirmasi dalam lingkup tahap aktif, jalankan tes terkait, dan perbarui status. Jangan mengembangkan fitur tahap berikutnya. Jika tidak ada temuan, sebutkan batas review dan verifikasi yang belum bisa dilakukan.
```

### Memecah segmen yang masih terlalu besar

Model: **H**.

```text
Pecah segmen [ID] menjadi beberapa subsegmen berurutan dengan satu hasil yang dapat diverifikasi per subsegmen. Pertahankan seluruh acceptance criteria asli dan sebutkan dependensi, file/modul utama, model/effort, tes, serta kontrak yang tidak boleh berubah.
Tulis prompt siap salin untuk tiap subsegmen ke promt_managemnet.md dan perbarui progress. Jangan menjalankan implementasinya pada permintaan pemecahan ini. Jangan menandai segmen induk selesai sampai seluruh subsegmen selesai.
```

## Titik pemeriksaan pengguna

- Setelah 08: coba membuat artboard, menggambar, transform, group dan undo.
- Setelah 14: buat komposisi dengan teks/gambar, simpan, buka lagi, dan coba recovery.
- Setelah 17: periksa PNG/JPG/WebP/PDF terhadap desain di canvas.
- Setelah 20: minta MCP membuat desain, edit manual, lalu undo perubahan AI.
- Setelah 22: AT-01–AT-29 serta AT-31–AT-34 dan P0 fungsional mempunyai bukti; P1 independen dapat dimulai. AT-30 masih gate rilis 24/25.
- Setelah 25: installer dan panduan dapat dipakai pada Windows tanpa environment development.
- Setelah 04/05/14/22: AT-31–AT-34 bertahap membuktikan restore native .ltechdesign; integritas contoh arsip saja belum memenuhi verifikasi aplikasi.
- Sesudah 01A/04A/06A/17A: bukti teknis awal dicatat; jangan menggantinya dengan rencana atau file konfigurasi saja.
- Sesudah 08/12/19B: bandingkan baseline kinerja ringan; optimisasi penuh tetap 23.
- Setelah fitur P1/P2: jalankan tes spesifik FR-030–FR-033 dan regression/release checks yang dipengaruhi sebelum distribusi.

Jika satu checkpoint gagal, jalankan prompt perbaikan pada segmen penyebabnya. Progres dihitung dari perilaku yang terverifikasi, bukan banyaknya file atau panjang jawaban model.
