# Baseline15 — raster export service and dialog

30 Oktober2026 (Asia/Jakarta), base HEAD `c7643d88a5b954d16a3613074e83f6e64c5a6b1b`
plus uncommitted segment14 implementation, preserved. No automatic commit.
Status `verified`: checkpoints `15.plans`, `15.jobs`, `15.dialog`, `15.encoding`,
`15.handoff` verified for raster15 scope. Contract [ADR0027](adr/0027-raster-export-jobs.md).

Main source: exports/contracts/service/worker/encoding, rendering/exporting and
shared render_image custom-dimensions option; ui/exporting and window lifecycle.
PNG/JPG/WebP only; PDF16/previewCLI17/MCP18C/presets33C not implemented automatically.

GUI and service use shared drawing/font/media with snapshot identity. Source14
changes were preserved. No tests removed or old tolerances weakened. Domain group
invariants remain strict: selection uses runtime traversal filtering, not synthetic
invalid groups or domain mutations. Artboard local axes, selection world axes and
centered custom-size padding are explicit contract choices.

## Actual verification

- `UV_OFFLINE=true; scripts/check.ps1 all`: exit0,496core+196desktop, Ruff130files/
  mypy126files, docs/fixtures/build/isolated installed wheel passed. Log:
  `artifacts/segment15-check-all.log`. An earlier lint attempt failed on line length;
  corrected before successful gate, not claimed passed.
- After the gate, final UI review found stale artboard dropdown entries when content
  changed while the dialog was open. Fixed stable-ID refresh and added one GUI test.
  Final `scripts/check.ps1 desktop`:197passed,46.20s. Final targeted service/dialog/
  shared-render/style/text/conformance:49passed,17.34s. Mypy126files passed again.
  Logs/XML `artifacts/segment15-desktop-final.*` and `segment15-targeted-final.*`.
- New behavior tests cover actual decoded PNG/JPEG/WebP dimensions/alpha/DPI,
  chosen-background JPEG flatten, custom letterbox, Qt capability missing/encoder
  failure/Pillow absence, lossless fallback, embedded font/media all-artboard order,
  actual leases/GC, write failure, collision/external change, clipping/stroke/shadow,
  isolated opacity/z-order, immutable source snapshot, dedup conflict/capacity/expiry,
  queue backpressure,64MP preflight rejection and real render-process exit.
- UI/API bytes identical for PNG/JPG/lossless WebP from the same snapshot while
  canvas had a differing editor preview/selection. Scene-adapter/selection raster
  pixels also match; old06A/style/text conformance still passes. Normal native
  document serialization/history/export source metadata are unaffected.
- Cancel tested queued/precommit/after real os.replace and after first all-artboard
  output. Precommit leaves no published files/temp/locks; late cancel retains outputs
  with truthful state and cancelled remaining rows. Final state follows process/
  temp/lease cleanup; source-tab close asynchronously drains before lifecycle.
- Real16,777,216pixel render cancelled during encoding, GUI timer remained active.
  Offscreen full-gate sample:343.99ms total,31.00ms cancellation,34heartbeats,
  maxgap16.00ms. Native sample:360.00ms total,32.00ms cancel,35heartbeats,maxgap16ms.
  Final native sample may differ; actual artifact `segment15-large-cancel.json`.
  This is job responsiveness evidence, not a full performance23 benchmark.
- Final package and PyInstaller6.22.3 offscreen executable spikes both succeed on
  portable native fixture: four jobs/eight outputs, PNG/JPG/WebP Qt plus WebP
  lossless Pillow. Each was actually decoded before replace. Python3.12.12,
  PySide6/Qt6.10.2 and Pillow12.3.0 unchanged. Frozen backend handles spawn without
  creating editor windows in children. Logs `segment15-package-final.log`,
  `segment15-executable-final.log`; raster reports `segment15-wheel-export-final.json`,
  `segment15-executable-export.json`.
- Final mixed-case regression found/closed: a write failure preceding late cancel
  now keeps overall failed state and still reports committed outputs.22service
  tests passed, then **final full gate** repeated:497core+197desktop,26.96s/50.75s,
  docs/lint130/type126/fixtures/build/installed-wheel raster spike exit0.
  `artifacts/segment15-check-final.log` is the final code gate. Frozen build/spike
  repeated on that source, `segment15-executable-final.log` exit0. Native25passed,
  10.82s (`segment15-native-final.log`/XML). Source-final hashes recorded in evidence15.
- Native `scripts/demo_export.py` exit0, actualDPR1.25, three successful jobs,
  all-artboard PNG plus selected objects JPG/lossless WebP. Actual options/results
  dialogs and decoded PNG visually inspected via view_image. Source design's own
  clip/text bounds preserved; no editor overlays. Captures `artifacts/export15`.
  Native test command/results and code/artifact hashes in
  [evidence15](evidence/segment15-verification.json).

## Run/demo and pending manual scenarios

`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run.ps1`, then File→
Export PNG / JPG / WebP… (`Ctrl+E`). [User/API guide](raster-export.md).
`.venv/Scripts/python.exe scripts/demo_export.py` reproduces native captures and
real output files under a new artifact directory. No PDF/CLI/MCP export is advertised.

Pending physical checks22/24: keyboard-only focus/labels/dialog resizing, screen
reader, OS monitor switching/HighDPI, user folder picker and viewer applications,
unplugged storage and clean Windows release machine. Automated native Qt and image
inspection were performed; physical input/other viewer checks were not.

## Limits and handoff

No blocker15; safe to continue16 separately. PDF16, previewCLI17, MCP18C and advanced
batch presets33C remain their owners, not worked automatically. WebP physical DPI
metadata is not promised: requested DPI appears in result; PNG/JPEG store it.
Only visible root artboards participate in all-artboards mode; explicit artboard
and selection visibility obey shared drawing. Conservative shadow bounds and shared
intermediate memory budget can reject large effects even below64MP output.
Retained result TTL does not delete user files. Foreign programs can still race
between final baseline check and replace; no filesystem CAS/power-loss/after-crash
exactly-once claim. General performance/release/security audits23/24/20 remain pending.
