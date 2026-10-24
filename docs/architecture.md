# Arsitektur ltechDesign Studio

Tanggal keputusan: 21 Oktober 2026 (Asia/Jakarta). Acuan: PRD 1.2, khususnya bagian 6–9, 11–13, 17 dan 20. Dokumen ini menetapkan kontrak implementasi, bukan bukti aplikasi telah bekerja. Status dan urutan implementasi ada di [progress.md](progress.md), pemilik kebutuhan di [requirements-matrix.md](requirements-matrix.md), alasan keputusan di [ADR](adr/README.md).

## 1. Baseline repository dan batas segmen 00

Baseline Git `54162c5` (`first commit`) hanya melacak `prd.md` dan `promt_managemnet.md`. Tidak ada AGENTS.md yang berlaku pada direktori workspace/ancestor yang diperiksa, source, pyproject, dependency lock, suite tes, atau scripts/check.ps1. Roadmap dibaca sebagai indeks pemilik pekerjaan; contoh prompt/desain bukan instruksi implementasi.

**B-001 selesai pada lingkup dokumentasi 00B:** atas permintaan pengguna, [spesifikasi format 1.0](ltechdesign-file-format.md) baru disusun dari PRD dan keputusan ini, bukan dipulihkan dari artefak historis. [ADR 0010](adr/0010-native-format-baseline.md) mencatat baseline dan contoh JSON yang diaudit. Native fixture `examples/proyek-contoh.ltechdesign` dan generator `scripts/New-LtechDesignExample.ps1` belum ada; pemiliknya 02/04, tidak lagi menjadi prasyarat dokumen 00. Segmen 00 tidak membangun aplikasi, schema validator produksi atau codec ZIP. Kesesuaian implementasi terhadap spesifikasi tetap harus dibuktikan 02/04/22.

Produk single-user lokal dan offline tanpa akun/AI berbayar wajib. GUI/MCP mengendalikan pekerjaan pengguna lokal yang sama. IPC, lock dan revision bukan collaboration. Tidak ada multiuser, sharing workspace, komentar tim, presence atau cloud sync. Pemindahan desain memakai file `.ltechdesign`. Namespace `pydesign://` hanya resource MCP internal.

Update 04 (23 Oktober 2026): `persistence` dan `assets` kini mengimplementasikan
ZIP produksi/byte admission, atomic save, lock/canonical path/fingerprint, Save As,
pure Duplicate Project dan retention adapter 03. Tidak menggunakan generator
fixture sebagai loader. [ADR 0014](adr/0014-native-persistence.md) dan
[baseline 04](baseline-segment04.md) menjadi delta terhadap backlog historis di
bawah: two-process spike masih 04A, lifecycle GUI 05, recovery disk 14, renderer
06/06A dan resolver fonts 11. Domain tetap bebas Qt. Layanan I/O terserialisasi
dipanggil worker/actor oleh integrasi berikutnya; tidak terhubung callback GUI saat ini.

## 2. Package, entry point dan dependency

Nama distribusi dan import package: `ltechdesign`, struktur `src/ltechdesign/`. Nama produk tampilan tetap **ltechDesign Studio**.

| Entry point yang akan dibuat di 01 | Target | Perilaku |
| --- | --- | --- |
| GUI script `ltechdesign` | `ltechdesign.main:main` | Desktop; tidak memakai stdout sebagai protokol |
| Console script `ltechdesign-cli` | `ltechdesign.cli:main` | Subcommand `gui`, `render`, `export`, `mcp` |
| `python -m ltechdesign` | `ltechdesign.__main__` → CLI | Jalur development yang sama; `mcp --mode attached` atau `headless` eksplisit |

Update segmen 01: GUI, CLI gui, dan python -m sudah dapat dijalankan; render/export/mcp belum didaftarkan sampai implementasinya tersedia. Headless tanpa editor masih dapat memerlukan QGuiApplication/offscreen untuk font dan rendering.

Python minimum 3.12; PySide6/Qt 6 dengan QGraphicsScene/QGraphicsView dan QPainter; Pillow untuk raster/fallback encoder; official MCP Python SDK untuk stdio. Pilihan domain **dataclasses `frozen=True, slots=True`**, koleksi immutable/copy-on-write dan validator eksplisit. Anotasi dataclass tidak memvalidasi tipe runtime, dan frozen tidak membekukan list/dict di dalamnya; boundary harus menolak input salah sebelum membentuk model. Tidak ada implicit coercion string ke angka. Pydantic yang diperlukan SDK boleh dipakai DTO adapter, tidak menjadi model konten kedua. Alasan: domain ringan, bebas Qt/transport, snapshot serta equality eksplisit; validator/schema telah ditulis dan diuji di 02, bersama tuple dan defensive-copy mapping proxy (ADR 0012). Lihat [dokumentasi dataclasses Python](https://docs.python.org/3.12/library/dataclasses.html).

Alur dependency: `uv` 0.12.1, `pyproject.toml` dan `uv.lock`, sync terkunci. Segmen 01 menguji Python 3.12.12 (dukungan saat ini dibatasi 3.12), PySide6/Qt 6.10.2 dan tool pengujian bersama; [baseline aktual](baseline-segment01.md) mencatat seluruh versi. Pillow/MCP SDK belum dipasang karena subsistemnya belum tersedia. Segmen 01A menguji PyInstaller 6.22.3 onedir/windowed dengan artifact native startup/shutdown; lihat [ADR 0011](adr/0011-windows-executable-spike.md) dan [bukti 01A](baseline-segment01a.md). Ini belum installer atau uji Windows bersih segmen 24.

## 3. Batas modul dan arah dependency

| Modul rencana | Ownership dan kontrak | Pemilik implementasi |
| --- | --- | --- |
| `domain` | Document, page, node, style, token, font/asset references, geometry, pure layout; tanpa import Qt, filesystem, MCP | 02, 13, 26–30 |
| `commands` | Typed command union, validation/planning, commit atomik, history, revision, deduplication; hanya jalur mutasi konten | 03 |
| `app` | DocumentSession registry, lifecycle, query service, job scheduler, orchestration; port persistence/render/security | 05, 14, 17–19 |
| `persistence` | Codec, migrations, staged load/save/recovery, canonical path, lock, baseline; tidak mengedit live model | 04, 04A, 14 |
| `assets` | Immutable blob store, staged imports, metadata, reference leases dan GC; tidak tergantung path asal | 04, 12 |
| `rendering` | Adapter Qt, shared traversal/primitives, text layout, bounds/clip/compositing, snapshot render plan | 06, 06A, 11, 12 |
| `ui` | QMainWindow, scene/view adapter, gestures, overlays, inspector; menerjemahkan intent ke commands | 05–13 |
| `exports` | Format/output policy dan job di atas shared renderer; raster/PDF, kemudian HTML/CSS/SVG | 15–17, 34, 41 |
| `mcp` | SDK schemas/tools/resources, stdio client context; menerjemahkan ke service milik sesi | 18A–18C |
| `ipc` | Versioned local bridge, authentication, framing, bounded queue, response correlation | 17A, 19A/19B |
| `platform` | Qt event-loop/lock adapters, Windows path identity, user settings/logging; implementasi port | 01, 04, 17A, 20, 24 |

Domain tidak mengimpor adapter. Commands bergantung domain dan port abstrak; application merangkainya. UI/MCP tidak menulis registry/node/Qt item sebagai data utama. Rendering/persistence/export mengonsumsi snapshot domain, bukan saling membaca state widget. SQLite hanya boleh cache/settings/history metadata; tidak diperlukan untuk restore proyek portabel. MVP tidak mewajibkan database.

## 4. Identitas, hierarchy dan token minimum

ID baru menggunakan UUID4 string kanonis lowercase tanpa semantik posisi/nama. Tipe Python terpisah untuk DocumentId, SessionId, PageId, NodeId, AssetId, TokenId, FontId dan JobId mencegah salah routing. ID persisten lama yang sah menurut spesifikasi dipertahankan, tidak ditulis ulang hanya agar menyerupai UUID. Format menerima ASCII ID 1–128 karakter menurut bagian 4 spesifikasi; page/node ID tidak bertabrakan, asset/token/font memakai registry bertipe terpisah. Implementasi validator/JSON Schema 02 tersedia; lihat baseline-segment02.md dan ADR 0012.

`document_id` persisten; `session_id` UUID baru setiap open/create/reload/recovery admission. `server_instance_id` UUID baru per proses server/owner. `revision` counter runtime monoton per sesi, awal 0 setelah admission, tidak menjadi urutan global lintas open. Format menyimpan checkpoint hanya sebagai `manifest.saved_revision`, informasional dari snapshot penyimpanan, bukan pemulihan identitas/counter sesi. `document.json` tidak memiliki field revision/session. Detail ditetapkan ADR 0010 dan diuji implementasinya 02/04.

Satu Document berisi page terurut dan registry node. Tiap page memiliki `root_ids` terurut. Node memiliki satu `parent_id` (null hanya untuk root), satu page pemilik, dan `children` terurut. Artboard P0 hanya root page; frame/group boleh nested; leaf tidak punya children. Root/children dari bawah ke atas menentukan paint/z-order, tanpa angka z lain. Setiap node muncul tepat sekali, semua references ada, relasi dua arah cocok, tidak ada cycle, orphan, duplicate ID atau lintas-page parent. Loader menolak kontradiksi; tidak memilih salah satu hierarchy diam-diam. Dispatcher satu-satunya penulis relasi.

Duplicate subtree/page memakai ID baru dan meremap semua referensi internal; referensi aset dalam dokumen yang sama boleh berbagi immutable blob. Duplicate Project memberi document/page/node/token/font/asset ID baru dan meremap binding/relasi; byte blob identik boleh dideduplikasi lewat SHA-256. Save As mempertahankan document ID dan ID isi, history sesi tetap miliknya. Dua salinan file dengan document ID sama tetap dua sesi/history/lock berbeda. Penutupan sesi membuat semua request/cursor lamanya invalid.

Token minimum P0: ID stabil, nama, discriminated typed value, registry dan operasi command read/write; serialization di 02/04, MCP di 18A/18B. Baseline format menetapkan color/number/string serta allowlist property-path bindings; typed validators/JSON Schema dibekukan 02. Nilai/path tidak dikenal tidak diterka. Binding yang ada di file harus dilestarikan/di-resolve sesuai capability, termasuk kesetaraan materialized value; fixture AT-31 wajib mencakup binding. UI binding/alias/themes dan token lengkap P1 di 26. Penghapusan token/aset/font yang masih dirujuk ditolak kecuali satu transaksi juga memperbaiki seluruh referensi. Missing font eksternal boleh unresolved dengan warning dan metadata asli utuh; missing embedded asset adalah kegagalan validasi file.

## 5. Geometri dan compositing (PRD 20.2)

Kontrak ini milik domain 02 dan commands 03/08; tidak ditunda sampai renderer.

- Unit internal logical pixel; x kanan, y bawah, sudut positif searah jarum jam. Semua angka finite; rotation dinormalisasi untuk perbandingan, scale uniform positif. P0 menolak shear/flip/negative scale/nonuniform group resize. Dimensi minimum tipe dibekukan 02; line memakai endpoints dan sah dengan satu extent nol. Gesture melewati nol di-clamp, bukan flip.
- Dengan vektor kolom, local transform `L = T(x,y) T(p) R(theta) S(s) T(-p)` dan world transform `W = W_parent L`. `x/y` translasi relatif parent, bukan minimum scene bounds. Pivot eksplisit di koordinat lokal, default pusat geometry saat create; line memakai titik tengah endpoints.
- Reparent menghitung `L_new = inverse(W_new_parent) W_old`. Transform P0 adalah similarity positif, sehingga komposisi/invers dapat direpresentasikan tepat oleh translation/rotation/uniform scale. Pilih pivot lokal eksplisit lalu pecahkan translasi dari matriks; jangan menyalin scene bounds ke x/y. Reject transform singular/tidak representable dan uji residual matriks, bukan approksimasi yang mengubah desain.
- Resize memilih anchor dalam koordinat parent. Geometry, pivot dan translasi diselesaikan bersama agar posisi dunia anchor tetap. Group resize mempertahankan rasio dan mengubah scale positif; geometry anak tidak ditulis ulang. Frame resize mengubah geometry lalu constraints/layout anak dalam transaksi yang sama. Layout tidak menulis hasil di luar commit.
- Geometry group berasal dari union geometry subtree dalam koordinat group, termasuk anak hidden agar show/hide tidak mengubah pivot; stroke/shadow dikecualikan dari geometry. Normalisasi origin sebesar `o` memakai `L_group_new = L_group_old T(o)` dan `L_child_new = T(-o) L_child_old`; pilih pivot pusat bounds baru dan pecahkan translasi yang ekuivalen. Maka `W_child` tetap. Empty group memakai bounds nol/pivot (0,0), resize berbasis handles ditolak sampai memiliki extent yang sah. Normalisasi setelah edit anak juga dalam transaksi yang sama.
- Grouping hanya siblings satu parent dalam P0: group baru pada posisi sibling teratas dari pilihan, urutan internal mengikuti urutan semula; sibling lain tidak diacak. Default opacity 1 dan clip false. Ungroup mengembalikan anak ke posisi group dengan urutan sama, memakai transform dunia. Grouping pilihan noncontiguous yang mengubah overlap dengan sibling lain harus diperingatkan/ditolak pada mode preserve-appearance; jangan diam-diam mengubah stacking.
- Reparent selalu mempertahankan world geometry. Perubahan ancestor clip/isolated opacity tidak selalu dapat direpresentasikan tanpa wrapper/flatten. Default operasi preserve-appearance menolak kasus yang tidak dapat dipertahankan (`unsupported_visual_preservation`) dengan alasan; tidak mengalikan opacity ke anak sebagai pengganti. Pengguna boleh memilih perubahan hierarchy yang memang mengubah konteks clip/compositing secara eksplisit. Ungroup group ber-opacity/clip nontrivial mengikuti aturan yang sama; batas ini dicatat dan diuji 08, bukan disembunyikan renderer.
- Geometry bounds untuk layout/resize; visual bounds mencakup stroke center-aligned, efek dan transform lalu intersection clip ancestors; hit-test bounds menambahkan toleransi layar yang dikonversi lewat zoom/DPR. Group visual bounds mencakup hasil komposit. Selection export memakai union visual bounds final dan tidak menyertakan overlay. Bounds kosong menghasilkan error ekspor yang jelas.
- `clip_content` default artboard true, frame/group false. Rounded frame memakai path radius sama untuk fill dan clip; radius dibatasi geometry. Opacity group diterapkan **sekali pada komposit terisolasi** setelah children dirender. Nested groups membentuk isolation nested. Overlap tidak boleh berubah menjadi alpha per anak. Leaf opacity/efek diisolasi saat diperlukan oleh drawing contract yang sama.
- Fallback isolation/shadow yang memerlukan raster memakai offscreen premultiplied alpha pada resolusi target, origin/padding dari visual bounds dan limit render. Canvas/preview/PDF memakai semantik yang sama; PDF melaporkan bagian yang diraster. Layar DPR hanya menentukan sampling UI, bukan ukuran dokumen/ekspor. Konversi fisik: `pixels = mm / 25.4 * DPI`, ukuran PDF point `pixels / DPI * 72`.

Tes 02/03 memeriksa matematika pivot, invariants, anchor dan rollback tanpa Qt; 06A membuktikan nested rotation, overlap alpha, rounded clip, multiline text, image transparan dan multi-artboard di canvas/PNG/PDF/offscreen. 08 membuktikan AT-24 dan undo seluruh hierarchy/transform. Nilai toleransi numerik/visual harus dibekukan dengan fixture 02/06A, tidak melonggarkan geometry/alpha untuk menutupi mismatch.

## 6. Content, state sesi dan side effect

Update 03: `commands.Dispatcher` kini mengimplementasikan typed operation union,
snapshot planning/publication, undo/redo dan post-commit events tanpa Qt. Kontrak
detail owner thread, request digest, memory charge, cancellation dan retention port
ada di [ADR 0013](adr/0013-command-dispatcher-runtime.md); bukti aktual di
[baseline 03](baseline-segment03.md). Layout evaluator 13, blob store 04, GUI dan
transport tetap tertunda. Low-level node Update bukan handler gesture/anchor resize.

| Kategori | Contoh | Revision/history | Jalur |
| --- | --- | --- | --- |
| Konten | Nodes/pages/style/text/layout/token, registered assets dan relasinya; guides manual P1 | Satu kenaikan per transaksi berhasil; undo/redo juga menaikkan revision | Dispatcher |
| State sesi | Selection, active page, pan/zoom, focus, tool, UI preferences | Tidak menaikkan content revision; bukan undo konten | Session service + event sesi |
| Job/side effect | Save/export/preview, load staging, decode/import staging, recovery write | Tidak menjadi command batch; melaporkan snapshot revision | Job service; hasil import baru masuk dispatcher saat commit |

Guide manual tersimpan per page, undoable sebagai konten P1 (38B), tapi overlay dan tidak diekspor. Preferences per pengguna bukan file konten. `workspace.json` opsional menyimpan view state yang diizinkan, bukan selection authority, client identity, session ID, job atau secret.

Dispatcher menerima envelope intent → validasi strict → dedup lookup → revision check → rencana pada snapshot → validasi invariants/layout → atomic publish model/history/assets → revision +1 → event post-commit. Deduplikasi harus sebelum stale revision untuk retry sukses. Gagal tidak mengubah model/history/revision/aset terdaftar dan tidak mengirim event sukses. Commit no-op yang valid tetap transaksi/revision tunggal; state sesi tidak disamarkan sebagai command no-op.

Gesture memakai preview ephemeral; release mengirim satu command/undo entry dengan base revision. Konflik dengan MCP membatalkan/rebase preview secara eksplisit, tidak overwrite edit baru. Undo/redo menyimpan aksi, sumber GUI/AI, timestamp, request ID dan reference leases. Redo branch dibuang setelah edit baru. Dirty state memakai semantic content checkpoint, bukan `revision == saved_revision`: undo ke konten tersimpan dapat clean meskipun revision meningkat. Save snapshot R yang selesai saat live R+1 tidak menandai live clean.

## 7. Retry, history dan asset retention

Mutasi dokumen MCP: `session_id`, `expected_revision`, `request_id` wajib. Scope dedup `(authenticated_client_id, session_id, request_id)` di owner dispatcher, tidak di proxy stdio. Identitas client berupa credential bridge lokal stabil selama owner hidup, tidak berubah hanya karena socket reconnect; dua client berbeda tidak berbagi scope. Payload digest dari typed canonical JSON (key terurut, default ternormalisasi, finite number representation, termasuk operation/target/expected_revision; transport correlation ID dikecualikan).

Payload sama mengembalikan hasil/error final lama; payload berbeda `request_id_conflict`; request sama in-flight join satu future. Hanya request yang lolos framing/auth/basic schema masuk ledger. Retensi hasil minimum 30 menit selama sesi hidup; entry in-flight tidak dievict. Jika kapasitas untuk entry yang belum kedaluwarsa penuh, `dedup_capacity_exceeded` sebelum commit. Tidak evict diam-diam agar menerima request baru. Sesudah expiry/restart/session close, baca ulang dan rekonsiliasi sebelum mutasi ulang; tidak ada janji retry exactly-once setelah crash.

`create_project` menggunakan scope client + server instance + request ID dan mengembalikan sesi baru. `open_project` admission read/lifecycle, bukan mutasi konten; canonical path yang sudah terbuka pada owner mengembalikan sesi yang sama. `set_selection` wajib session tanpa expected content revision. Save/export memakai request ID + snapshot revision dan mengembalikan job/hasil yang sama selama retensi; cancellation idempotent berdasarkan job ID. Request side effect baru hanya diterima jika revision yang diminta masih current saat snapshot dipin; jika tidak, `revision_conflict`, bukan mengganti dengan state terbaru. Setelah admission, job tetap memakai snapshot tersebut walau konten berubah. Deduplikasi retry job lama dilakukan sebelum pemeriksaan itu. Preview tanpa revision eksplisit menangkap current dan selalu melaporkan revision yang benar-benar dirender. Timeout/disconnect bukan bukti commit gagal.

Budget history awal 128 MiB per dokumen, eviction entry utuh dan pemberitahuan batas undo. Byte aset immutable disimpan terpisah dari history; perubahan referensi mempunyai leases. GC mark/sweep hanya saat tidak ada staging commit yang bersaing, dengan akar **live document, undo, redo, named snapshots, recovery dan queued/running jobs**. Lease dilepas setelah pengguna hasil selesai/TTL dan cleanup aman, bukan saat timeout client. Import mandiri mendaftarkan aset lewat transaksi; batch import+create menahan staging sampai satu commit, rollback/cancel menghapus staging. Asset byte yang masih diperlukan undo tidak dibuang walau image diganti/dihapus. Persisted recovery/snapshot mempunyai inventory referensi untuk GC lintas restart. Save native selalu menyertakan closure byte aset yang dibutuhkan konten portabel; history/leases runtime tidak diserialisasi.

## 8. Single writer dan lifecycle persistence (PRD 20.1)

Update 04A: [spike dua proses nyata](baseline-segment04a.md) membuktikan adapter
dan lifecycle 04 pada Windows lokal, termasuk crash/stale lock, external replace,
Save As gagal/sukses dan salinan document_id sama. Kontrak tetap; integrasi
GUI/MCP 19B/22 serta audit platform/security lebih luas 20 masih tertunda.

Semua jalur Open/Import Project/save/MCP memakai service yang sama. Path service menyelesaikan absolute path, `..`, case/drive spelling dan symlink/junction ke identitas final Windows; untuk target baru, resolve parent yang ada + nama target. Final identity dicek ulang sebelum replace untuk mendeteksi retarget. Tidak memakai string-prefix untuk allowlist. UNC/network writer default ditolak sampai semantics filesystem dibuktikan; read-only/import salinan lokal dapat ditawarkan. Existing hardlink berjumlah >1 ditolak untuk writer agar dua alias inode tidak melewati path lock; uji Windows di 04A/20. Path/lock tidak bergantung cwd.

Adapter QLockFile memakai sidecar canonical target + `.lock`, di luar container. Semua aplikasi memakai nama/protokol sama, dan long-lived lock mematikan expiry berbasis umur (`setStaleLockTime(0)`). Jangan mengambil alih writer aktif karena lock sudah tua. Metadata lock/PID/host serta process liveness diperiksa; ambiguous stale lock tetap read-only/error, force removal memerlukan konfirmasi pengguna. [Dokumentasi QLockFile](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QLockFile.html) menjelaskan stale detection dan batas koordinasi. Adapter persistence menyembunyikan Qt dari domain.

| Operasi | Urutan dan titik publikasi |
| --- | --- |
| New | Model tervalidasi → session baru tanpa path/lock, dirty; recovery tersedia setelah 14 |
| Open / Import Project | Allowlist/canonical identity → lock writer atau read-only → bounded ZIP/JSON/assets validation dan migrations di staging → registrasi session/tab setelah sukses; kegagalan melepas lock staging dan tidak mengganti tab aktif. Baseline berasal dari byte file yang benar-benar dimuat, dengan identity/hash stability check saat pembacaan; perubahan selama load membatalkan admission, bukan memasangkan model lama dengan baseline baru |
| Open kedua | Jika canonical path sama pada owner: fokus/return sesi yang sama; proses lain writer: attached jika bridge sah tersedia, selain itu read-only atau reject; tidak membuat writer kedua |
| Save | Pin snapshot/aset → serialize ke temp di filesystem tujuan → validasi temp → cek ulang baseline/identity → atomic replace → baseline baru dan checkpoint snapshot; satu save per sesi/path pada satu waktu |
| Save As | Hold source lock; acquire target lock dan baseline target/absent marker setelah persetujuan overwrite bila perlu → staged write/check/replace → transfer path/ownership setelah sukses; gagal mempertahankan sumber dan dirty/history. Target identik canonical source dirutekan ke Save tanpa reentrant lock; target milik sesi lain pada proses sama ditolak `target_in_use`, tidak berbagi writer lock |
| Duplicate Project | Clone/remap seluruh ID isi dan document ID baru → sesi/path baru melalui lifecycle biasa; blob immutable boleh sama |
| External change | Baseline SHA-256 + ukuran/mtime + file identity saat open/save; watcher hanya notifikasi. Sebelum replace hash ulang. Konflik membatalkan save, menawarkan Reload/Save As, tanpa overwrite diam-diam |
| Reload | Unsaved-change decision → validasi staging; sukses mengganti admission dengan session ID baru/history reset dan invalidasi cursor/request lama, memakai ownership yang masih sah |
| Close | Tolak request konten baru → resolve unsaved changes → cancel/drain jobs secara async dan tunggu side effect final → remove session/leases dan release lock; cancel close mengembalikan sesi terbuka |
| Crash / recovery | Startup menyajikan recovery; cek stale owner, baseline dan integrity; recovery menjadi admission baru, tidak diam-diam menimpa sumber/writer lain |

Lock adalah koordinasi proses aplikasi yang patuh. Program asing masih dapat menulis pada celah antara pemeriksaan baseline dan replace; tidak mengklaim atomic compare-and-swap filesystem terhadap semua program. Race identity/alias wajib ditangani fail-closed bila terdeteksi. Recovery tidak mengganti file utama otomatis. Read-only sesi tidak menerima mutasi konten; Save As ke target baru mempromosikan sesi menjadi writable hanya setelah berhasil.

Format normatif: extension `.ltechdesign`, format ID `ltechdesign.project`, container version `1.0`, document schema `1.0`, ZIP berisi manifest/document/assets index + data/tokens/fonts, workspace/thumbnails opsional, extensions capability-aware. [Spesifikasi format](ltechdesign-file-format.md) menetapkan exact fields, inventory hash, typed payload, capabilities dan unknown-field policy. PRD/app version terpisah dari versi format. Reject archive traversal, duplicate members, zip bombs, hash/size mismatch, missing embedded assets dan unsupported required capability sebelum admission. Unknown optional metadata extension dipreservasi opaque bila aman; duplicate project dengan unknown extension menunggu remap adapter atau ditolak. Field core tak dikenal tidak dibuang: reject edit atau read-only dengan penjelasan. Migration murni di staging, backup sumber sebelum menulis hasil versi baru. Implementasi validator/codec dan conformance tests tetap 02/04.

Import Project membuka dokumen lengkap dari path sumber dan mempertahankan konten/ID serta ownershipnya; bukan merge atau preview flatten. Absolute asset path, database lokal dan thumbnail tidak boleh dibutuhkan untuk restore. Font metadata asli/fallback disimpan terpisah dari resolusi runtime; embedding hanya bila lisensi mengizinkan. Save/Open/Import tanpa login/internet. Semua fitur baru wajib menambah codec/migration, undo, shared rendering dan export atau mencatat integrasi belum tersedia sampai pemilik segmennya selesai.

## 9. Shared renderer dan jobs

Satu traversal/render plan dari snapshot menentukan transform, style, text shaping/layout, clipping, stroke, shadow, isolation dan bounds. Scene adapter mengelola QGraphicsItems/cache/dirty regions; primitives menggambar dengan QPainter pada target canvas, QImage, PDF. Scene bukan renderer alternatif dengan default opacity/clip yang berbeda. Text memakai shared Qt layout (misalnya QTextLayout, diuji 06A/11) dan font resolver sama di canvas/headless; tidak memakai QGraphicsTextItem sebagai sumber layout tersendiri. Font tak tersedia menghasilkan warning, bukan mutasi metadata.

Export raster/PDF menerima snapshot + target/bounds/scale/DPI/background dan asset leases. JPG flatten dengan background pilihan; cek encoder WebP runtime, fallback Pillow dibuktikan 15. PDF single/multipage dan artboard berbeda ukuran wajib P0 16; print bleed/CMYK bukan alasan menunda dasar. Offscreen process menginisialisasi QGuiApplication pada main thread sendiri, memakai font/metrik dan drawing code sama; tidak memindahkan QGraphicsScene atau QPixmap live ke worker.

Jobs: `queued → running → succeeded | failed | cancelled`, dengan ID/session/source_revision/progress/result/error. Commit barrier eksplisit: cancel sebelum barrier membersihkan staging/temp; sesudah atomic replace/transaction publish, hasil tetap succeeded/failed yang menyatakan side effect aktual, bukan cancelled palsu. Multi-output P1 melaporkan hasil per file dan partial success. Artifact preview opaque ID + TTL 30 menit, default maksimum 2048 px/sisi; tidak dihapus selama dipakai job/resource. File export pilihan pengguna tidak terkena TTL. Job snapshot/aset di-pin sampai final cleanup. `get_job_status`/`cancel_job` P0; GUI dan MCP memakai service yang sama.

## 10. Thread dan IPC yang dipilih

| Komponen | Thread/proses pemilik | Komunikasi |
| --- | --- | --- |
| Live DocumentSession, dispatcher, revision/history, session state; Qt widgets/scene | Main GUI thread attached; satu owner event-loop thread headless | Serialized command queue, event setelah publish |
| SDK stdio adapter | Proses console terpisah; async event loop SDK | Typed requests ke owner bridge; stdout protokol saja, stderr/file log |
| Bridge listener dan persistence I/O actor/lock handles | QThread event loop per layanan pada owner process | Qt queued signals/futures; DTO immutable tanpa live model/widget |
| Decode/validation/hash/compression | Bounded workers; CPU-heavy Python ke subprocess spawn | Snapshot/staging, cancellation token, hasil tervalidasi dikembalikan owner |
| Render/export berat | Bounded subprocess offscreen, QGuiApplication pada main thread subprocess | Snapshot + asset leases, progress/result; shared renderer package |

Domain tidak mengenal thread Qt. [Qt Threads and QObjects](https://doc.qt.io/qt-6/threads-qobject.html) menjadi acuan affinity dan queued connection: widget/scene hanya main GUI thread, I/O QObject dibuat/dihapus dalam actor thread-nya. Tidak blocking `.wait()` GUI untuk job. Owner membuat snapshot immutable cepat; planning berat dilakukan pada snapshot worker, lalu owner mengecek ulang base revision sebelum publish. Maksimum satu commit konten berjalan per sesi. Stale plan ditolak, bukan dicommit ke state baru. Copy-on-write menghindari deep-copy besar setiap gesture; 23 mengukur biaya snapshot/commit terpisah.

Persistence actor menahan lock dan lease operasi path selama I/O async; owner tetap boleh menerima edit saat save snapshot berjalan. Close/Save As tidak melepas atau mengalihkan ownership sebelum actor memberi hasil barrier final. Scheduler menserialkan job save pada sesi/path dan menerapkan bounded queue. Respons sukses mutasi dikirim setelah publish revision, tidak setelah sekadar enqueue; redraw Qt menyusul event pada loop GUI yang sama. AT-12/13 tetap harus melihat model/scene konsisten.

IPC dipilih **QLocalServer/QLocalSocket**, Windows named pipe; tidak memakai HTTP tersembunyi. Endpoint acak per server instance, `UserAccessOption` sebelum listen, ditambah challenge/token lokal dan pemeriksaan instance/protocol. Descriptor endpoint/credential ada di runtime directory dengan ACL pengguna, tidak di file proyek/log/resource. Permission flag bukan perlindungan dari proses jahat milik pengguna yang sama. [Dokumentasi QLocalServer](https://doc.qt.io/qtforpython-6/PySide6/QtNetwork/QLocalServer.html) mendukung user access dan menjelaskan bahwa Windows dapat menerima beberapa server bernama sama; karena itu endpoint random dan handshake instance wajib, bukan menganggap nama pipe sebagai singleton lock.

Frame IPC: 4-byte big-endian length lalu UTF-8 JSON; maksimum JSON 4 MiB sebelum alokasi; protocol major 1, correlation ID, client credential context, operation dan typed arguments. Response berisi result/error, session/document/revision relevan. Bridge bukan server MCP kedua; SDK tetap external boundary, domain errors dipetakan konsisten. Versi mayor tidak cocok ditolak. Reconnect memakai credential client yang sama pada owner hidup agar dedup tetap berlaku. Tidak auto-launch atau takeover GUI/headless lain tanpa intent pengguna.

Headless writer memakai lock yang sama. Jika GUI pemilik dan bridge tersedia, CLI/MCP attached merutekan ke sesi pemilik; tanpa bridge sah writer ditolak/read-only. Headless rendering read-only boleh memakai snapshot file dengan revision sumber yang jelas, tidak mengaku state GUI terbaru. Registry discovery per-user memuat endpoint dan path/session routing secukupnya dengan ACL; stale descriptor tidak membuktikan owner mati. Close/reopen menghasilkan `session_closed` untuk request lama. Shutdown menolak queue baru, membatalkan pekerjaan sebelum barrier, drain yang sudah commit, lalu release lock dan runtime descriptor. Timeout awal 30 detik tidak membatalkan commit otomatis. 17A wajib menguji bridge nyata sebelum 18; 19A/19B memperluasnya.

Topologi headless yang dipilih: console SDK meluncurkan owner runtime child dengan Qt event loop ketika mode headless diminta; attached hanya menghubungi owner GUI yang sudah hidup. Owner runtime dapat meluncurkan subprocess render di bawahnya. CLI render/export sekali jalan memakai runtime yang sama tanpa SDK. EOF stdio memicu graceful shutdown owner headless setelah job/barrier diselesaikan; owner GUI tidak ditutup oleh EOF proxy attached. Reconnect/retry hanya dijamin ledger selama owner dan sesi tetap hidup. Completion worker selalu membawa session generation/base revision; hasil sesi yang sudah ditutup tidak boleh menghidupkan kembali tab/model.

## 11. Kontrak MCP awal dan batas keamanan

Official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) dipilih, bukan custom transport MCP. Belum ada versi SDK/protocol yang diuji; 18A membekukan JSON schemas, examples dan error union untuk semua tools PRD 7.3 + jobs sebelum tool dinyatakan bekerja. Kontrak lokal terdokumentasi menjadi source of truth; OpenAPI/HTTP workspace/Postman publication tidak diperlukan untuk stdio/named pipe pada 00.

Semua response dokumen memuat session/document/revision; konten mutasi memakai envelope bagian 7. Error terstruktur minimal code/message/details/retryable dan current_revision bila relevan. Kode kontrak: `validation_error`, `revision_conflict`, `session_closed`, `read_only`, `file_owned`, `target_in_use`, `external_change_conflict`, `path_not_allowed`, `unsupported_version`, `unsupported_capability`, `unsupported_visual_preservation`, `request_id_conflict`, `dedup_capacity_exceeded`, `stale_cursor`, `selection_unavailable`, `limit_exceeded`, `queue_full`, `artifact_expired`, `job_not_found`, `protocol_version_mismatch`. Tidak mengekspor traceback/secret sebagai detail publik.

Tree query filter page/subtree/name/type, depth/fields, default limit 100/max 500, deterministic depth-first pre-order mengikuti page/root/children order. Cursor opaque terikat session + revision + canonical query digest + offset; tamper/parameter berbeda ditolak, revision berubah `stale_cursor`. Resources `pydesign://project/active`, tree/tokens/selection/artboards dan `pydesign://sessions/{session_id}/...` memakai query service/batas yang sama; active alias menyertakan identitas eksplisit. Selection headless `selection_unavailable`; `set_selection` tidak didaftarkan sebagai fitur headless berhasil. Resources tidak membuka tree tak terbatas; invalidation revision P0, subscriptions opsional setelah diuji.

| Batas awal PRD 20.4 | Enforcement |
| --- | --- |
| JSON 4 MiB; batch 100 operasi | Sebelum parsing/alokasi besar, depth/schema checks; save/export/session ops dilarang dalam union konten |
| Asset 50 MiB/file; decode 40 megapixel | Header dan actual decode guard, staging bounded, SVG tanpa script/external fetch |
| Archive 10.000 entry/512 MiB uncompressed | Inventory/streamed limit, duplicate/path/hash checks sebelum admission |
| Render 64 megapixel/output; preview 2048 px/sisi | Validasi ukuran/scale dan offscreen buffers; efek/padding juga diberi budget |
| Request timeout 30 detik; dedup/artifact 30 menit | Timeout berarti hasil belum diketahui; poll job/retry dalam scope yang sama |

Queue awal maksimum 128 pending request per owner dan 16 job berat queued, satu render worker aktif; kelebihan ditolak `queue_full`, bukan memory tanpa batas. Nilai operasional ini asumsi 00 yang diuji 17A/18C/23, dapat dikonfigurasi dalam batas aman. Batas query response juga 4 MiB; jika fields/detail terlalu besar, `limit_exceeded` dengan saran fields/limit atau resource asset terpisah. Tidak memotong string diam-diam. Limits bukan janji sebuah dokumen 1.000 node dapat dibaca sekaligus; harus lewat pagination.

Allowlist filesystem ditegakkan service layer semua jalur, termasuk resource/job, bukan GUI saja. Tidak ada shell/database arbitrer, embedded script atau upload otomatis. Destructive lifecycle/outside-allowlist memerlukan interaksi persetujuan lokal yang tercatat; batch node di area yang telah diizinkan memakai undo, bukan dialog setiap command. Akses luar area ditolak sampai pengguna memperluas izin eksplisit, bukan disetujui AI sendiri. HTTP 21 `not_included`, default-off; jika diaktifkan kelak wajib SDK Streamable HTTP, loopback/token/Host/Origin validation dan regresi keamanan.

## 12. Rencana pembuktian dan keputusan terbuka

Dokumentasi 00 diperiksa kelengkapan pemilik/status/link lokal dengan `scripts/check-segment00.ps1`; `-RequirePrerequisites` juga memeriksa ketersediaan spesifikasi dan menjalankan `scripts/check-file-format-spec.ps1` atas contoh kontraknya. Audit kedua kini memakai typed domain boundary 02 untuk fixture final/historis, integrity dan semantic round-trip. Suite core 02 menguji invariants model/geometry dan penolakan input rusak. ZIP/Qt rendering/persistence belum dibuktikan oleh audit format. Integration backlog: 03 transaction/retry/history; 04/04A atomic codec/two-process locks; 06A shared-render artifacts; 17A subprocess bridge; 18/19 MCP; 22 AT lengkap; 23 performance; 24/25 clean Windows release.

Keputusan yang memang menunggu bukti mempunyai pemilik dan gate: schema/validators/fixtures 02 sudah teruji sesuai freeze ADR 0012, dependency pins 01 (sudah diuji; lihat baseline), packager 01A (spike lokal sudah diuji; gate Windows bersih 24), numeric tolerances 02 sudah dibekukan dan teruji, raster/font/PDF tolerances dan fallback resolution 06A, font redistribusi 11/24, IPC ACL/canonical Windows alias behavior 04A/17A/20, hardware budgets 23. Ownership, pivot/group opacity, revision, persistence lifecycle dan field/capability baseline sudah diputuskan. Perubahan yang memengaruhi kontrak wajib ADR dan migration bila perlu. Mesin Windows bersih yang belum tersedia dicatat pending di 24/25, tidak menghentikan pekerjaan independen dan tidak membuat rilis dianggap siap.

Asumsi kontrak tambahan yang dipilih 00 (tidak dinyatakan sebagai detail eksplisit PRD): UUID4 untuk ID baru, artboard root-only, grouping siblings dengan kebijakan preserve-appearance, read-only tanpa mutasi sebelum Save As, guides manual sebagai konten undoable, UNC/hardlink writer fail-closed, revision admission awal 0, headless owner child, queue budgets dan side-effect snapshot admission current-only. Pemilik pada ADR/roadmap harus menguji asumsi ini; perubahan yang memengaruhi caller/file dicatat sebagai ADR, bukan silent behavior change.

Update 05: shell/lifecycle GUI tersedia dengan dispatcher per tab, staged reload, read-only promotion dan executor satu worker persistence. Delta actor/thread dan batas renderer dicatat di [ADR 0015](adr/0015-desktop-session-shell.md), bukti di [baseline 05](baseline-segment05.md).

Update 06: rendering/drawing.py dan rendering/canvas.py mengimplementasikan shared shape traversal, isolated alpha/rounded clipping dan stable-ID scene indexing, dengan canvas navigation state per view. Delta renderer dan batas fitur di [ADR 0016](adr/0016-shared-painter-scene.md); bukti di [baseline 06](baseline-segment06.md). Full cross-target conformance menunggu 06A.

Update 06A: [ADR0017](adr/0017-render-conformance.md) membekukan fixed metrics QTextLayout/outline primitive, resource port, device-aligned isolation dan PDF single-page proof adapter. [Bukti conformance](baseline-segment06a.md) meliputi actual native canvas/PNG/PDF/QGui offscreen. Public export services/security/jobs/multipage tetap 15–17/20; font resolver/inline edit11 dan image12 tidak dianggap selesai.
