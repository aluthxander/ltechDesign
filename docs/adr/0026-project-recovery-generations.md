# ADR 0026 — Local project workflows and basic recovery

Accepted, 30 Oktober 2026 (Asia/Jakarta). Owner:14.

Native1.0 remains unchanged. Runtime session IDs/undo/redo are never persisted in
normal projects. Save checkpoint and preview describe the captured snapshot;
PersistenceService rejects older saves than the handle's last successful runtime
revision. A Save-before-Close/Reload continuation runs only if live content is
clean. Close/Reload freezes content commands until completion. Tabs share the
existing serialized I/O worker, without queued speculative saves.

Autosave defaults120seconds; configurable10–3600 or0(off). Each tick captures all
dirty writable tabs on the GUI thread, including unnamed revision0, with asset
leases. Worker failures are reported per tab and retry next tick. Busy/import/close
defers a tick: interval is cadence, not a realtime deadline. Autosave never writes
the source or changes manual checkpoint/dirty state. Source canonical locks,
baseline detection, read-only promotion and Save As retain ADR0014/0015 policy.

Per-user data: `%LOCALAPPDATA%/ltechDesign Studio`, overridable by
`LTECHDESIGN_DATA_DIR`. Recent catalogue holds12canonical successful Open/Save
paths, not restore data. Preferences use atomic flushed replace; concurrent
preference writers use last successful write. Duplicate reuses the full domain ID
remapper and pinned embedded bytes, into a new unnamed dirty admission.

Recovery record version1 is independent of native/app/PRD versions. Each
`recovery/<runtime-session-uuid>/owner.lock` uses the existing conservative local
QLockFile protocol. Active/ambiguous owners are excluded from startup offers.
An immutable `<20-digit-revision>-<uuid>` generation contains full native
`snapshot.ltechdesign` and bounded `record.json`: UTC timestamp, revision, semantic
digest, informational source path/baseline digest. Source is never an implicit
restore destination. Admission thumbnails are stripped from recovery snapshots.

Archive write → flush/fsync → production-reader validation → record write/fsync →
rename complete staging directory is the publication barrier. Retain two newest
generations; ignore unrenamed staging debris. Post-publication maintenance failure
does not undo a successful snapshot. This proves process-crash recovery on tested
local Windows storage, not power-loss durability, filesystem compare-and-swap or
exactly-once retries after crash. Aggregate quotas/orphan staging cleanup/named
snapshots/full session lists/advanced manager remain39.

Startup claims owners across the decision, labels corruption and offers valid
previous generations with explicit UTC timestamp/revision/source. Restore makes
a new dirty unnamed runtime session/revision0/history-empty while preserving
portable document identity/embedded bytes. It never steals a source writer or
overwrites external changes. Old recovery stays durable/claimed until manual save
or explicit close/discard. Later releases without deleting. Save retires only
generations through its captured revision; close removes published recovery after
jobs finish and user resolves dirty state. Cleanup failure leaves recovery for later.
Recovery carries its asset inventory/byte closure across process GC; existing
live/history/undo/redo/job roots remain in BlobStore.

GUI Save creates optional `thumbnails/project.png` from that exact snapshot in a
bounded spawn subprocess with QGuiApplication on its main thread. It uses shared
font/media resolver/drawing/transforms/clip/opacity. Cover is first nonempty page,
fit within320×240; empty design transparent. Timeout20seconds/renderer failure
omits optional preview and does not prevent saving content. Frozen entry points
call freeze_support. Missing fonts retain authored metadata with explicit fallback
warning, without a pixel-identical claim. No automatic font embedding, invented
legacy migration, new native version or dependency. Existing backup-before-migration
path remains tested; unsupported versions still rejected until a real migration exists.

Evidence: [baseline14](../baseline-segment14.md).
