# Indeks ADR

Tanggal: 21 Oktober 2026. `accepted` berarti arah desain dipilih, bukan implementasi/tes sudah lulus. Detail kontrak ada di [architecture.md](../architecture.md); status implementasi di [progress.md](../progress.md). Semua ADR lingkup lokal single-user.

| ADR | Keputusan | Status | Pemilik pembuktian |
| --- | --- | --- | --- |
| [0001](0001-modules-and-domain.md) | Package, modules, dataclasses, entry points | accepted | 01/02 |
| [0002](0002-identities-and-hierarchy.md) | ID dan hierarchy terurut | accepted | 02/03/05 |
| [0003](0003-geometry-and-compositing.md) | Pivot, reparent, resize, bounds, opacity | accepted | 02/03/06A/08 |
| [0004](0004-file-ownership.md) | Single writer, canonical path, baseline | accepted | 04/04A/19B/20 |
| [0005](0005-shared-rendering.md) | Shared drawing dan offscreen render | accepted | 06/06A/11/12/15–17 |
| [0006](0006-transactions-and-revision.md) | Content/session/job dan revision | accepted | 03/05/13/18/19 |
| [0007](0007-retry-and-retention.md) | Dedup, history dan asset leases | accepted | 03/04/14/18B/18C/19B |
| [0008](0008-threads-and-ipc.md) | Owner thread, attached/headless, IPC | accepted | 17A/18A/19A/19B/20 |
| [0009](0009-persistence-lifecycle.md) | Portable project dan lifecycle staging | accepted; baseline format pada 0010 | 00B/02/04/05/14/22 |
| [0010](0010-native-format-baseline.md) | Spesifikasi native 1.0 baru, field/version/capabilities dan asal-usul | accepted (kontrak dokumentasi) | 00B/02/04/22 |
| [0011](0011-windows-executable-spike.md) | PyInstaller onedir/windowed dan smoke artifact Windows | accepted; bukti lokal 01A | 01A/24 |
| [0012](0012-domain-schema-freeze.md) | Domain immutable, schema 1.0, JSON fixture dan validation freeze | accepted; bukti lokal 02 | 02/04/06A |
| [0013](0013-command-dispatcher-runtime.md) | Dispatcher typed, publication, checkpoints, dedup dan asset retention ports | accepted; bukti lokal 03 | 03/04/05/13/18/19/23 |
| [0014](0014-native-persistence.md) | Native ZIP, atomic I/O, conservative ownership, byte retention dan fixture PNG | accepted; bukti lokal 04 | 04/04A/05/11/12/14/22 |

Versi dependency dan packager yang diuji dicatat pada ADR 0011 serta baseline 01/01A. Bila keputusan berubah, supersede ADR, jelaskan bukti dan migration; jangan mengedit sejarah menjadi klaim fitur telah tersedia.

- [0015 — Desktop session shell](0015-desktop-session-shell.md): accepted, 05; executor I/O dan GUI owner.

- [0016 — Shared painter scene](0016-shared-painter-scene.md): accepted, 06; root invalidation, explicit drawing/isolation dan view overlays.

- [0017 — Render conformance](0017-render-conformance.md): accepted, 06A; explicit fonts/text outlines, device-aligned isolation dan PDF lossless proof.

- [0018 — Drawing dan selection](0018-drawing-and-selection.md): accepted, 07; artboard preset/unit/DPI, ephemeral gestures, parent space, hit paths dan session selection.

- [0019 — Transform dan clipboard editor](0019-editor-transform-clipboard.md): accepted, 08; semantic selection commands, anchor/scale/frame semantics, validated portable clipboard, safe focus routing dan baseline. Evaluator constraints/layout tetap13.

- [0020 — Pages dan layer projection](0020-pages-and-layer-projection.md): accepted,09; page CRUD/clone graph, own layer flags, revision-bound Qt drag, stable page/session selection dan optional workspace reference sanitization.

- [0021 — Inspector dan shared shadow](0021-inspector-and-shared-shadow.md): accepted,10A; parent translation, validated Mixed input, client-scoped history grouping, local palette dan shared alpha shadow/PDF fallback.

- [0022 — Canvas aids dan arrangement](0022-canvas-aids-and-arrangement.md): accepted,10B; physical-pixel snap tolerance, per-view ruler/grid/guides, constrained handles dan atomic world align/equal-gap distribution.

- [0023 — Inline text dan shared layout](0023-inline-text-and-layout.md): accepted,11; typography units, atomic auto-size metrics port, Unicode/IME input, local/embedded fallback dan shared outline diagnostics.

- [0024 — Portable media dan staged import](0024-portable-media-import.md): accepted,12; bounded worker staging/cancel, vector drawing/DPI, source crop mapping dan retained embedded bytes.

- [0025 — Deterministic stack dan parent constraints](0025-deterministic-stack-layout.md): accepted,13; dependency graph, atomic layout/text sizing, fixed/hug/fill/overflow, supported MVP combinations dan parent resize.

- [0026 — Project workflows and basic recovery](0026-project-recovery-generations.md): accepted,14; snapshot checkpoints, separate generations/owner claims, fresh restore sessions, retention and subprocess thumbnails.

- [0027 — Snapshot raster export jobs](0027-raster-export-jobs.md): accepted,15; shared selection/ancestor filter, bounded snapshot jobs, actual codecs/fallback, canonical output commit and truthful cancellation.
