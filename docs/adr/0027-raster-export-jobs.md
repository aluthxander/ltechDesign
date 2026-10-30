# ADR 0027 — Snapshot raster export jobs

Accepted, 30 Oktober2026 (Asia/Jakarta). Owner15. Native1.0/dependencies unchanged.

ExportService is a local Python job API, outside content dispatcher/history. UI
and future transport use the same service. No HTTP/MCP transport is added here.
`submit(snapshot, store, options, expected_revision, request_id, client_id)` pins
assets and returns queued job identity/session/document/source revision. Retry is
deduplicated by client/session/request ID + canonical option/revision digest,
before checking current snapshot revision. Final records retained at least30minutes;
capacity full rejects without evicting unexpired results. No crash exactly-once claim.
`get_job_status`/`cancel_job` are local methods; actual MCP tools remain18C.

One coordinator thread and one spawned render process run a job at a time, with
at most16queued jobs,128retained results by default. Limits configurable downward
(ledger up to1024). A job allows up to256outputs; output max64MP and32768px/side,
validated before allocation. Existing shared64MP intermediate-isolation budget
remains. Font/media preparation/QGuiApplication occur on child main thread; no
live scene/widget/render cache crosses processes. The source is a validated native
snapshot/embedded closure; long work does not block GUI. Jobs keep their revision
even if editing continues or another tab becomes active.

Artboard export uses its local rectangle/axes, independent of canvas placement,
rotation, screen zoom/DPR. All artboards use document page/root order, visible root
artboards only; locked content renders normally. Selection requires one page,
normalizes ancestor+descendant overlap, follows document z-order and keeps selected
subtrees. A shared-drawing filter preserves original ancestor transform/pivot/isolated
opacity/rounded clip, omitting unselected ancestor fills/strokes/shadows and siblings.
Bounds use shared shape/stroke semantics,3-sigma shadow envelopes and true ancestor
clip paths; conservative shadow padding is allowed, no hit-test/selection handles.
No geometry in the live document is changed. Empty/clipped-away selection errors.

Scale1/2/3 sets pixel dimensions by ceiling; arithmetic noise within1e-6pixel of
an integer is snapped for raster extents, shared by planner/renderer. Positive
subpixel extents still occupy at least one pixel. No domain tolerance is changed.
Custom width+height preserve uniform
scale, centered padding if aspect differs. DPI36–1200 sets PNG/JPEG physical
metadata, never multiplies logical pixels or uses screen DPR. WebP stores pixel
dimensions; DPI is reported in job result, no promise of WebP physical metadata.
JPG requires explicit opaque RGB background and is flattened before encoding.
PNG/WebP can preserve transparency or flatten to solid. Artboard's own authored
background remains design content; transparent output does not remove it.

Runtime QImageWriter capability/canWrite/write are checked. WebP falls back to
Pillow if Qt lacks/fails the encoder; explicit lossless uses Pillow's lossless flag.
Encoder choice is in result. All encoded files are fsynced and really decoded,
checking format/dimensions/JPEG without alpha before publication. Metadata/layout
share existing FontResolver/drawing with canvas; missing fonts warn, without
claiming identical pixels on machines lacking the same fonts.

Destination roots must be granted by local UI user choice or explicit API caller
configuration. Future MCP must reuse grants, not grant arbitrary request paths.
Canonical local path/QLockFile, baseline checks and parent retarget checks protect
each target; no filesystem compare-and-swap against unrelated writers is claimed.
Naming supports project/page/artboard/index/id, bounded sanitized components,
fixed extensions, no path traversal, case-insensitive duplicate output rejection.
Default collision policy fails; checkbox explicitly permits replace existing files.

Write/validate temporary output in destination folder → parent cancellation check →
baseline recheck → guarded per-file os.replace is commit barrier. Child never
publishes. Job terminal state is visible after process/temp/lease cleanup. Cancel
before any publication is cancelled; after publication, outputs remain and state
does not pretend rollback (succeeded with cancelled remaining outputs). Write errors
are failed with per-file results, retaining already published files. All-artboards
is P0; advanced presets/batch scheduling are33C. Closing/reloading source cancels
and asynchronously drains its jobs before lifecycle proceeds.

Official API references checked:
[Qt6.10 QImageWriter](https://doc.qt.io/qtforpython-6.10/PySide6/QtGui/QImageWriter.html),
[Pillow WebP](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp).
Actual tested versions/results: [baseline15](../baseline-segment15.md).
