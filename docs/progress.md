# Progress ltechDesign Studio

Tanggal pembaruan: 26 Oktober 2026 (Asia/Jakarta). Baseline historis `54162c5`; HEAD saat mulai13 `db9fe72`. Working tree awal13 bersih; tidak ada commit otomatis. PRD 1.2. Indeks ini dibaca dahulu; lanjutkan hanya source/keputusan terkait segmen aktif.

## Status singkat dan langkah berikutnya

**Segmen aktif13: verified (26 Oktober 2026).** Pure-domain horizontal/vertical
stack, padding/gap/alignment, fixed/hug/fill, basic parent constraints, cycle/
overflow policy dan Inspector Apply terhubung transaksi/text/native/shared export.
Final459core+167desktop,46targeted/22native, Ruff107/mypy103, docs/fixtures/package/
installed-wheel/executable spike lulus. Native Inspector/PNG/PDF raster diperiksa;
PNG wheel byte-identik. [Baseline13](baseline-segment13.md),
[evidence13](evidence/segment13-verification.json), ADR0025. Base HEAD `db9fe72`,
tanpa commit otomatis. 08.layout dan induk08 kini verified. Tidak ada blocker13.
Berikutnya14 `not_started`; tidak dikerjakan otomatis. Advanced28 tetap backlog.

### Handoff segmen13

- `13.engine`, `13.commands`, `13.inspector`, `13.integration`, `13.handoff`
  `verified`. Graph dimensi tanpa Qt/scene menolak siklus; nested fill width ->
  shared text wrap -> hug height sebelum publish sekali. Resize parent tidak
  menskalakan anak. Invalid layout/metrics/token binding rollback seluruh batch.
- SetLayout/SetConstraints, ResizeNode/SetProperties, text/typography/font edits,
  child create/delete/reorder memakai dispatcher/history yang sama. Native1.0
  menyimpan konfigurasi dan geometry editable; stable IDs/asset references tetap.
  Shared canvas/PNG/PDF membaca geometry final; tidak ada renderer layout kedua.
- Aktual46targeted=39core+7desktop,22native termasuk pointer resize/inline text
  serta regresi transform/Inspector. Full `scripts/check.ps1 all` offline exit0:
  459core+167desktop, Ruff107/mypy103, docs/fixtures/build/isolated-wheel lulus.
  Incremental UI root-constraint validation: native22 lalu targeted46, mypy103,
  lint/format dan `check.ps1 package` ulang lulus; source terakhir masuk bundle.
- Python3.12.12/PySide6Qt6.10.2/Pillow12.3.0 tidak berubah; PyInstaller6.22.3
  build/executable offscreen spike exit0. Demo native actualDPR1.25 dan installed
  wheel (-I) menghasilkan PNG SHA256 sama; screenshot Inspector/PNG/PDF raster
  benar-benar diperiksa. Batas dan resolusi di ADR0025; tanpa toleransi tes lama
  yang dilonggarkan. Regresi fixed-text metrics guard yang ditemukan full gate
  diperbaiki dan tes asli lulus kembali.
- 08.layout kini verified dengan evaluator13 dan tes pointer/command parent resize,
  constraints/nested stack/text reflow/undo/native/export serta existing08 regression.
  Semua checkpoint08 lain sudah verified; induk08 verified untuk lingkup MVP.
  Bukti benchmark08 historis dan target100ms yang belum tercapai tetap pending23.
- Manual fisik keyboard/mouse/screen reader/OS DPI/monitor switching, viewer PDF
  lain dan mesin Windows rilis bersih belum diuji (22/24). Performance23,
  recovery14, public export jobs15–17, MCP18–19 dan advanced28 tetap pemilik.
  Aman melanjutkan14 sesuai prasyaratnya, bukan klaim seluruh acceptance/rilis.

**Segmen12 (historis): verified.** PNG/JPEG/WebP/static SVG via dialog/local drop,
embedded thumbnails, fit/fill/stretch/source crop/rounded clip/opacity/rotation dan
replace tanpa mengubah container tersedia. Final420core+160desktop,38targeted/
53native, lint102/mypy98, docs/fixtures/package/wheel/executable codec spike lulus.
Actual36MP cancel/staging/GUI heartbeat serta baseline10detik shapes/mixed diulang.
[Baseline12](baseline-segment12.md), [evidence12](evidence/segment12-verification.json), ADR0024.
Base HEAD `3f7a785`, working tree awal bersih, tanpa commit otomatis. Segmen13 tidak
dikerjakan; clipboard image eksternal tetap38A. Performance1000selection/GUI100ms
masih pending23, physical release machine pending24; bukan klaim semua NFR verified.

Catatan01–12 di bawah bersifat historis; status aktif sesi ini adalah13.

**Segmen aktif11: verified.** Text tool/inline multiline, validated Mixed typography Inspector, local/embedded font resolver dan shared layout/outline terhubung command/native/PNG/PDF. Final418core+124desktop,27targeted/28native, lint96/mypy92, fixtures/docs/package/wheel/executable spike lulus. Native DPR aktual1.25/1.875/2.5, PNG/PDF dan screenshot Inspector diperiksa. [Baseline11](baseline-segment11.md), [evidence11](evidence/segment11-verification.json), ADR0023. Base HEAD `f1918d2d28f2139f31fe4d2f5cc1a65ff533cc95`; tanpa commit otomatis. Segmen12 tidak dikerjakan.

**Segmen aktif10B: verified; induk10 verified.** Rulers/grid, world grid/object snapping, smart guides, master snap toggle dan Inspector align/equal-gap distribution tersedia. Final405core+110desktop,58targeted/47native, lint/type/fixtures/docs/package/wheel/executable spike lulus; native DPR1/1.5/2 dan PNG/PDF diperiksa. [Baseline10B](baseline-segment10b.md), [evidence](evidence/segment10b-verification.json), ADR0022. Tidak mengerjakan11 atau manual guides38B otomatis.

**Baseline08: blocked pada integrasi layout13.** Semua checkpoint independen08.transforms/editing/clipboard/baseline/handoff verified: 352 core+53 desktop, lint/type/fixtures/docs/package/wheel,7 GUI native dan executable spike lulus. Induk08 tidak verified: evaluator Constraints/Layout13 belum ada. Frame default fixed berfungsi; tidak mengarang evaluator atau menskalakan anak sebagai pengganti. Dua baseline10detik tersimpan, respons GUI batch110,69/111,07ms masih melampaui target100ms. Detail [baseline08](baseline-segment08.md), ADR0019.

**Baseline 07: verified.** Preset/custom artboard, lima drawing tools, ephemeral preview, hit-testing dan session selection tersedia. Gate final 344 core + 46 desktop, lint/type/fixtures/docs/package/installed-wheel, 27 tes GUI native serta executable offscreen spike lulus. Screenshot native canvas/dialog benar-benar diperiksa. Detail [baseline 07](baseline-segment07.md), ADR 0018.

**Baseline 06A: verified untuk fixture conformance yang diminta.** Canvas/PNG/PDF/QGui offscreen memakai traversal yang sama; text primitive awal, device-aligned isolation dan lossless PDF fallback dibuktikan dengan artifact nyata. Full gate 324 core + 19 desktop, lint/type/fixtures/docs/package/wheel dan executable offscreen lulus. Bukti [baseline 06A](baseline-segment06a.md), ADR 0017. Teks PDF berupa outline; UI export/multipage dan text editing tetap segmen pemilik.

**Baseline 06: verified untuk renderer dasar/navigation.** Shared painter traversal, isolated opacity, rounded clip, stable-ID scene adapter dan pan/Ctrl+wheel/zoom controls/fit tersedia. Gate final 324 core + 16 desktop (7 tes renderer baru), lint/type/fixtures/docs/package/wheel lulus; executable offscreen spike exit 0. Demo native fixture dan screenshot diperiksa. Detail [baseline 06](baseline-segment06.md), ADR 0016. 06A menunggu instruksi berikutnya sesuai klarifikasi pengguna.

**Baseline 05: verified untuk shell/lifecycle.** QMainWindow, menu/toolbar, Pages/Layers, Inspector, tabs, selection/history/dirty state per sesi dan async persistence tersedia. Gate final: 324 core + 9 desktop, lint/type/fixtures/docs/build/wheel lulus. Native screenshot loaded-document pada DPR efektif 1/1.5/2 diperiksa; AT-27 monitor fisik/handles/export tetap pending pemiliknya. Detail [baseline 05](baseline-segment05.md) dan ADR 0015. Segmen 06 belum dimulai.

**Baseline 04A: verified.** Tujuh tes memakai dua proses persistence nyata membuktikan writer/read-only, close/crash/stale lock, baseline conflict, Save As gagal/sukses, source lock lifecycle, hardlink dan salinan document_id sama. Gate offline lulus: **324 core + 5 desktop offscreen**, lint/type/fixtures/docs/build/wheel portability. Bukti di [baseline 04A](baseline-segment04a.md). Fondasi 01–04 tetap verified; integrasi GUI/MCP tetap 19B/22.

- [architecture.md](architecture.md): module boundaries, identity/hierarchy, geometry/pivot/group opacity, ownership, lifecycle, renderer, content/session/jobs, dedup/retention, thread/IPC dan batas MCP.
- [ADR index](adr/README.md): empat belas keputusan dengan konsekuensi dan pemilik pembuktian, termasuk dispatcher runtime, persistence dan asal-usul baseline format baru.
- [requirements-matrix.md](requirements-matrix.md): FR/NFR/AT, bagian 20, import/export, tools/resources dan deliverables.
- [audit segmen 00](../scripts/check-segment00.ps1): pemeriksaan struktur/cakupan dokumen dan gate prasyarat terpisah.
- [Spesifikasi .ltechdesign 1.0](ltechdesign-file-format.md), [contoh JSON kontrak](examples/ltechdesign-v1-contract.json), [native ZIP](../examples/proyek-contoh.ltechdesign), dan [audit contoh](../scripts/check-file-format-spec.ps1): typed validator 02 + codec produksi 04; GUI masih menunggu 05/22.

Segmen09/10A/10B/induk10 dan11 verified, independen dari blocker08.layout/13.
12 verified; berikutnya13 tetap not_started. Production export
tetap15–17 dan manual guides P1 tetap38B; clipboard image eksternal tetap38A.

### Handoff segmen12

- 12.import/render/editor/retention/baseline/handoff `verified`; tidak ada blocker
  lingkup12. Command SetMedia (tanpa Qt) dan RegisterAsset+Create/SetMedia atomik
  memakai dispatcher/revision/undo yang sama; Save/Open/native1.0 mempertahankan
  semua byte/reference, crop/fit dan container. Runtime thumbnails bukan restore.
- Source utama assets/importing/store/validation, rendering/media/shared drawing,
  ui/images/canvas/window/Inspector, commands contracts/planning. Clipboard node
  internal existing disambungkan ke prepared media; clipboard image eksternal38A
  belum dikerjakan. Subset SVG/rejection policy di image-import.md dan ADR0024.
- Base HEAD `3f7a785dee15c9d5b61eaa6f207f9dd07412bb1a`; tanpa commit otomatis/ubah
  PRD. Python3.12.12/PySide6Qt6.10.2/Pillow12.3.0 tetap; PyInstaller6.22.3 diuji.
- Aktual38targeted=2core+36desktop,53native=36image+17style/transforms,36image
  masing-masing faktor1.5/2. Probe actualDPR1.25/1.875/2.5, native/offscreen/wheel
  shared PNG exact. Finalcheck.ps1 exit0:420core+160desktop, Ruff102/mypy98,
  docs/fixtures/build/installed-wheel lulus. Executable offscreen spike exit0
  benar-benar encode/decode PNG/JPEG/WebP dan record/replay SVG vector dalam bundle.
- Canvas/PNG exact; PDF opaque interiors≤2/255 dan SVG opaque no image XObject.
  Source move/reopen, editable crop+replace native roundtrip, actual drop Copy,
  malformed/unsafe/animation/EXIF/limits, atomic multi-file rollback, stale/closed
  source dan GUI-thread publication diuji. AT-25 real GC/undo/redo/independent lease
  menahan bytes; persisted recovery14 tetap pemiliknya.
- Actual36MP cancel selesai180.64ms,29heartbeat, gap38.60ms, nodes/staging/blobs0.
  Decode native tunggal tidak preemptible, cancel dicek sebelum publication.
  Import satu active worker/32file, byte50MiB/decode40MP, prepared cache256MiB;
  SVG bounds/complexity dan rejection semantics terdokumentasi.
- Baseline final10detik/phase, shapes dan20%media pada sourcehash sama:100object
  pan/drag p95≈16.72–16.79ms. 1000selection max164.84/120.14ms dan batch heartbeat
  123.50/117.98ms masih melampaui100ms, pending23; tidak mengubah target. RSS
  repeated open/close≈103.8–107.8MB tanpa raster besar; development host32GiB,
  bukan mesin rilis acuan. Bukti lengkap di baseline12/evidence12.
- Screenshot aplikasi native dan actual PDF raster diperiksa. Explorer/mouse/
  keyboard/screen reader/OS DPI fisik, viewer PDF lain dan mesin rilis bersih
  belum diuji, pending22/24. Production export jobs15–17/MCP18/19/recovery14 tetap
  integrasi pemilik. Existing08.layout masih blocked13. Berikutnya13 `not_started`,
  aman dilanjutkan sesuai scope/prasyarat; tidak dijalankan otomatis.

### Handoff segmen11 (historis)

- 11.commands,11.layout,11.editor,11.handoff `verified`; tidak ada blocker lingkup11. Text tool klik auto_width/drag fixed; inline multiline/F2/double click, Unicode/IME/clipboard/Delete dan grouped undo melalui dispatcher yang sama. Typography fields/Mixed/validation, color/opacity10A, auto_height/resize, missing-font warning dan explicit replacement/undo tersedia.
- Shared QTextLayout96dpi/design advances, outline/fallback/emoji diagnostics dan UTF16 caret dipakai canvas/PNG/PDF; serialization native1.0 mempertahankan data/font IDs/embedded bytes dan ukuran. Font registry fallback diselesaikan setelah seluruh embedded font dimuat; reopen tidak mengandalkan path font sumber. IME preedit/session selection tidak ikut PNG/scene.render/PDF/history/native.
- Base HEAD `f1918d2d28f2139f31fe4d2f5cc1a65ff533cc95`, working tree awal bersih; tanpa commit otomatis/ubah PRD. Python3.12.12/PySide6Qt6.10.2/Pillow12.3.0 tidak berubah. Kontrak unit baseline/letter spacing, metrics port tanpa Qt, limits dan fallback di ADR0023.
- Aktual27targeted (13core+14desktop),28native (13text/layout+15regresi Inspector/transforms),7text native masing-masing DPR aktual1.875/2.5; native utama DPR1.25. Full check.ps1 offline exit0:418core+124desktop, Ruff96/mypy92, fixtures/docs/build/installed-wheel lulus. PyInstaller6.22.3 offscreen executable spike exit0; isolated-wheel embedded-font conformance exit0.
- Canvas==PNG exact, metrics native/offscreen exact; outline edges max19/interior0, PDF2x native40/offscreen38 dan interior2/255 (nested alpha quantization). Existing06A tests tidak dilonggarkan. Native font controls/scroll layout pada tiga DPR, shared Unicode/emoji PNG dan actual PDF raster benar-benar diperiksa. Artifact/log/hash di baseline11/evidence11.
- Batas: emoji outline monokrom bila tersedia, replacement+warning jika tidak; PDF text outline tidak searchable. Physical IME candidate-window/keyboard/mouse, screen reader, monitor switching/OS DPI fisik, viewer PDF lain/mesin rilis bersih pending22/24. Rich spans/fonts lanjutan31, layout13, image12, public export/jobs15–17/MCP18/19 tetap pemilik.
- Berikutnya12 `not_started`; aman melanjutkan sesuai scope/prasyaratnya, tidak dijalankan otomatis. Existing08.layout tetap blocked pada13.

### Handoff segmen10B

- 10B.snapping/arrangement/overlays/handoff `verified`; tidak ada blocker10B. Induk10 `verified` karena10A dan10B selesai. Ruler world-px pada margin viewport, fixed logical grid, grid/object edge-center snap, ephemeral smart guides dan mode/master toggle per tab tersedia; manual guides tetap38B.
- ArrangeNodes melalui dispatcher: six-way world align/equal gaps, per-parent inverse translation, root selection, one undo/revision/event, unchanged IDs/z-order. Pointer move/drawing/resize menjaga anchor/uniform scale dan physical-pixel tolerance8/(zoom*DPR). Inspector/nudge tetap literal logical px, publication menyinkronkan canvas/Inspector.
- Source utama domain/snapping.py/arrangement.py, commands contracts/planning, ui/canvas_aids.py/arrangement.py/canvas.py/transforms.py/Inspector/window serta view grid renderer. Native1.0/dependency tidak berubah. ADR0022 mencatat kebijakan candidate geometry/clip AABB konservatif dan state view yang tidak ikut serialization/history/export.
- Base HEAD `d05a7e171d070987eddf091cd7b21a4f1ad5c06f`; perubahan09/10A dipertahankan, tanpa commit otomatis/ubah PRD. Versi diuji Python3.12.12, PySide6/Qt6.10.2, Pillow12.3.0.
- Aktual58targeted offscreen (29core+29GUI),47native (29GUI10B+18regresi09/10A). Full check.ps1 offline exit0:405core+110desktop, Ruff87/mypy83 files, fixtures/docs/package/installed-wheel lulus. Build/executable offscreen exit0, PyInstaller6.22.3; isolated-wheel aids spike empat zoom lulus.
- Native actual DPR1/1.5/2 pada zoom0.5/1/2/4:7.9physical px snap,8.1 tidak; actual QTest gesture dan one-undo/Inspector sync terbukti. Nested parent move/resize, cross-parent multiselect, hidden/locked exclusion, stable order/equal/negative gaps, stale/selection/toggle cancellation, master snap off, overlay-free exact scene/PNG, aligned PDF pixels dan Save/Open editable diuji. Screenshot ruler/grid/guides/DPR serta PNG/PDF raster benar-benar diperiksa.
- Ruler tidak menutupi konten: viewport margin terpisah mempertahankan regresi drawing10A native. Programmatic Layers selection membatalkan preview tanpa perlu focus-out. Timer ruler dimiliki view, tidak membuat content command atau callback pada view yang sudah dihapus.
- Mouse fisik, screen reader, monitor switching/OS DPI fisik, mesin rilis bersih dan benchmark besar pending. Existing08.layout masih blocked pada13; manual guides38B, text11, constraints13, public export/jobs15-17, MCP18/19, acceptance22/performance23/release24 tetap pemilik.
- Berikutnya11 `not_started`; aman melanjutkan sesuai prasyaratnya, tidak dijalankan otomatis. Bukti/log/hash di baseline10B/evidence10B.

### Handoff segmen10A (historis)

- 10A.properties,10A.history,10A.shadow,10A.handoff `verified`. Tidak ada blocker lingkup. Parent-space X/Y, anchor/pivot resize, uniform group width/height, rotation/opacity/fill/centered stroke/radius/shadow, RGBA picker, foreground/background defaults dan validated Mixed values terhubung dispatcher yang sama.
- Source utama domain/inspector.py, commands contracts/planning/dispatcher, ui/inspector.py/window.py/canvas.py, rendering/shadow.py/drawing.py/pdf.py. Native codec1.0 tidak berubah; warna/aset desain tetap portable/editable. Pillow12.3.0 dikunci setelah install/tes bersama Python3.12.12 dan PySide6/Qt6.10.2. ADR0021 mencatat history_group/save boundary dan shared alpha-shadow semantics.
- Base HEAD `d05a7e171d070987eddf091cd7b21a4f1ad5c06f`; perubahan09 yang sudah ada dipertahankan. Tidak mengubah PRD atau membuat commit otomatis. Source/artifact hashes di evidence10A.
- Aktual:34targeted offscreen (16core+18GUI),18Windows native; full check.ps1 offline exit0,376core+81desktop, Ruff79/mypy75 files, fixtures/docs/package/wheel/isolated-wheel lulus. smoke-build.ps1 offscreen exit0, PyInstaller6.22.3; wheel probe native ZIP->PNG byte-identik/PDF shadow lulus. Perintah/log di baseline10A.
- Canvas/PNG fixture nested rotation/scale/stroke/radius/shadow exact; PDF2x max18/255/interior1/255 dan rasterization report benar. Group overlap alpha/undo, thick rotated stroke bounds, large/empty shadow limits, atomic invalid multiselect, stale external focus/picker, keyboard/slider merge, Save/Open editable roundtrip diuji. Screenshot Inspector/Mixed/actual RGBA picker serta PNG/PDF raster benar-benar diperiksa.
- Mouse fisik, screen reader, multi-monitor/DPI, PDF viewer lain dan mesin rilis bersih pending, tidak menghentikan pekerjaan independen. Existing08.layout menunggu13; text/image11/12, constraints/export Inspector13/15-17, MCP18/19, acceptance22/performance23/release24 tetap pemilik.
- Berikutnya10B `not_started`; aman melanjutkan pekerjaan independen yang memakai10A, tetapi tidak dikerjakan otomatis. Induk10 `in_progress` sampai10B verified; tidak membuat snapping.

### Handoff segmen09

- 09.commands,09.panel,09.drag,09.handoff `verified`; tidak ada blocker09. Typed page CRUD/duplicate, graph/token ID remap dengan asset/font immutable refs, page-active stable ID, tree/search/own visibility-lock/selection, Qt DnD→RelocateNodes atomik tersedia. Qt item bukan sumber model dan tidak melakukan default drop mutation.
- Source utama commands/contracts.py/planning.py, workspace guard dispatcher.py, ui/hierarchy.py, integrasi window.py dan safe editing guard di ui/editing.py. Tidak mengubah native schema/version/dependency atau validator layout13. ADR0020 mencatat kontrak reverse-z drop, world preservation/context mode dan workspace sanitization.
- Base revision saat mulai09 `d05a7e171d070987eddf091cd7b21a4f1ad5c06f`; working tree awal bersih, tidak membuat commit otomatis, PRD tidak diubah. Fixture contoh dipulihkan byte-identik setelah kesalahan Save pada harness awal; tes final memakai source copy tmp_path dan Save As, fixture repo final tidak berubah.
- Verifikasi aktual: targeted18=8core+10GUI lulus;10GUI native lulus. `scripts/check.ps1` offline exit0, **360core+63desktop**, Ruff73/mypy69 files, fixtures/docs/build/wheel/isolated-wheel smoke lulus. `scripts/smoke-build.ps1 -SmokeMode offscreen` exit0, PyInstaller6.22.3. Python3.12.12/PySide6Qt6.10.2 tanpa dependency baru. Perintah dan log di baseline09.
- Bukti mencakup actual Qt drag events, nested world matrices, PNG pixel/z-order, cycles/stale/reparent clip context, hidden/locked ancestors, search/reveal/collapse, selection signal count tanpa loop, external dispatcher pada active/inactive tab serta external revision ketika rename inline terbuka. Page duplicate/delete/undo dan ZIP save/reload mempertahankan graph/aset/bindings; optional workspace page refs tetap sah.
- Screenshot native Pages/Artboards/Layers benar-benar diperiksa. Input fisik, screen reader, multi-monitor dan mesin rilis bersih belum manual; skenario ada di baseline09. Caller eksternal memakai dispatcher lokal, bukan klaim transport MCP18/19.
- Berikutnya10A not_started, aman untuk scope Inspector/style yang memakai09; tidak dijalankan otomatis. 08.layout/13 tetap blocked, public export/jobs15–17, SDK/MCP18/19, acceptance22/performance23/clean release24 masih pemilik.

### Handoff segmen08 (historis)

- Status induk `blocked` hanya untuk08.layout: `Layout`/`Constraints` masih ditolak oleh Project validator dan Draft; perlu evaluator13 nyata, admission dan tes resize-frame+layout+undo atomik. Checkpoint08.transforms/editing/clipboard/baseline/handoff `verified` pada lingkup independen. Tidak ada prasyarat lain yang diarang atau P0 ditandai not_included.
- Implementasi: domain/editing.py, semantic selection commands di commands, wireframe gesture/handles di ui/transforms.py, action/clipboard/context/focus routing di ui/editing.py, portable embedded clipboard di persistence/clipboard.py; integrasi canvas/window, bounded staging cleanup dan cache proyeksi/fingerprint. ADR0019 mencatat modifier, parent/world, aspect/anchor, frame-vs-group dan clipboard limits.
- Tes aktual: `scripts/check.ps1` offline exit0, **352 core+53 desktop**; targeted15=8core+7GUI;7GUI native exit0. Ruff70/mypy66 files, fixtures/docs/sdist/wheel/isolated-wheel smoke lulus. `scripts/smoke-build.ps1 -SmokeMode offscreen` exit0, PyInstaller6.22.3. Python3.12.12/PySide6Qt6.10.2 tanpa dependency baru; perintah/log di baseline08.
- AT24: actual PNG group→reparent rotated parent→ungroup, max byte-channel delta≤1/255, undo memulihkan hierarchy/project tepat. Nested anchor/member/group scaling, delete-subtree/history/redo-branch, asset clipboard setelah source close, GC+undo/redo+save/reload, stale/corrupt clipboard dan text-safe shortcuts diuji. Screenshot handles/context Windows native dan PNG benar-benar diperiksa; mouse fisik/multi-monitor belum manual.
- Dua benchmark10detik native disimpan; [evidence terbaru](evidence/segment08-benchmark.json):100pan p95/p9916,45/16,83ms;100drag16,49/16,84ms;1000pan-selection16,90/48,04ms, gapmax53,30ms. Commit100 p95/max49,16ms; GUI heartbeat110,69ms **melewati100ms**, tetap pending23. Resident1000~94,77MB, tiga siklus97,69–97,99MB; run pertama dipertahankan. Tidak mengklaim reference hardware/cold launch/leak-free.
- Revision dasar `23515f33714519cf732ded30e818ef9fc0ff0c28`, perubahan07 yang sudah ada dipertahankan, PRD tidak diubah, belum ada commit sesi ini. Native serialization/shared drawing/PNG dan PDF conformance terhubung; public export/jobs15–17, MCP18/19, acceptance22/23/24 tetap pemilik.
- Berikutnya09 not_started. Infrastruktur hierarchy/commands untuk bagian09 yang independen tersedia; penutupan induk08 tetap menunggu08.layout/13. Tidak otomatis mengerjakan09 atau13.

### Handoff segmen 07 (historis)

- 07.artboards, 07.gestures, 07.selection dan 07.handoff semuanya verified pada lingkup segmen. Tidak ada blocker. Artboard1080×1350 dan custom unit/orientasi/DPI, lima tool, nested parent space, preview/cancellation, single undo, hidden/locked dan selection sinkron Layers dibuktikan.
- Source utama domain/authoring.py, ui/artboard.py, ui/canvas.py, rendering/hit_testing.py dan integrasi ui/window.py. Serialization/native/shared drawing/PNG/PDF proof memakai implementasi yang sudah ada; tidak mengubah schema atau dependency. ADR0018 mencatat pilihan parent/polygon/marquee/toleransi.
- Base revision aktual `23515f33714519cf732ded30e818ef9fc0ff0c28`, belum ada commit sesi ini. PRD tidak diubah.
- Verifikasi aktual: `scripts/check.ps1` offline exit0, 344 core + 46 desktop, ruff63/mypy59 files, fixtures/docs/build/wheel smoke. Target 20 core + 27 GUI baru lulus; 27 GUI yang sama juga lulus pada platform Windows native. `scripts/smoke-build.ps1 -SmokeMode offscreen` final exit0, PyInstaller6.22.3. Python3.12.12, PySide6/Qt6.10.2 diuji tanpa dependency baru. Perintah/log di baseline07.
- Save/close/Open seluruh node mempertahankan posisi/ID/hierarchy/data; custom mm/300DPI juga diuji save/reload. Fixture editable dan screenshot canvas/dialog Windows native di artifacts/drawing07; screenshot benar-benar diperiksa. Mouse fisik/multi-monitor/mesin rilis bersih belum diuji manual.
- Integrasi tertunda sesuai pemilik: handles/transform08, layer management09, text11/image12, production export/jobs15–17, MCP18/19, acceptance22/performance23/clean release24. Tidak ada tool text/image dummy. Berikutnya08 tidak dikerjakan otomatis.

### Handoff segmen 06A (historis)

- Checkpoint 06A.fixture/text/targets/handoff verified pada lingkup fixture yang diminta; tidak ada blocker 06A. Artifact actual dan perintah reproduksi di baseline 06A. Base revision 54162c5, working tree belum di-commit; tidak mengubah prd.md pengguna.
- Source: rendering/text.py, rendering/pdf.py, perbaikan isolation drawing.py, resource port canvas.py, scripts/check_render_conformance.py dan render_compare.py, tiga tes conformance baru + regresi ancestor clip. Domain/format native tidak berubah.
- Hasil aktual check.ps1 offline exit 0: 324 core + 19 desktop, ruff57 files/mypy53 files, fixtures/docs/build/wheel smoke. smoke-build.ps1 offscreen exit 0, PyInstaller6.22.3; Python3.12.12/PySide6Qt6.10.2 tetap terkunci tanpa dependency baru.
- Native canvas vs PNG exact; native/offscreen layout exact dan interior pixels0 error, hanya glyph edge max4/255. PDF interior0 error, edge band1px max58/255, regional geometry ≤1px. Alpha overlap127±1/rounded corner0. Dua PDF image objects membuktikan isolation+SMask; shape/text lain vector.
- Native canvas screenshot dan PDF raster benar-benar diperiksa. Poppler tidak tersedia; QtPdf/PDFium digunakan sebagai rasterizer pembanding. PDF text outline tidak searchable; resolver/inline editing11, image12, shadow10A, UI/multipage/jobs15–17, full acceptance22 tetap pending. Print/monitor fisik dan viewer PDF lain belum diuji.
- Berikutnya07 not_started. Scope hanya06A; tidak memperluas drawing tools atau export UI.

### Handoff segmen 06 (historis)

- Checkpoint 06.drawing, 06.adapter, 06.navigation, 06.verification: verified pada scope dasar. Tidak ada blocker 06. Source rendering/drawing.py, rendering/canvas.py, integrasi ui/window.py dan scripts/demo_renderer.py; kontrak di ADR 0016.
- Base revision 54162c5, seluruh implementasi masih working tree, tidak membuat commit. Tidak ada dependency baru. Python 3.12.12, PySide6/Qt 6.10.2 diuji.
- Verifikasi aktual check.ps1 offline exit 0: 324 core + 16 desktop, lint/format/type (49 files)/fixtures/docs/build/wheel. smoke-build.ps1 offscreen exit 0 (PyInstaller 6.22.3); bukti di baseline 06.
- Demo native dan shared image diperiksa; navigasi Qt events tidak mengubah model/history; stable item identity diuji setelah command edit. Manual mouse fisik/multi-monitor dan benchmark besar belum dilakukan.
- Integrasi tertunda: 06A conformance cross-target, text 11, image/SVG 12, shadow/style lengkap 10A, export 15–17 dan acceptance 22. Canvas memberi warning untuk fitur belum didukung; strict offscreen menolak daripada menghasilkan output tak lengkap.
- Selanjutnya 06A wajib sebelum drawing diperluas; status 06A not_started, tidak dijalankan sesi ini sesuai klarifikasi pengguna.

### Handoff segmen 05 (historis)

- Status `verified` untuk checkpoint shell/lifecycle/verification; source utama ui/window.py, staged service.reload, Dispatcher.set_read_only; tanpa dependency baru. ADR 0015 menjelaskan executor worker.
- Verifikasi final: check.ps1 offline exit 0 (324 core + 9 desktop, lint/type/fixtures/docs/wheel), smoke-build.ps1 offscreen exit 0. Empat tes GUI baru, native loaded screenshot pada DPR 1/1.5/2 diperiksa.
- Base revision 54162c5; belum di-commit. Bukti/cara demo/keterbatasan/manual checklist di baseline 05. AT-27 monitor fisik/export/handles, renderer 06/06A dan acceptance 22 tetap pending; 06 belum dimulai.

### Handoff segmen 04A (historis)

- Status `verified`; tidak ada blocker lingkup. Perubahan terbatas pada harness worker, tujuh tes subprocess, konfigurasi type check dan dokumentasi/evidence. Kontrak/service produksi tidak berubah; ADR baru tidak diperlukan.
- Revision dasar `54162c5f1c7300d5701dd841b0fb961592540d8b`, belum ada commit implementasi. Perubahan pengguna dipertahankan.
- Reproduksi: `.venv/Scripts/python.exe -m pytest tests/test_persistence_processes.py -v --junitxml=artifacts/segment04a.xml` → **7 passed, 0 skipped**. Child punya PID berbeda, cwd sementara, QLockFile dan service produksi nyata. Save As gagal karena handle baca Windows nyata, tanpa mock replace.
- Gate: `$env:UV_OFFLINE = 'true'; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1` → exit 0, **324 core + 5 desktop**, lint/format/type (41 files)/fixtures/docs/package/installed-wheel smoke lulus. Python 3.12.12 dan PySide6/Qt 6.10.2, tanpa dependency baru.
- Bukti AT-21/22/26 fondasi dan transcript PID/request/response ada di baseline 04A dan [evidence](evidence/segment04a-processes.json). Acceptance GUI/headless attached/MCP, multi-tab routing/history tetap pending 19B/22; audit junction/ACL/PID reuse ambigu lebih luas di 20.
- Tidak ada GUI baru atau pemeriksaan visual/manual. Skenario manual GUI/MCP menunggu subsistem pemilik, bukan diklaim lulus dari subprocess.
- Berikutnya 05 tetap `not_started`; tidak dikerjakan otomatis.

### Handoff segmen 04 (historis, sebelum 04A)

- Status: `verified`; checkpoint 04.codec, 04.ownership, 04.retention dan 04.handoff semuanya verified pada lingkup fondasi; dirinci di baseline 04. Tidak ada blocker lingkup 04.
- Revision dasar: `54162c5f1c7300d5701dd841b0fb961592540d8b`; seluruh perubahan belum di-commit. `prd.md` pengguna tidak diubah.
- Perubahan: package persistence/assets, 87 tes fondasi, fixture ZIP valid dan generator khusus fixture, smoke installed-wheel, ADR 0014 dan dokumentasi traceability. Tidak ada dependency baru.
- Verifikasi aktual: `$env:UV_OFFLINE = 'true'; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1` → exit 0, 317 core + 5 desktop, lint/type/fixtures/docs/build/isolated-wheel smoke lulus. `scripts/smoke-build.ps1 -SmokeMode offscreen` → build/executable exit 0. Wheel memuat 2 page/17 objek/3 blob dengan cwd berbeda. Python 3.12.12, PySide6/Qt 6.10.2 dan dependency versions aktual tercatat di baseline 04.
- Demo: perintah offline pada baseline 04 atau `uv run --offline --locked python scripts/check_persistence.py examples/proyek-contoh.ltechdesign --scratch artifacts/persistence-demo` setelah environment uv dikonfigurasi.
- Batas: PNG fixture JSON lama corrupt CRC, dipertahankan dan diuji ditolak; fixture native baru memakai PNG valid. Layout/evaluator 13, GUI 05, resolver font 11, renderer/thumbnail/export 06/06A/15–17, persistent recovery 14, job scheduler/MCP 18/19/22 masih pending sesuai pemilik.
- Visual/manual tidak dilakukan; tidak ada perubahan GUI. Skenario manual dan batas tes otomatis tercatat di baseline 04. Mesin Windows bersih/CI remote tetap pending.
- Berikutnya 04A tetap `not_started`, tidak dikerjakan otomatis.

### Handoff segmen 03

- Status: `verified`; 03A operasi/hierarchy, 03B transaksi/history, 03C retry/retention ports dan 03D verification/handoff verified pada lingkup fondasi. Rincian ada di baseline 03; tidak ada blocker lingkup 03.
- Revision dasar: `54162c5f1c7300d5701dd841b0fb961592540d8b`; belum ada commit implementasi. Perubahan pengguna pada `prd.md` dipertahankan.
- Perubahan: package `commands`, 37 tes perilaku, ADR 0013, architecture/progress/requirements matrix. Tidak ada dependency baru atau rewrite domain 02.
- Verifikasi aktual: `$env:UV_OFFLINE = 'true'; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1` exit 0, 230 core + 5 desktop; lint/format/type/fixtures/docs/build/isolated-wheel smoke lulus. Riwayat kegagalan awal dan pemulihannya tercatat di baseline 03.
- Demo: `uv run --offline --locked pytest tests/test_commands.py -v`, atau snippet dispatcher pada baseline 03.
- Integrasi tertunda: blob store/atomic save/ownership 04/04A, GUI/session/gesture 05/08, renderer/export 06/06A/15–17, layout evaluator 13, IPC/MCP 18/19/22 dan benchmark 23. Port metadata default menolak import aset baru tanpa store. Tidak ada journal retry lintas restart.
- Visual interaktif/manual belum dilakukan; desktop offscreen hanya regresi otomatis. CI remote/clean Windows release tetap pending, tidak memblokir pekerjaan independen 04.
- Aman melanjutkan ke 04 setelah pengguna memberikan instruksi. 04 tetap `not_started`.

### Handoff segmen 02 (historis, sebelum 03)

- Status: `verified`; tidak ada blocker tersisa untuk lingkup domain/schema 02. Tidak ditemukan AGENTS.md pada workspace atau ancestor yang diperiksa.
- Revision dasar: `54162c5f1c7300d5701dd841b0fb961592540d8b`; implementasi masih berupa perubahan working tree, belum memiliki commit tersendiri.
- Verifikasi aktual: `$env:UV_OFFLINE = 'true'`, lalu `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1`; exit 0, 193 core + 5 desktop offscreen lulus, lint/type/fixture/docs/package dan installed-wheel domain smoke lulus. Detail environment dan hasil ada di [baseline 02](baseline-segment02.md).
- Demo tanpa GUI: `uv run --offline --locked python scripts/check_file_format.py` memuat fixture final/historis, memeriksa integrity dan semantic round-trip, serta menolak required capability yang tidak didukung.
- Pemeriksaan visual manual tidak dilakukan untuk 02; tes desktop hanya regresi otomatis offscreen. CI remote dan mesin rilis Windows bersih belum diuji pada sesi 02.
- Integrasi tertunda: dispatcher/undo/revision atomik 03, ZIP/asset store/ownership 04/04A, renderer/preview/export pada segmen pemilik, layout evaluator 13, acceptance GUI/MCP 22. Bounds domain bersifat konservatif dan bukan bukti painted pixels.
- Aman melanjutkan fondasi ke 03 setelah instruksi segmen tersebut diberikan; 03 tetap `not_started` dan tidak dikerjakan otomatis.

## Checkpoint segmen 00

| ID | Lingkup | Status | Bukti dan sisa |
| --- | --- | --- | --- |
| 00A | Audit repository, batas modul dan keputusan runtime | verified | Inventaris baseline; arsitektur + ADR ditinjau terhadap PRD 6–9/11–13/17/20; accepted berarti desain saja |
| 00B | Baseline spesifikasi normatif native dan pencocokan keputusan | verified | Atas otorisasi pengguna, spesifikasi baru 1.0 + ADR 0010; contoh dua page dengan text/token/font/embedded asset; audit positif dan 13 negatif lulus. Native codec/schema produksi tetap belum diimplementasikan |
| 00C | Pemilik kebutuhan dan roadmap | verified | Audit ID FR-001–033, NFR-001–005, AT-01–34, deliverables dan tools; semua punya owner, status implementasi belum dimulai |
| 00D | Audit dokumen dan handoff | verified | Audit cakupan/status/link lokal dan gate spesifikasi diselaraskan; hasil awal gagal B-001 dicatat historis, hasil setelah penutupan dicatat pada log. Tidak ada klaim perilaku aplikasi |

Status sah: `not_started`, `in_progress`, `implemented_pending_verification`, `verified`, `blocked`, `not_included`. Induk verified hanya jika semua checkpoint mandatory verified. P0 wajib tidak dapat not_included. Bukti dokumen tidak menaikkan status fitur; fitur yang kodenya ada tetapi belum diuji memakai implemented_pending_verification. Mesin rilis yang belum tersedia dicatat pending tanpa menghentikan kerja independen.

## Roadmap berurutan

Urutan berasal dari indeks roadmap, bukan instruksi otomatis. Checkpoint08 pada baseline08; `08`, `10`, `18`, `19`, `31`–`33`, `36`–`40`, `42` adalah induk dan tidak verified sebelum anak wajibnya. Integrasi pada tiap fitur mencakup serialization, command undo/revision, shared drawing dan export; bila subsistem belum tersedia, catat pending sampai pemiliknya dijalankan.

| ID | Hasil yang dimiliki | Status | Prasyarat/gate utama |
| --- | --- | --- | --- |
| 00 | Keputusan arsitektur dan traceability | verified | 00A–00D; lingkup dokumentasi, bukan fitur aplikasi |
| 01 | src/pyproject, uv lock, separate entries, logging/pytest/pytest-qt/lint/type/CI/check.ps1/run.ps1 | verified | Bukti lokal di baseline-segment01.md; 10 tes, build/install wheel, lint/type; CI remote dan inspeksi GUI belum dijalankan |
| 01A | Spike executable window minimal | verified | PyInstaller 6.22.3; artifact native title/close exit 0; baseline-segment01a.md + ADR 0011; Windows bersih pending 24 |
| 02 | Domain, geometry, token minimum, typed schema/fixtures/migration registry | verified | Baseline 02; 193 core + 5 desktop tests; no Qt, final + legacy 1.0 fixtures, typed/JSON schemas, full offline gate dan installed wheel lulus |
| 03 | Dispatcher, atomic batch, revision/history/dedup/asset staging ports | verified | Baseline 03 + ADR 0013; 37 tes command, 230 core/5 desktop, full offline gate; adapter store/layout/GUI/MCP tertunda sesuai pemilik |
| 04 | Codec .ltechdesign, asset store, atomic save/ownership/baseline | verified | Baseline 04 + ADR 0014; 87 tes baru, 317 core/5 desktop, full offline gate/wheel portability/executable offscreen lulus; 04A tetap terpisah |
| 04A | Dua proses nyata ownership/crash/external-change/Save As | verified | Baseline 04A: 7 real-process tests, 324 core/5 desktop, full offline gate lulus; GUI/MCP 19B/22 pending |
| 05 | Main window/tabs/session registry/New/Open/Import/Save/Close/accessibility dasar | verified | Shell/lifecycle + 4 GUI tests; final 324 core/9 desktop, visual DPR1/1.5/2; baseline 05 |
| 06 | Shared renderer dasar dan pan/zoom | verified | Baseline 06 + ADR 0016; 7 renderer tests; 324 core/16 desktop + full gate/spike/demo; 06A next |
| 06A | Canvas/PNG/PDF/offscreen fixture shared drawing | verified | Baseline 06A + ADR 0017; actual fixture/PDF fallback/text outline proof; 324 core/19 desktop, full gate + executable spike |
| 07 | Artboard presets/drawing/selection | verified | Baseline07 + ADR0018; 344 core/46 desktop full gate, 27 GUI native, visual canvas/dialog dan executable offscreen spike |
| 08 | Transform/clipboard/group/undo/nudge/z-order, AT-24 | verified | Baseline08 + ADR0019 historis;08.layout ditutup13 dengan atomic parent layout/constraints, pointer resize/text/undo/native/shared drawing. Baseline13/full gate/native regression lulus; target GUI100ms tetap pending23 |
| 09 | Pages/layers/search/reorder/reparent | verified | Baseline09+ADR0020;18targeted/10native,360core+63desktop full gate, visual native dan executable spike; tidak menutup08.layout |
| 10 | Inspector/style dan snapping/alignment | verified | 10A verified +10B verified; baseline10A/10B, ADR0021/0022 dan full gate/spike |
| 10A | Inspector/style/color/basic shadow | verified | Baseline10A+ADR0021;34targeted/18native,376core+81desktop full gate; screenshot native, wheel shadow probe dan executable spike lulus |
| 10B | Rulers/grid/snap/smart guides/alignment/distribution | verified | Baseline10B+ADR0022;58targeted/47native,405core+110desktop full gate; DPR1/1.5/2/visual/wheel/executable spike |
| 11 | Text inline, fonts/shared layout/fallback warning | verified | Baseline11+ADR0023;27targeted/28native,418core+124desktop full gate, local/embedded restore dan shared PNG/PDF; packaging/wheel spike lulus |
| 12 | Raster/SVG/import/crop/replace/asset retention | verified | Baseline12/ADR0024;38targeted/53native,420core+160desktop full gate/wheel/executable codecs; portable embedded media, shared vector drawing/undo/GC,36MP cancellation dan baseline shapes/mixed diulang; performance1000 pending23 |
| 13 | Stack/constraints fixed/hug/fill dasar atomik | verified | Baseline13/ADR0025;459core+167desktop,46targeted/22native, native Inspector/PNG/PDF visual dan wheel/executable spike; batas advanced28 eksplisit |
| 14 | Recent/duplicate/autosave/recovery/checkpoint/thumbnail/font metadata | not_started | 13 |
| 15 | PNG/JPG/WebP job/service/dialog/codec fallback | not_started | 14 |
| 16 | PDF single/multipage ukuran berbeda P0 | not_started | 15 |
| 17 | Preview/headless CLI/render artifacts | not_started | 16 |
| 17A | Subprocess command → GUI owner → canvas → undo/revision spike | not_started | 17; sebelum 18 |
| 18 | Headless stdio MCP | not_started | 18A, 18B, 18C |
| 18A | SDK schemas seluruh registry; working discovery/bounded reads/resources | not_started | 17A; versi SDK/protocol aktual |
| 18B | Working mutation/pages/groups/assets/tokens/staged batch | not_started | 18A |
| 18C | Working preview/save/export/jobs/status/cancel/transfer | not_started | 18B; seluruh P0 tools pada mode yang didukung |
| 19 | Attached mode integration | not_started | 19A, 19B |
| 19A | Bridge lifecycle/session/selection/status/shutdown | not_started | 18, 17A |
| 19B | Concurrency/retry/two-process ownership/GC | not_started | 19A; ulang baseline ringan |
| 20 | Service security/allowlist/canonical paths/import/payload/IPC audit | not_started | 19 |
| 21 | Optional loopback Streamable HTTP | not_included | Default-off; hanya jika pengguna memasukkannya, setelah 20 |
| 22 | Acceptance integration AT-01–29 dan AT-31–34, fixture poster/web, real client | not_started | 20; 21 jika diaktifkan; bukan otomatis siap rilis |
| 23 | Comprehensive startup/frame/batch/memory/heavy-export benchmark | not_started | 22; evidence menentukan penutupan NFR-001 dan gate P0 penuh |
| 24 | Windows x64 bundled build/installer, AT-30 | not_started | 23; ulang 01A/06A sesuai dependency/packaging; mesin bersih belum disiapkan |
| 25 | Docs/user/developer/MCP/Codex configs dan release smoke | not_started | 24; gate siap rilis berbeda dari selesai fitur |
| 26 | Token UI/bindings/aliases/theme variables P1 | not_started | 22 verified + gate MVP; release blocker 24/25 tidak memblokir fitur independen |
| 27 | Components/instances/override/library lokal | not_started | 26 |
| 28 | Advanced nested layout/min-max/constraints | not_started | 13, 26; 27 untuk instance integration |
| 29 | Pen/Bézier/path/caps/joins/dash | not_started | 22, 02, 06, 08 |
| 30 | Boolean/masks/flatten | not_started | 29 |
| 31 | Advanced typography | not_started | 31A, 31B |
| 31A | Rich spans/styles/auto-fit | not_started | 11, 22 |
| 31B | Variable font/text-on-path | not_started | 31A, 29 |
| 32 | Image adjustment dan creative styling | not_started | 32A, 32B |
| 32A | Non-destructive brightness/contrast/hue/saturation/blur/grayscale/mask | not_started | 12, 22 |
| 32B | Gradients/eyedropper/blend/presets/licensed icons | not_started | 10, 12, 22 |
| 33 | Print/templates/batch export | not_started | 33A, 33B, 33C |
| 33A | Advanced print units/bleed/safe area/raster resolution | not_started | 04, 14, 15, 16, 22 |
| 33B | Local templates → new remapped project | not_started | 04, 14, 22 |
| 33C | Preset/batch output naming/progress/cancel/partial errors | not_started | 15, 16, 22 |
| 34 | HTML/CSS/assets/CSS tokens/semantic responsive subset | not_started | 26, 28; 27 jika instances dipakai |
| 38 | Clipboard, guides dan preferences P1 | not_started | 38A, 38B |
| 38A | Windows image clipboard/in-place actions | not_started | 08, 12, 22 |
| 38B | Persisted undoable non-export guides/palette/preferences | not_started | 10B, 22 |
| 39 | Recovery/history productivity P1 | not_started | 39A, 39B |
| 39A | Session restore/missing dependencies/relink | not_started | 03, 04, 14, 22 |
| 39B | History UI/named snapshots/retention | not_started | 03, 04, 14, 22 |
| 40 | AI dry-run dan diagnostics P1 | not_started | 40A, 40B |
| 40A | Preview operations without live mutation | not_started | 18, 19, 20, 22 |
| 40B | analyze_design bounds/missing refs diagnostics | not_started | 18, 19, 20, 22; bukan accessibility audit |
| 41 | SVG export subset with embedded assets/report | not_started | 16, 22; 29/30 jika path/boolean digunakan |
| 42 | Diagnostics dan UI accessibility P1 | not_started | 42A, 42B |
| 42A | Redacted local diagnostic bundle | not_started | 05, 20, 22 |
| 42B | Keyboard/screen-reader/High DPI editor audit | not_started | 05, 22; palette bila 38B ada |
| 35 | Interactive prototype P2 | not_started | 22; 27 jika component states |
| 36 | Plugin API dan PDF import P2 | not_started | 36A, 36B; keduanya independen |
| 36A | Versioned trusted plugin API/capabilities/lifecycle/error isolation | not_started | 22; tidak mengklaim Python sandbox |
| 36B | PDF multipage raster preview + editable subset fidelity spike | not_started | 22; 36A hanya jika importer dipaketkan plugin |
| 37 | Advanced capabilities P2 | not_started | 37A, 37B, 37C, 37D |
| 37A | Brush/erase raster vertical slice with source/undo | not_started | 12, 32A, 22 |
| 37B | Design accessibility analysis (contrast/text/semantics) | not_started | 40B, 22 |
| 37C | One advanced codegen target above HTML/CSS | not_started | 34, 22 |
| 37D | Optional desktop AI adapter with consent/preview/apply/undo | not_started | 19, 20, 40A, 22; credentials/dokumentasi provider diperlukan |

Jalur handoff: 22 → 26 → 28 → 34, dengan 27 jika instances digunakan. Jalur vektor 29 → 30 independen dari handoff. P1/P2 setelah gate MVP dan prasyarat teknis, tidak harus menunggu mesin distribusi bersih. 22 dapat verified untuk lingkup acceptance-nya sementara G-MVP tetap menunggu seluruh bukti P0 termasuk performance 23; ini menghindari siklus prasyarat 22/23. Setiap fitur yang masuk versi distribusi memerlukan regresi/build checks yang terdampak.

## Keputusan tertutup dan bukti yang masih terbuka

| Keputusan / bukti belum tersedia | Pemilik | Gate / tindakan |
| --- | --- | --- |
| B-001 (ditutup): spesifikasi awal tidak ada | 00B | Dokumen baru dibuat atas permintaan pengguna; ADR 0010 menetapkan asal-usul dan baseline, audit kontrak lulus. Native example/generator tetap pending 02/04 |
| Implementasi typed validators/JSON Schema, registry migrasi dan seluruh per-node union | 02 | Field/version/capabilities, token binding dan manifest.saved_revision sudah normatif pada spesifikasi 1.0; implementasikan+uji, jangan mengganti dengan ilustrasi PRD |
| Dependency pins dan runtime Python yang kompatibel | 01 | uv lock + tes aktual, catat versi, tidak pin dari contoh |
| Packager/Qt plugins/bundle manifest | 01A | Spike executable nyata; ulang jika dependency berubah; installer 24 |
| Numeric tolerances/minimum dimensions dan stable canonical JSON digest encoding | 02, 03 | Freeze fixture matematika/validator/retry, independent Qt |
| Raster fallback resolution/font baseline/pixel diff tolerances dan font redistribusi | 06A, 11, 24 | Shared artifacts nyata dan license review, tidak menutupi alpha/geometry mismatch |
| Windows aliases/ACL/stale-lock process identity dan named-pipe authentication behavior | 04A, 17A, 20 | Dua proses dan subprocess nyata; desain ownership/thread sudah dipilih |
| Queue/history/memory budgets terhadap hardware acuan | 23 | Ukur baseline 08/12/19B lebih awal, full budget report 23; perubahan budget lewat ADR |
| Mesin Windows bersih dan monitor DPI untuk release evidence | 24, 25 | Pending penyediaan lingkungan; jangan klaim AT-30/high-DPI manual lulus tanpa menjalankan |
| Lingkup kecil P2 yang belum dirinci PRD | 36A, 36B, 37A, 37B, 37C, 37D | Freeze capability/threat model/fidelity di checkpoint masing-masing, tidak memperluas MVP |

Ownership, pivot/group opacity, content/session/job boundaries, monotonic revision, staging save/load dan thread authority **bukan keputusan terbuka**. Integrasi implementasi semuanya masih tertunda ke segmen pemilik pada roadmap.

## Log verifikasi segmen 00

Lingkungan shell PowerShell Windows di workspace `Z:\project\ltechDesign`; host belum dipakai sebagai mesin uji produk. uv 0.12.1 terdeteksi; Python/PySide6/MCP belum diinstal atau diuji. Pemeriksaan command discovery tidak menemukan python/py pada PATH, sehingga tidak ada klaim runtime Python 3.12 lulus.

| Perintah / pemeriksaan | Hasil aktual |
| --- | --- |
| `git ls-files`; `git log -1 --format='%h %s'`; `git status --short` | Baseline 54162c5, dua dokumen tracked, awal sesi clean; file baru segmen 00 belum di-commit |
| `rg` headings/IDs + pembacaan UTF-8 bagian PRD/roadmap terkait | Inventaris FR 33/NFR 5/AT 34, contracts 20.1–20.9 dan deliverables 13 ditemukan |
| `Test-Path scripts/check.ps1` | False; subsystem runner belum tersedia (pemilik 01) |
| `uv --version` | uv 0.12.1; bukan tes dependency aplikasi |
| Audit awal `scripts/check-segment00.ps1` sebelum spesifikasi dibuat | Historis: exit 0 untuk cakupan/status/link; 184 baris, 79 segmen/checkpoint, 37 tools, 13 Markdown; B-001 dilaporkan |
| Gate awal `scripts/check-segment00.ps1 -RequirePrerequisites` | Historis: exit 1 khusus B-001. Digantikan hasil setelah spesifikasi baru dibuat di bawah, bukan disembunyikan sebagai lulus sejak awal |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-file-format-spec.ps1` | Exit 0: contoh dua page/6 node, hierarchy/ref/token/font/runtime exclusions dan inventory/embedded SHA-256 valid; 13 kasus negatif ditolak dengan reason yang sesuai. Invariants terpilih saja, bukan full schema/ZIP loader; dijalankan juga oleh prerequisite gate |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-segment00.ps1` setelah penutupan B-001 | Exit 0: 184 baris matriks, 79 segmen/checkpoint, 37 tools MCP, 15 Markdown; pemilik/status/P0/link lokal valid. Semua FR/NFR/AT produk tetap belum verified |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-segment00.ps1 -RequirePrerequisites` setelah penutupan B-001 | Exit 0: audit kontrak positif dan 13 negatif lulus, disusul audit cakupan/link/status. B-001 ditutup pada lingkup spesifikasi dokumentasi |
| .NET System.Drawing decode atas embedded example PNG | Gambar 1×1 berhasil dibaca; 68 byte, SHA-256 8b3634ccad5be602a2f51ab1a9b33b3e9826082d2ee187236f6b7916000ec93b. Ini pemeriksaan fixture, bukan visual renderer Qt |
| `git diff --check` + whitespace check file baru melalui audit | Exit 0; diff tracked kosong karena file baru belum tracked, sehingga whitespace/link/UTF-8 file baru diperiksa oleh audit |
| PowerShell AST Parser `ParseFile` untuk kedua script audit; whitespace seluruh docs/scripts | Exit 0: kedua script tanpa syntax error; seluruh file docs/scripts tanpa trailing whitespace. Tidak ada source/lint/type aplikasi yang dijalankan |

Review dokumen terhadap sumber resmi: dataclasses Python 3.12, Qt QLockFile/QLocalServer/Threads and QObjects, dan official MCP Python SDK; tautan dicatat di architecture. Review API bukan eksekusi runtime atau bukti versi kompatibel. Tidak ada perubahan dependency/rendering/packaging yang diimplementasikan, sehingga spike 01A/06A/17A belum dijalankan.

Tes otomatis aplikasi, lint/type aplikasi: belum ada konfigurasi/source dan tidak dijalankan. Pemeriksaan visual Qt/canvas/PDF: tidak dilakukan, belum ada aplikasi. Manual GUI belum dapat dilakukan; skenario yang harus dijalankan pemilik segmen: dua tab/copy document ID, New→Open/Import→edit→Save As→close/reopen, second-process ownership dan external replacement, group nested rotation/overlap opacity, DPI 100/150/200% antar-monitor, lost MCP response retry, cancel job sebelum/sesudah commit. Segmen 00 hanya memverifikasi dokumen dan mapping; seluruh bukti perilaku tetap pending.


## Handoff segmen 01

21 Oktober 2026: fondasi runtime diuji dengan Python 3.12.12, PySide6/Qt 6.10.2 dan uv 0.12.1. Tidak ada perubahan status fitur editor/AT produk. scripts/check.ps1 hanya menawarkan subsistem yang tersedia; schema/migration/visual belum menjadi gate palsu. Fixture font Abel SIL OFL 1.1 disertakan, generator memeriksa hash dan drift. Detail perintah, hardware/display dan batas pembuktian ada di README dan baseline-segment01.md.


## Handoff segmen 01A

21 Oktober 2026: scripts/smoke-build.ps1 membangun bundle Windows minimal lalu menjalankan artifact aktual. Native title/handle, loaded runtime dari bundle dan WM_CLOSE/exit 0 tercatat; offscreen juga lulus. Dependency packaging terkunci di group packaging. Bukti dan batas ada di baseline-segment01a.md serta ADR 0011. Tidak ada installer atau UI editor baru; segmen 24 wajib mengulang smoke pada Windows bersih.
