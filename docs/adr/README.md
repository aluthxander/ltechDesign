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
