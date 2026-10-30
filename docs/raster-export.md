# Raster export — local GUI and Python service

Open a project, then **File → Export PNG / JPG / WebP…** (`Ctrl+E`). Choose an
artboard, selected objects, or all visible artboards across pages. Hidden artboards
are skipped in all-artboards mode; locks do not suppress rendering. The artboard
list follows live additions/removals and retains your options/selected stable ID.

Scale1/2/3 uses logical pixels, independent of screen DPI/zoom. Custom pixels keep
aspect ratio with centered transparent/solid padding. DPI36–1200 writes PNG/JPG
physical metadata; WebP DPI is reported in job result because no portable physical
resolution metadata is promised. An artboard's authored background is still content:
choosing transparent does not erase its fill. JPG requires a solid RGB color and
is flattened before encoding. WebP supports quality and explicit lossless.

Pick an existing local output folder and naming pattern. Tokens: `{project}`,
`{page}`, `{artboard}`, `{index}`, `{index:03d}`, `{id}`. Extension is automatic.
No folder separators/attribute expressions; unsafe characters in design names are
sanitized, duplicate names rejected. Existing files are protected unless you check
the explicit replace box. A detected external change still blocks replacement.

**Export** pins the current content snapshot and asset bytes. Editing/Save/tab
switching afterward does not change that export. Progress/report identify source
revision, dimensions, paths, warnings, encoder and per-output errors. **Cancel job**
cancels staging; files already committed remain in the result. **Close** hides the
dialog while the job continues. Closing/reloading the source tab cancels/drains
its jobs before the normal unsaved-change decision. Export is not a node command,
does not change revision/history/dirty state, and includes no editor overlays.

Selection bounds include centered stroke and conservative3-sigma shadow padding
after ancestor rounded clips/transforms; isolated ancestor opacity is preserved.
Unselected siblings and ancestor fills/strokes/shadows are omitted. Selection uses
world axes; entire artboard uses its local rectangle/axes. Cross-page or completely
clipped selection is rejected. Tiny curve-intersection arithmetic within1e-6pixel
of integer raster extents is normalized; domain geometry tolerances are unchanged.

Default limits:64MP/output,32768px/side,256outputs/job,16queued jobs plus one active,
128retained job results. Existing shared64MP intermediate buffer budget also applies;
large shadows/isolated groups can hit it before the output pixel limit. Lower scale
or effect size if `limit_exceeded`. Limits can be lowered through ExportService
constructor; safe maxima cannot be increased. PNG/JPG/WebP files are decoded before
publication. WebP capability is checked at runtime and Pillow fallback is tested.
Missing fonts produce warnings; original font metadata is never replaced to export.

## Local service example

The local Python contract is [exports/contracts.py](../src/ltechdesign/exports/contracts.py).
Actual MCP tools/transport remain18C; no HTTP server is required. Run scripts with
a `__main__` guard because rendering uses Windows spawn:

```python
from pathlib import Path
from multiprocessing import freeze_support
from threading import Event
from ltechdesign.assets import BlobStore
from ltechdesign.exports import ExportOptions, ExportTarget, ExportService
from ltechdesign.persistence import PersistenceService

def main():
    output = Path("exports").resolve()
    output.mkdir(exist_ok=True)
    files = PersistenceService()
    handle = files.open("project.ltechdesign", read_only=True)
    store = BlobStore()
    admission = store.admit(handle.loaded.project.assets.assets, handle.loaded.blobs)
    service = ExportService(allowed_roots=(output,))
    try:
        snapshot = handle.admission
        job = service.submit(
            snapshot, store,
            ExportOptions(str(output), ExportTarget("all_artboards"), scale=2),
            expected_revision=snapshot.revision, request_id="raster-001",
        )
        while True:
            status = service.get_job_status(job.id)
            if status.state in ("succeeded", "failed", "cancelled"):
                break
            Event().wait(0.05)
        print(status.state, status.source_revision, status.outputs)
    finally:
        service.shutdown()
        admission.release()
        files.close(handle)

if __name__ == "__main__":
    freeze_support()
    main()
```

Caller supplies already authorized roots and a stable authenticated client identity
when applicable. Future MCP must reuse grants, not expand them from request paths.
Identical client/session/request IDs and payload return the same retained job;
changed payload yields `request_id_conflict`. Dedup lookup precedes stale revision
rejection. Results retained at least30minutes; a full unexpired ledger rejects new
requests. User files never expire with that ledger. After restart/expiry, reconcile
filesystem/state before retry; no crash exactly-once guarantee. Error records and
partial outputs are data, not evidence of rollback.

Verification and remaining manual checks: [baseline15](baseline-segment15.md).
