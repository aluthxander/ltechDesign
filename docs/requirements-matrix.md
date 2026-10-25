# Matriks kebutuhan ltechDesign Studio

Acuan PRD 1.2, 21 Oktober 2026. Pemilik segmen mengikuti indeks `promt_managemnet.md`; tabel ini bukan instruksi menjalankan segmen tersebut. Update 01: fondasi package/window minimal telah diuji; fitur aplikasi lengkap belum tersedia. `not_started` tetap dipakai walaupun arah desain sudah didokumentasikan. B-001 ditutup pada lingkup dokumentasi: spesifikasi format baru dibuat atas permintaan pengguna, bukan dipulihkan dari sumber historis. Status fitur/AT tidak dinaikkan oleh ADR atau audit dokumen.

Kolom Pemilik adalah penanggung jawab utama, kolom Integrasi/verifikasi menyebut pekerjaan pendukung dan gate. Semua ID segmen terdaftar di [progress.md](progress.md). `P0/P1` memuat kewajiban kedua prioritas; rincian P0 tidak boleh menunggu P1. Status yang sah: not_started, in_progress, implemented_pending_verification, verified, blocked, not_included.

Update 03 (22 Oktober 2026): dispatcher domain dan kontrak retention terverifikasi di
[baseline 03](baseline-segment03.md). Baris kebutuhan lintas GUI/MCP/store/layout
tetap `in_progress` sampai integrasi pemilik selesai; tes domain tidak menaikkan
acceptance produk end-to-end menjadi verified.

Update 04 (23 Oktober 2026): codec ZIP produksi, portability, byte admission,
atomic save/ownership, duplicate/remap dan real retention store memiliki bukti
fondasi pada [baseline 04](baseline-segment04.md). AT-31–34 tetap `in_progress`
sampai integrasi GUI/renderer/font/layout pada segmen pemilik; 04A dua proses
belum dijalankan. Tidak ada klaim restore UI dari tes persistence.

Update 04A: tujuh tes dua proses nyata lulus, dicatat di
[baseline 04A](baseline-segment04a.md). AT-21/22/26 fondasi terbukti; status
acceptance penuh tetap in_progress sampai integrasi GUI/MCP 19B/22.

## Gate

| ID | Prioritas/gate | Pemilik | Integrasi/verifikasi | Status | Bukti / kriteria selesai |
| --- | --- | --- | --- | --- | --- |
| G-MVP | P0 / MVP fungsional | 22 | 01A, 04A, 06A, 17A, 18A, 18B, 18C, 19A, 19B, 20, 23 | not_started | Seluruh P0, AT-01–AT-29 dan AT-31–AT-34; empat format export; manual GUI + subprocess MCP/Codex; target performance diukur 23 |
| G-FEATURE | Semua fitur roadmap | 25 | 22, 26, 27, 28, 29, 30, 31A, 31B, 32A, 32B, 33A, 33B, 33C, 34, 35, 36A, 36B, 37A, 37B, 37C, 37D, 38A, 38B, 39A, 39B, 40A, 40B, 41, 42A, 42B | not_started | Lingkup fitur selesai hanya jika masing-masing kebutuhan dan checkpoint termasuk P1/P2 yang dijadwalkan punya bukti; MVP tidak berarti seluruh roadmap selesai |
| G-RELEASE | P0 / siap distribusi | 25 | 22, 23, 24 | not_started | Gate MVP, installer/runtime bundled, AT-30 Windows bersih tanpa Python dev, dokumen/lisensi/capability aktual; fitur tambahan yang disertakan wajib regresi |

Mesin rilis yang belum tersedia membuat bukti AT-30 pending, bukan verified dan bukan penghalang fitur independen. HTTP opsional tidak disertakan. P0 wajib tidak boleh not_included. `verified` lingkup dokumen 00 tidak memenuhi gate produk di atas.

## Kebutuhan fungsional

| ID | Prioritas/gate | Pemilik | Integrasi/verifikasi | Status | Bukti / kriteria selesai |
| --- | --- | --- | --- | --- | --- |
| FR-001 | P0 | 14 | 04, 05, 09, 22 | in_progress | 05 lifecycle/tab +09 page CRUD/duplicate/artboard list dan editable restore tersedia; recent/autosave/recovery/duplicate project UI14 serta acceptance22 tetap pemilik |
| FR-002 | P0 | 04 | 00B, 02, 05, 14, 22 | in_progress | 04: codec ZIP/JSON + embedded bytes, inventory/schema/hash, portability dan atomic save teruji fondasi; GUI/native acceptance 05/14/22 pending |
| FR-003 | P0 | 08 | 03, 06, 07, 09, 10B, 11, 22 | in_progress | 08 transform/history/clipboard/nudge +09 hierarchy;10B rulers/grid/world snap/smart guides dan align/distribute tersedia, 10B verified:58targeted/47native,405core+110desktop/full gate/spike, DPR1/1.5/2; overlay-free PNG/PDF/native roundtrip lulus. Frame layout13/full22 tetap pemilik |
| FR-004 | P0 | 07 | 02, 08, 13, 16, 22 | verified | 07: 11 preset PRD/custom px/mm/cm/in, orientasi/DPI/background, data editable dan ukuran akurat; 20 tes core/27 GUI, full gate dan visual native; integrasi layout13/export16/acceptance22 tetap pemilik |
| FR-005 | P0 | 09 | 03, 05, 08, 22 | verified | 09: nested tree/selection dua arah, name/type search, rename/duplicate/hide-lock, actual Qt drag/reorder/reparent via dispatcher dan external-command projection;18targeted+10native,360core/63desktop full gate dan visual native lulus; acceptance22 diulang |
| FR-006 | P0 | 07 | 02, 06, 08, 11, 12, 22 | in_progress | 07: frame/rectangle/ellipse/line/polygon;08 group/ungroup dan transform/clipboards teruji. Text11/image/SVG12 pending; tanpa dummy tools |
| FR-007 | P1 | 29 | 30, 41 | not_started | Pen/Bézier/path edit, cap/join/dash; boolean/masks/flatten di 30 |
| FR-008 | P0 | 10A | 08, 10B, 11, 13, 15, 16, 22 | in_progress | 10A geometry/style/shadow/color/Mixed terhubung dispatcher/model/canvas/native/PNG/PDF proof; 10A verified;10B align/distribute dan canvas/Inspector/undo sync verified,405core+110desktop/full gate/spike lulus; text/constraints/export Inspector lengkap tetap11/13/15–17 |
| FR-009 | P0 | 11 | 02, 04, 06A, 15, 16, 17, 22 | not_started | Font lokal, size/weight/italic, multiline/alignment/line spacing/letter spacing, text bounds/auto size, Unicode/emoji sesuai capabilities |
| FR-010 | P1 | 31A | 11, 29, 31B | not_started | Rich spans/global styles/auto-fit; fallback/substitution metadata aman; variable font dan text-on-path 31B |
| FR-011 | P0 | 12 | 04, 06, 15, 16, 22 | not_started | Raster/SVG subset, dialog/drop, fit/fill/stretch/crop/rounded clip, rotate/opacity, replace container tetap |
| FR-012 | P1 | 32A | 12, 32B, 36A | not_started | Non-destructive adjustment/masking; background removal opsional plugin, core tidak bergantung layanan |
| FR-013 | P0/P1 | 13 | 02, 03, 08, 11, 28, 34, 22 | not_started | P0 stack/padding/gap/alignment/fixed/hug/fill/constraints dasar; advanced nested/min-max 28 |
| FR-014 | P1 | 27 | 26, 28, 34 | not_started | Master/instances/overrides/propagation/detach/library lokal, referensi/cycle aman |
| FR-015 | P0/P1 | 26 | 02, 04, 18A, 18B, 22 | not_started | P0 token minimum dimiliki TOK-P0; P1 UI token/binding/alias/themes dan komponen design system di 26/27 |
| FR-016 | P2 | 35 | 22, 27 | not_started | Click/navigation/hover/transitions/preview tanpa menjalankan script pengguna |
| FR-017 | P0 | 22 | 07, 08, 10A, 10B, 11, 12, 13, 15, 16 | not_started | Fixture poster/banner/social/thumbnail/infografis/brosur/sertifikat/presentasi memakai fitur editor, bukan generator contoh PRD |
| FR-018 | P0/P1 | 32B | 10A, 10B, 12, 30, 32A, 33B, 22 | in_progress | P0 color picker/solid fill/stroke/shadow/alignment-distribution10A/10B verified; P1 gradient/eyedropper/blend/presets/icon 32B, masks 30/32A, template 33B |
| FR-019 | P0/P1 | 33A | 07, 16, 22 | not_started | P0 multipage PDF 16; P1 mm/cm/inch/DPI/bleed/safe margin/raster resolution, text/vector sejauh supported; tanpa janji CMYK/ICC/PDF-X |
| FR-020 | P0 | 15 | 16, 17, 18C, 22 | not_started | Artboard/selection/all artboards, scale/custom size/DPI, background/quality/naming/folder/progress/error |
| FR-021 | P1 | 33C | 15, 16, 18C | not_started | Preset/batch export, collisions/cancel/partial per-output report; dasar all-artboards P0 tetap 15/16 |
| FR-022 | P0 + HTTP opsional | 18A | 17A, 18B, 18C, 19A, 20, 21, 22 | not_started | Stdio, start/stop/status/log/discovery; HTTP conditional di HTTP-OPTIONAL |
| FR-023 | P0 | 18A | 17, 18C, 19A, 22 | not_started | Metadata/tree/nodes/tokens/assets/selection dan preview bounded dengan identity/revision |
| FR-024 | P0 | 18B | 03, 12, 18C, 19A, 22 | not_started | Manipulation/page/group/reorder/assets memakai dispatcher; save/export side effects 18C |
| FR-025 | P0 | 03 | 18B, 19B, 22 | in_progress | 03 verified: typed dispatcher, validation/error, atomic batch, revision/history/undo/redo; rollback/event tests lulus. Integrasi transport/acceptance 18/19/22 pending |
| FR-026 | P0 + HTTP kondisional | 20 | 04, 12, 17A, 18A, 18B, 18C, 19A, 21, 22 | not_started | Allowlist/canonical paths, payload limits, no shell/script, local consent/audit/disable; HTTP token/Host/Origin jika disertakan |
| FR-027 | P0 | 04A | 04, 05, 14, 19B, 20, 22 | in_progress | 04: canonical single writer/baseline/Save As/read-only dan stale metadata check; session terpisah. 04A dua proses/crash/case/.. dan hardlink verified; GUI/MCP dan audit platform luas pending |
| FR-028 | P0 | 03 | 04, 14, 18B, 18C, 19B, 22 | in_progress | 03/04: content union/checkpoints/history/retry + real blob staging/retention undo/redo dan job/recovery leases teruji; scheduler/transport/persistent recovery pending |
| FR-029 | P0 | 18C | 17, 18A, 19A, 20, 22 | in_progress | 04: archive/asset/decode limits dan save cancellation barrier teruji; query cursor, preview/TTL, scheduler/status/cancel/backpressure tetap 17–22 |
| FR-030 | P0/P1 | 38A | 05, 08, 10B, 11, 38B, 42B, 22 | in_progress | 08: nudge1/10px dunia, sibling z-order dan shortcut aman pada input teks diuji. 10B actual Qt DPR1/1.5/2+zoom0.5/1/2/4 pada snapping/rulers/Inspector diuji; HighDPI fisik22/24, image clipboard/in-place38A dan guides/palette/preferences38B pending |
| FR-031 | P1 | 39A | 03, 04, 14, 39B | not_started | Restore/missing dependency manager/relink; history UI/named snapshots/retention 39B |
| FR-032 | P1 | 40A | 18B, 18C, 19A, 41 | not_started | Dry-run isolation/base revision/apply recheck; SVG handoff di 41 |
| FR-033 | P0/P1 | 42A | 00A, 00C, 01, 01A, 06A, 17A, 25, 42B | in_progress | Fondasi docs/checks/handoff 00/01 tersedia dan diuji lokal; diagnostic bundle/redaction P1 42A dan bukti fitur berikutnya belum ada |

## Kebutuhan non-fungsional

| ID | Prioritas/gate | Pemilik | Integrasi/verifikasi | Status | Bukti / kriteria selesai |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | P0 | 23 | 01A, 06A, 08, 12, 19B, 22, 24 | in_progress | Dua baseline08 warm native10detik disimpan; terbaru100pan/drag p95~16,5ms;1000pan-selection p99=48,04ms/gapmax53,30ms; commit100=49,16ms. GUI heartbeat110,69–111,07ms gagal target100ms; comprehensive/reference hardware/cold/leak checks23 tetap pending |
| NFR-002 | P0 | 14 | 02, 03, 04, 04A, 22 | in_progress | 02–04 schema/undo/atomic replace dan backup-before-migration mechanism teruji; autosave/recovery dan crash integration 04A/14/22 pending |
| NFR-003 | P0 | 20 | 04, 12, 18A, 18B, 18C, 19A, 22 | not_started | Offline/no account/no auto upload, untrusted import guarded, no embedded scripts, project permissions |
| NFR-004 | P0 | 01 | 00A, 00C, 02, 03, 04, 18A, 22, 24, 25 | in_progress | Modular/types/tests/integration/structured logs/CI/build/versioned schema+contracts; docs 00 bukan bukti kode |
| NFR-005 | P0 / release | 24 | 01A, 06A, 25 | not_started | Windows x64 bundled runtime/installer/no Python dev, settings per-user, projects terpisah install; AT-30 wajib |

## Acceptance tests

| ID | Prioritas/gate | Pemilik | Integrasi/verifikasi | Status | Bukti / kriteria selesai |
| --- | --- | --- | --- | --- | --- |
| AT-01 | P0 / MVP | 07 | 22 | verified | 07: dialog preset menghasilkan artboard1080×1350 tepat, drawing lima tools dan Save/close/Open editable; native dan offscreen lulus; ulang fixture acceptance penuh22 |
| AT-02 | P0 / MVP | 11 | 06A, 07, 22 | not_started | Rectangle dan text nyata tampil canvas |
| AT-03 | P0 / MVP | 08 | 10A, 22 | in_progress | 08: resize/rotate handles sinkron ke model, anchor/pivot/parent rotations dan undo diuji; Inspector geometry10A verified termasuk nested parent-space input/undo; layout13/acceptance22 pending |
| AT-04 | P0 / MVP | 08 | 03, 09, 22 | verified | Lingkup08: GUI group/ungroup, hierarchy/undo tepat, world pose dan actual PNG tetap; preserve-appearance menolak stacking/clip/isolation yang tak representable. Full fixture22 tetap diulang |
| AT-05 | P0 / MVP | 04 | 05, 14, 22 | not_started | Save/reopen struktur sama |
| AT-06 | P0 / MVP | 03 | 08, 22 | in_progress | 03/08: real GUI delete group subtree+undo/redo memulihkan hierarchy/style, nested normalization, redo branch dibuang setelah command baru; acceptance22 pending |
| AT-07 | P0 / MVP | 15 | 06A, 22 | not_started | PNG alpha benar |
| AT-08 | P0 / MVP | 15 | 22 | not_started | JPG flatten background, tanpa alpha |
| AT-09 | P0 / MVP | 15 | 22 | not_started | WebP decode kembali, capability/fallback diuji |
| AT-10 | P0 / MVP | 16 | 06A, 22 | not_started | PDF multipage jumlah/ukuran/urutan akurat |
| AT-11 | P0 / MVP | 18A | 19A, 22 | not_started | Client Codex membaca layer sebenarnya |
| AT-12 | P0 / MVP | 19A | 18B, 22 | not_started | MCP create tampil canvas dan GUI undo |
| AT-13 | P0 / MVP | 19A | 10A, 18B, 22 | not_started | MCP warna sinkron model/renderer |
| AT-14 | P0 / MVP | 18B | 03, 19B, 22 | in_progress | 03: tengah batch/final validation/layout/prepare/cancel gagal tidak mengubah konten/history/revision/events; staging double dibersihkan. Real store/MCP pending |
| AT-15 | P0 / MVP | 19B | 03, 18B, 22 | in_progress | 03: stale revision ditolak tanpa overwrite; GUI/MCP dua proses 18/19/22 pending |
| AT-16 | P0 / MVP | 18C | 15, 16, 20, 22 | not_started | MCP export ke path diizinkan |
| AT-17 | P0 / MVP | 14 | 04, 22 | not_started | Crash sebelum manual save, recovery tersedia |
| AT-18 | P0 / MVP | 04 | 02, 05, 22 | not_started | Malformed file controlled error, tab utuh |
| AT-19 | P0 / MVP | 20 | 18A, 18B, 18C, 22 | not_started | Akses path terlarang ditolak semua jalur |
| AT-20 | P0 / MVP | 17 | 06A, 11, 12, 22 | not_started | Headless/canvas sebanding, toleransi ditetapkan dan artifacts diperiksa |
| AT-21 | P0 / MVP | 19B | 04A, 05, 22 | in_progress | 04A verified fondasi: dua proses writer/reject/read-only, close/crash/stale dan source/target Save As locks; GUI/attached tetap 19B/22 |
| AT-22 | P0 / MVP | 19B | 04A, 05, 14, 22 | in_progress | 04A verified fondasi: external replace identik/berbeda memicu conflict tanpa overwrite; Save As gagal/sukses nyata; GUI Reload/recovery tetap 05/14/19B/22 |
| AT-23 | P0 / MVP | 19B | 03, 18B, 18C, 22 | in_progress | 03: retry lama mendahului stale check, cached error, conflict, shared Future dan restart boundary teruji; lost-response transport/jobs pending |
| AT-24 | P0 / MVP | 08 | 02, 03, 06A, 09, 22 | verified | 08 core+GUI native/offscreen: group/reparent rotated parents/ungroup mempertahankan world matrices dan PNG maxdelta1/255; undo project/hierarchy tepat, invalid compositing context ditolak atomik. Full acceptance22 diulang |
| AT-25 | P0 / MVP | 19B | 04, 12, 14, 18B, 22 | in_progress | 03: retention conformance double menahan live/undo/redo/external leases saat GC; real byte store/replace image/recovery/transport pending |
| AT-26 | P0 / MVP | 19B | 04A, 05, 22 | in_progress | 04A verified fondasi: dua copy document_id sama, session_id/lock/save/reopen independen; multi-tab routing/history GUI/MCP tetap 19B/22 |
| AT-27 | P0 / MVP | 05 | 06, 07, 08, 22, 24 | in_progress | 10B native Qt actualDPR1/1.5/2, four zooms snapping/handles/ruler/Inspector dan PNG/PDF diuji; OS Windows100/150/200% fisik/pindah monitor/clean release tetap22/24 pending |
| AT-28 | P0 / MVP | 18A | 19A, 22 | not_started | Cursor revision lama stale_cursor, query restart |
| AT-29 | P0 / MVP | 18C | 12, 14, 15, 16, 17, 19A, 22 | not_started | Cancel heavy job sebelum/sesudah barrier, UI responsif, staging bersih |
| AT-30 | P0 / release | 24 | 25 | not_started | Windows bersih tanpa Python dev; startup/project/font/codecs/SVG/PDF/stdio MCP; mesin uji belum disiapkan |
| AT-31 | P0 / MVP | 22 | 02, 04, 05, 13, 14, 18C, 19A | in_progress | 04 fondasi: dua page/nested/IDs/order/transforms/text/style/token bindings + dispatcher edit-save-undo; layout solver/GUI Import/MCP pending |
| AT-32 | P0 / MVP | 22 | 04, 11, 12, 14 | in_progress | 04: pindah file, hapus sumber bytes dan load tanpa network/cwd dependency; embedded bytes sama. Font resolution/fallback warning dan GUI pending 11/22 |
| AT-33 | P0 / MVP | 22 | 02, 04, 05 | in_progress | 04: malformed manifest/hash/missing assets/version/capability ditolak tanpa admission/model/lock parsial; tab GUI belum tersedia 05 |
| AT-34 | P0 / MVP | 22 | 02, 04, 06A, 11, 12, 13, 14 | in_progress | 04: repeated native semantic/byte round-trip, runtime excluded, opaque/workspace/thumbnail preservation; preview visual/advanced fixtures pending |

## Kontrak PRD bagian 20 dan keputusan lintas subsistem

Setiap baris memiliki acceptance owner; kontrak desain yang sudah ditulis tidak membuat status implementasinya verified.

| ID | Prioritas/gate | Pemilik | Integrasi/verifikasi | Status | Bukti / kriteria selesai |
| --- | --- | --- | --- | --- | --- |
| C20.1 | P0 | 04A | 04, 05, 14, 19B, 20, 22 | in_progress | 04 foundation ownership/path/baseline/identity/Save As/duplicate/stale/close teruji; 04A two-process/crash/Save As verified; GUI/recovery/MCP tetap 05/14/19B/22; ADR 0014 |
| C20.2-UNITS | P0 | 02 | 07, 16, 22 | in_progress | Logical px/physical DPI/screen DPR terpisah;10B8physical-px snap/(zoom*DPR), actualDPR1/1.5/2/four zooms dan literal Inspector/nudge teruji; physical export16/full22 pending |
| C20.2-PIVOT | P0 | 03 | 02, 08, 22 | in_progress | 02/03/08: explicit pivot, world reparent, nested group normalization, GUI anchor resize/rotate/undo dibuktikan; full fixture22 pending |
| C20.2-RESIZE | P0 | 08 | 02, 13, 22 | blocked | 08: positive uniform group/multiselect, frame geometry default fixed tanpa scale anak, zero-extent line/no shear/flip teruji. Evaluator constraints/layout13 belum tersedia; resize frame ber-layout ditolak, tidak dianggap selesai |
| C20.2-BOUNDS | P0 | 06 | 02, 07, 08, 15, 17, 22 | in_progress | Geometry/visual/hit distinct;10A thick centered stroke/square cap/miter dan multiple-shadow bounds teruji; clipped effects/selection export tanpa overlay; public export/acceptance15/17/22 pending |
| C20.2-CLIP | P0 | 06A | 06, 10A, 12, 22 | in_progress | 06A/10A rounded fill/ancestor clip, centered stroke dan radius clamp teruji; image12/full fixture22 pending |
| C20.2-OPACITY | P0 | 06A | 06, 10A, 16, 22 | in_progress | 06A/10A isolated group composite+shadow, Inspector opacity/undo/overlap alpha, shared fallback/PDF raster reporting teruji; production PDF16/full fixture22 pending |
| C20.2-HIERARCHY | P0 | 02 | 03, 08, 09, 22 | in_progress | 02/03/08/09: invariants, page/subtree graph remap, atomic Qt relocation/world pose/undo, layer visibility/lock ancestry dan external-command sync teruji; full acceptance22 pending |
| C20.2-DRAWING | P0 | 06A | 11, 12, 15, 16, 17, 22 | in_progress | One shared drawing fixture nested rotation/overlap/rounded clip/multiline/transparent image/multi-artboard |
| C20.3-TX | P0 | 03 | 13, 18B, 22 | in_progress | 03: prepare/validate/publish atomik, satu revision/event, hook layout rollback teruji; evaluator nyata 13 dan transport 18/22 pending |
| C20.3-STATE | P0 | 05 | 03, 19A, 22 | in_progress | 03: union menolak selection/viewport/save/export, monotonic undo/redo dan semantic checkpoint teruji; session event service 05/19 pending |
| C20.3-IMPORT | P0 | 04 | 03, 12, 18B, 22 | in_progress | 03/04: RegisterAsset + real byte validation/staging/prepare/commit/abort dan GC roots teruji; GUI import/asset rendering/MCP integration 12/18B/22 pending |
| C20.3-DEDUP | P0 | 03 | 18B, 19B, 22 | in_progress | 03: client/session/request scope, canonical digest, retry sebelum revision, shared in-flight Future teruji; authenticated bridge dan reconnect 18/19 pending |
| C20.3-LIFECYCLE | P0 | 18B | 18A, 18C, 19A, 22 | not_started | create_project exception, open admission, selection tanpa revision, save/export snapshot+request/jobs |
| C20.3-RETENTION | P0 | 19B | 03, 18B, 18C, 22 | in_progress | 03: injected-clock tests ≥30 menit, capacity reject, close/reopen/expiry; tidak menjamin exactly-once crash. Real transport/jobs 18/19 pending |
| C20.3-HISTORY | P0 | 03 | 04, 14, 19B, 39B, 22 | in_progress | 03: 128 MiB configurable object-graph charge, whole-entry eviction notice, GUI/AI metadata dan safe retention roots teruji; store/recovery/jobs/UI/benchmark pending |
| C20.4-QUERY | P0 | 18A | 19A, 22 | not_started | Filter/depth/fields/page 100/max500, deterministic session/revision/query cursor |
| C20.4-PREVIEW | P0 | 17 | 18C, 22 | not_started | Artboard/selection/region, source identity/revision/bounds/dimensions/mime, max2048 |
| C20.4-ARTIFACT | P0 | 18C | 17, 22 | not_started | Opaque preview IDs TTL30m/leases; user export tidak dihapus TTL |
| C20.4-TRANSFER | P0 | 18C | 18A, 19A, 22 | not_started | Negotiated image/resource/local access, no assumption cloud reads local path |
| C20.4-JOBS | P0 | 18C | 12, 14, 15, 16, 17, 19A, 22 | not_started | queued/running/succeeded/failed/cancelled, status/cancel/progress/error/snapshot |
| C20.4-CANCEL | P0 | 18C | 04, 15, 16, 17, 22 | not_started | Snapshot/assets held, staging cancel before barrier, no false cancel after commit; per-file temp/replace |
| C20.4-LIMITS | P0 | 20 | 04, 12, 17, 18A, 18B, 18C, 22 | not_started | JSON4MiB/batch100/asset50MiB/decode40MP/archive10k+512MiB/render64MP, reject before large allocation |
| C20.4-TIMEOUT | P0 | 17A | 18C, 19A, 19B, 23, 22 | not_started | 30s timeout bukan rollback, bounded output/queue/backpressure |
| C20.5-SPIKES | P0 | 01A | 04A, 06A, 17A | in_progress | Minimal executable 01A verified lokal (baseline-segment01a.md); two-process ownership 04A verified; shared render/bridge belum diuji; subprocess→GUI mandatory evidence |
| C20.5-BENCH | P0 | 23 | 08, 12, 19B, 24 | not_started | Hardware/OS/scaling/versions/warm-cold; early baselines 08/12/19B, p95/p99/freeze/commit-vs-IPC/render |
| C20.5-MEMORY | P0 | 23 | 03, 04, 06 | not_started | 1.000 shapes target resident≤512MiB outside large raster; repeated open/close and history budget |
| C20.5-FIXTURES | P0 | 02 | 04, 06A, 11, 22 | in_progress | Old schema/migration fixtures, licensed deterministic fonts, geometry/alpha-aware diff artifacts |
| C20.5-CHECKS | P0 | 01 | 01A, 04A, 06A, 17A, 24, 25 | in_progress | scripts/check.ps1 subsystem failure exit, run.ps1/repro fixtures, affected spikes after dependency/render/packaging change |
| C20.5-STATUS | P0 | 22 | 00C, 01, 25 | not_started | Status vocabulary/evidence maintained each segment; separate auto/visual/manual and release |
| C20.6 | P0/P1 | 38A | 05, 08, 10B, 38B, 42B, 22 | in_progress | Base accessibility/nudge/order P0; clipboard/in-place/guides/preferences P1; guides content undoable, not export |
| C20.7 | P1 | 39A | 14, 39B | not_started | Session restore respects writer, relink undoable, history source, local named snapshots/quotas/user deletion consent |
| C20.8 | P1 | 40A | 18B, 18C, 41 | not_started | Dry-run no live/history/permanent asset mutation; apply revision recheck; SVG subset portability/report |
| C20.9 | P0/P1 | 42A | 00A, 00C, 01, 25, 38A, 38B, 39A, 39B, 40A, 40B, 41, 42B | not_started | Development ADR/progress/checks P0; P1 redacted local diagnostics, no auto upload, feature-specific regression evidence |

## Import/export, prioritas yang dipecah, dan deliverables

| ID | Prioritas/gate | Pemilik | Integrasi/verifikasi | Status | Bukti / kriteria selesai |
| --- | --- | --- | --- | --- | --- |
| DOC-FORMAT | P0 / prasyarat dokumentasi | 00B | 02, 04 | verified | Spesifikasi baru docs/ltechdesign-file-format.md + ADR 0010, contoh JSON, audit cross-refs/inventory dan 13 kasus negatif; bukan conformance codec aplikasi |
| FILE-FIXTURE | P0 | 02 | 04, 22 | in_progress | 02/04: historical JSON tetap, native ZIP valid + generator drift/round-trip teruji; PNG lama CRC rusak ditolak produksi; acceptance GUI 22 pending |
| TOK-P0 | P0 | 02 | 03, 04, 18A, 18B, 22 | in_progress | 02–04: token IDs/typed values/JSON, SetTokens materialization dan native bindings round-trip teruji; MCP/acceptance 18/22 pending; UI/alias/themes P1 26 |
| STYLE-P0 | P0 | 10A | 10B, 06A, 15, 16, 22 | in_progress | Editor style10A dan alignment/distribution10B verified;58targeted/47native,405core+110desktop/full gate/spike lulus. Production export15/16/acceptance22 tetap pending |
| IMP-NATIVE | P0 | 05 | 02, 04, 14, 18A, 22 | not_started | Open/Import Project satu loader, tab editable/ownership sumber/IDs/assets; validation sebelum admission, no merge/flatten |
| IMP-RASTER | P0 | 12 | 04, 18B, 22 | not_started | PNG/JPEG/WebP bytes embedded, decode guards, file dialog/drop |
| IMP-SVG | P0 | 12 | 04, 06A, 20, 22 | not_started | Compatible subset vector, no script/external reference, explicit unsupported warnings |
| IMP-PDF | P2 | 36B | 04, 12, 22 | not_started | Multipage preview/raster first; editable conversion distinct fidelity spike, 36A hanya jika packaged plugin |
| EXP-RASTER | P0 | 15 | 06A, 17, 18C, 22 | not_started | PNG/JPG/WebP options/alpha/flatten/codec fallback, snapshot job |
| EXP-PDF | P0 | 16 | 06A, 17, 18C, 22 | not_started | Single/multipage dasar, varied page sizes/order/DPI, vector/text where supported; raster warning |
| EXP-BATCH | P1 | 33C | 15, 16, 18C | not_started | Presets/naming/cancel/partial report, tidak menunda all-artboard P0 |
| EXP-CODE | P1 | 34 | 26, 28, 27 | not_started | HTML/CSS/assets/CSS tokens, semantic/responsive subset, explicit freeform fallback; 27 jika instances digunakan |
| EXP-SVG | P1 | 41 | 16, 22, 29, 30 | not_started | Capability subset transform/clip/path/text/image, embedded assets, independent viewer; 29/30 hanya untuk fitur terkait |
| ANALYZE-DIAGNOSTIC | P1 | 40B | 18A, 19A, 22 | not_started | analyze_design bounds/overflow/missing assets/fonts/broken token refs, revision/bounded evidence, no auto mutation |
| ANALYZE-ACCESSIBILITY | P2 | 37B | 40B | not_started | Contrast/text size/semantics statis, transparent background fixtures; bukan jaminan aksesibilitas app hasil export |
| UI-ACCESSIBILITY | P0/P1 | 05 | 08, 11, 22, 42B | not_started | P0 focus/tab/label/contrast/state/High DPI; audit keyboard/screen reader P1 42B berbeda dari analisis desain |
| HTTP-OPTIONAL | Opsional / default-off | 21 | 20, 22, 24 | not_included | Tidak dibangun pada roadmap MVP yang dipilih; bila diaktifkan: official SDK Streamable HTTP, loopback/token/Host/Origin dan regression gate |
| P1-CLIPBOARD | P1 | 38A | 04, 08, 12 | not_started | Clipboard image bytes survive reopen, duplicate/paste-in-place one undo, ID remap |
| P1-GUIDES | P1 | 38B | 03, 10B, 15, 16 | not_started | Guides persisted/undoable/non-export, palette/preferences/default restore/shortcut tests |
| P1-RESTORE | P1 | 39A | 04, 14, 19B | not_started | Restore writer-safe, missing asset/font relink no geometry loss/undo |
| P1-HISTORY | P1 | 39B | 03, 04, 14 | not_started | GUI/AI history steps, named snapshots portable retention quota/confirmation |
| P1-DRYRUN | P1 | 40A | 18B, 18C, 19A | not_started | No source/history/assets mutation, diff/base revision, stale apply refused |
| P1-DIAGNOSTICS | P1 | 42A | 01, 20, 25 | not_started | Local bundle preview/redaction paths/user/secrets, design/assets absent default/no upload |
| P1-UI-AUDIT | P1 | 42B | 05, 22, 38B | not_started | Keyboard New→draw/property→Save→Export, scale/screen reader actual evidence; palette conditional |
| D-01 | P0 / deliverable | 01 | 02, 03, 04, 05, 06, 07, 08, 09, 10A, 10B, 11, 12, 13, 14, 15, 16, 17, 18A, 18B, 18C, 19A, 19B, 20 | in_progress | Source code Python modular, bukan dokumen saja |
| D-02 | P0 / release deliverable | 24 | 25 | not_started | Installer Windows x64 + runtime/license inventory |
| D-03 | P0 / deliverable | 05 | 22 | not_started | Native desktop UI |
| D-04 | P0 / deliverable | 22 | 06, 07, 08, 09, 10A, 10B, 11, 12, 13 | not_started | Visual design editor integrated |
| D-05 | P0 / deliverable | 04 | 00B, 02, 05, 14, 22 | not_started | Save/load .ltechdesign + embedded assets |
| D-06 | P0 / deliverable | 16 | 15, 17, 18C, 22 | not_started | Export PDF/PNG/JPG/WebP |
| D-07 | P0 / deliverable | 19A | 18A, 18B, 18C, 19B, 20, 22 | not_started | Local MCP server stdio headless/attached |
| D-08 | P0 / deliverable | 25 | 18A, 18B, 18C, 19A | not_started | Tool/resource contracts dan examples aktual |
| D-09 | P0 / deliverable | 25 | 18A, 19A, 24 | not_started | Contoh konfigurasi Codex untuk executable yang benar-benar dibangun |
| D-10 | P0 / deliverable | 22 | 04, 07, 11, 12, 13, 15, 16, 25 | not_started | Contoh editable poster + web UI, bukan menjalankan prompt desain dalam PRD sekarang |
| D-11 | P0 / deliverable | 22 | 01, 02, 03, 04, 06A, 18A, 18B, 18C, 19B, 24 | not_started | Automated domain/integration/GUI/MCP/build tests sesuai risiko |
| D-12 | P0 / deliverable | 25 | 01, 01A, 24 | not_started | Developer setup guide reproducible dan versi diuji |
| D-13 | P0 / deliverable | 25 | 05, 14, 15, 16, 20, 24 | not_started | User guide, shortcuts, recovery/fonts/codecs/MCP troubleshooting |

## Registry MCP: pemilik semua operasi PRD 7.3/20.4

Ini inventaris kontrak rencana, bukan discovery tool yang sudah tersedia. JSON schema input/output/error/examples dibekukan 18A; adapter hanya mendaftarkan tool yang sudah bekerja. Semua tools dokumen menggunakan session_id; mutasi konten juga expected_revision/request_id. Resource tree memakai query service bounded yang sama.

| ID | Prioritas/gate | Pemilik | Integrasi/verifikasi | Status | Bukti / kriteria selesai |
| --- | --- | --- | --- | --- | --- |
| MCP-get_app_status | P0 | 18A | 19A | not_started | Versi/capabilities/active context |
| MCP-create_project | P0 | 18B | 19A | not_started | New-session dedup exception |
| MCP-open_project | P0 | 18A | 04, 19A | not_started | Shared loader/admission/ownership |
| MCP-list_documents | P0 | 18A | 19A | not_started | Runtime sessions/document IDs/revisions/mode |
| MCP-get_document_info | P0 | 18A | 19A | not_started | Explicit session routing |
| MCP-get_document_tree | P0 | 18A | 19A | not_started | Query/cursor bounded/stale |
| MCP-get_node | P0 | 18A | 19A | not_started | Strict field projection/output limit |
| MCP-get_selection | P0 | 18A | 19A | not_started | Headless selection_unavailable; attached session |
| MCP-set_selection | P0 | 19A | 05 | not_started | State sesi, tanpa content revision/history |
| MCP-create_artboard | P0 | 18B | 07, 19A | not_started | Typed command |
| MCP-create_node | P0 | 18B | 03, 19A | not_started | Typed command |
| MCP-update_node | P0 | 18B | 03, 19A | not_started | Typed command |
| MCP-delete_node | P0 | 18B | 03, 19A | not_started | Subtree/references/history |
| MCP-batch_operations | P0 | 18B | 03, 19B | not_started | Typed content union termasuk page/group/reorder/staged import; bukan save/export/selection |
| MCP-set_text | P0 | 18B | 11, 19A | not_started | Shared text/layout transaction |
| MCP-set_style | P0 | 18B | 10A, 19A | not_started | Shared style renderer |
| MCP-move_node | P0 | 18B | 08, 19A | not_started | Transform/reparent preservation |
| MCP-get_design_tokens | P0 | 18A | 02, 04 | not_started | Minimum typed store |
| MCP-set_design_token | P0 | 18B | 02, 03, 04 | not_started | Undoable typed minimum store |
| MCP-render_preview | P0 | 18C | 17, 19A | not_started | Revision/artifact/transfer/limits |
| MCP-export_design | P0 | 18C | 15, 16, 19A | not_started | Snapshot side effect/job/dedup |
| MCP-save_project | P0 | 18C | 04, 14, 19A | not_started | Snapshot side effect/ownership/conflict |
| MCP-create_page | P0 | 18B | 09, 19A | not_started | Page command/undo |
| MCP-update_page | P0 | 18B | 09, 19A | not_started | Explicit content move semantics |
| MCP-delete_page | P0 | 18B | 09, 19A | not_started | Explicit subtree deletion/undo |
| MCP-import_asset | P0 | 18B | 04, 12, 20 | not_started | Standalone register or batch staging |
| MCP-list_assets | P0 | 18A | 04, 19A | not_started | Bounded manifest metadata |
| MCP-group_nodes | P0 | 18B | 08, 19A | not_started | Dispatcher/geometry/appearance policy |
| MCP-ungroup_nodes | P0 | 18B | 08, 19A | not_started | Dispatcher/geometry/appearance policy |
| MCP-reorder_nodes | P0 | 18B | 09, 19A | not_started | Explicit sibling order |
| MCP-get_job_status | P0 | 18C | 19A | not_started | Lifecycle/progress/source revision |
| MCP-cancel_job | P0 | 18C | 19A | not_started | Idempotent cancellation and commit barrier |
| MCP-create_component | P1 | 27 | 18B | not_started | Component command/tool integration |
| MCP-apply_auto_layout | P1 | 28 | 13, 18B | not_started | Advanced layout; P0 layout domain/GUI 13 |
| MCP-export_html_css | P1 | 34 | 18C | not_started | Code export job |
| MCP-analyze_design | P1/P2 | 40B | 37B | not_started | Diagnostic P1; accessibility extension P2 |
| MCP-preview_operations | P1 | 40A | 18B, 18C, 19A | not_started | Isolated dry-run/base revision |
| MCP-RESOURCES | P0 | 18A | 18C, 19A | not_started | pydesign:// aliases + session templates/revision invalidation, bounded content; subscriptions conditional |

Update 05: shell GUI, tabs/session/history/selection, staged Open/Import/Reload, async Save/Save As/Close dan read-only promotion diimplementasikan. Empat tes GUI serta DPR efektif 1/1.5/2 diuji; AT-27 pindah monitor/handles/export dan integrasi MCP tetap pending. Bukti: [baseline 05](baseline-segment05.md).

05 verified untuk shell/lifecycle dengan 324 core + 9 desktop pada full gate. AT-27 hanya layout DPR efektif 1/1.5/2 + inspeksi screenshot; Windows setting/monitor switching/renderer handles/export belum verified. Acceptance end-to-end tetap menunggu 22.

Update 06: shape/frame/group fill/stroke/radius/transform/z-order/visibility/isolation/clipping, stable scene items dan pan/zoom/fit terimplementasi. Navigation tidak memutasi konten. Canvas text/image/SVG placeholder dengan warning, shadow warning, strict image render menolak fitur belum didukung; metadata tetap tersimpan. [Bukti 06](baseline-segment06.md). AT renderer lintas target tetap pending 06A/22.

Update 06A verified untuk fixture kecil nested rotation/rounded clip/isolated overlap dan primitive text: native canvas/PNG/PDF/QGui offscreen, font metrics/geometry/alpha dan actual PDF image+SMask dibuktikan. Perbaikan device-aligned buffers dan lossless fallback menghilangkan interior mismatch, residual AA dibatasi band1px. Text PDF outline belum searchable. [Bukti 06A](baseline-segment06a.md); acceptance lengkap/transparent image/multi-artboard/production export dan font UI tetap pemilik11/12/15–17/22.

Update 07 verified (24 Oktober 2026): [baseline07](baseline-segment07.md), [ADR0018](adr/0018-drawing-and-selection.md). Canvas selection sinkron Layers, hidden/locked ancestry, real-path hit test dan clip, marquee/Select All adalah state sesi. Save/Open serta shared PNG/PDF proof mempertahankan node editable. Gate344 core/46 desktop, 27 GUI native dan packaging spike lulus; screenshot native diperiksa. Public export jobs tetap15–17, acceptance penuh22. FR-003/005/006 tetap memerlukan integrasi pemilik berikutnya.

Update08: checkpoint independen transform/edit/clipboard/AT24/baseline verified pada [baseline08](baseline-segment08.md), [ADR0019](adr/0019-editor-transform-clipboard.md). Induk08 dan C20.2-RESIZE tetap blocked: evaluator Constraints/Layout13 belum ada; default fixed frame tidak dianggap pengganti evaluator. [Evidence benchmark](evidence/segment08-benchmark.json) mencatat p95/p99/freeze dan target GUI heartbeat yang belum tercapai, bukan klaim NFR-001 lengkap.

Update09 verified: [baseline09](baseline-segment09.md), [ADR0020](adr/0020-pages-and-layer-projection.md). Page CRUD/clone IDs/asset refs, active-page session stability, tree/selection/search/flags dan command-based Qt reorder/reparent teruji termasuk outside-panel dispatcher changes. 360core+63desktop,10GUI native, lint/type/fixtures/docs/package/wheel/executable spike lulus; screenshot native diperiksa. Format native dan blocker08.layout tidak berubah; transport MCP serta acceptance penuh tetap18/19/22.

Update10A verified: [baseline10A](baseline-segment10a.md), [ADR0021](adr/0021-inspector-and-shared-shadow.md). Nested parent-space X/Y/resize/rotation, atomic Mixed edits, finite/color validation, grouped style undo, group opacity dan shadow shared canvas/PNG/PDF/native roundtrip diuji. 34targeted offscreen/18native, full gate376core+81desktop, lint/type/fixtures/docs/package/wheel/executable spike lulus. Screenshot UI/Mixed/picker dan PNG/PDF raster diperiksa. Evidence hashes/version/JUnit di [evidence10A](evidence/segment10a-verification.json). FR008/STYLE-P0 dan AT03/C20.2 terkait belum diklaim lengkap lintas segmen;10B/11/13/15–17/22 tetap pemilik.

Update10B verified dan induk10 verified: [baseline10B](baseline-segment10b.md), [ADR0022](adr/0022-canvas-aids-and-arrangement.md), [evidence10B](evidence/segment10b-verification.json).58targeted/47native,405core+110desktop, lint/type/fixtures/docs/package/wheel/executable spike lulus. Actual native DPR1/1.5/2/four zooms, nested/cross-parent move/resize/align, root multiselect, hidden/locked targets, atomic undo, Inspector sync dan session-only rulers/grid/smart guides diuji. Scene/PNG overlay-free exact, PDF aligned positions dan Save/Open editable dibuktikan. Screenshot native/PNG/PDF raster diperiksa. Manual OS DPI/monitor/clean release/reference performance tetap pending22/23/24; manual persisted guides38B tidak dikerjakan.
