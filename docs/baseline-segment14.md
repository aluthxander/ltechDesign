# Baseline segment14 — projects and crash recovery

30 Oktober 2026 (Asia/Jakarta). Base HEAD
`c7643d88a5b954d16a3613074e83f6e64c5a6b1b`; initial tree clean. No automatic commit.
Native1.0/PRD/dependencies unchanged. Status `verified` for segment14 P0 scope.
Checkpoints: `14.workflow`, `14.recovery`, `14.portability`, `14.handoff`.
All checkpoints `verified`; no mandatory blocker. Release-machine checks remain
pending22/24 without blocking this segment. Next15 `not_started`.
[Contract ADR0026](adr/0026-project-recovery-generations.md).

File→Recent projects/Duplicate Project/Autosave interval complete the existing
page/artboard/Save/Open/Import UI. Autosave is separate from source and manual
checkpoint, includes unnamed tabs, uses pinned snapshots/assets and two atomic
generations. Startup Restore/Discard/Later provides UTC timestamp, corruption
diagnostics and previous generation. Restore creates a new dirty/history-empty
session. Save/Close/Reload protect newer edits. Thumbnail uses shared subprocess
drawing; font metadata stays portable and missing fonts warn.

Main source: persistence/{preferences,recovery,service}.py, ui/{projects,window}.py,
rendering/thumbnail.py and main/freeze entry points. Tests: test_recovery.py,
test_recovery_processes.py, test_projects_workflow.py plus existing regressions.

## Actual evidence

- Initial targeted29 passed (11recovery+9GUI+5process+4shell),14.51s. Extra
  read-only/preferences/malformed-import cases added before final configured gate.
- Real Qt editor subprocesses killed after completed autosave or while next archive
  was staged: named/unnamed cases recover exactly last successfully published
  snapshot, save a normal file in another process, leave source unchanged.
  Newer unsaved memory is not claimed recovered. Session/revision/history reset.
- Fresh-process portability: Save As→close app→move only file→delete original
  project/assets folder→independent fresh profile→Open/edit/resave. Socket audit
  hooks reject network access. Content and embedded bytes retained; UI Import uses
  the same production loader. Missing system font preserves family/PostScript/
  fallback metadata and warning, without claiming identical pixels.
- I/O faults at archive/record/directory publication preserve prior snapshot.
  Corrupt archive/metadata/missing recovery, valid previous generation, active-owner
  exclusion, stale saves/retirement and real BlobStore/history/undo/redo/GC tested.
  Existing migration backup/ownership regressions remain required; no invented edge.
- Native `scripts/demo_projects.py` exit0, actualDPR1.25. Actual dialog, recovered
  tabs, recent menu and saved thumbnail PNGs in `artifacts/projects14` visually
  inspected: timestamp/options readable and native design represented consistently.
  Capture automated; physical mouse/keyboard/screen reader not exercised.
- First all-gate attempt failed when uv tried restricted network; offline retry
  reached lint. Import/format issues fixed. These attempts are not claimed passes.
- Final configured `UV_OFFLINE=true; scripts/check.ps1 all`: exit0,475core+
  183desktop, Ruff117files/mypy113files, docs/fixtures/build/installed-wheel pass.
  Log `artifacts/segment14-check-all.log`. A final small close-job change captures
  session ID on GUI thread instead of reading dispatcher from worker. Then
  persistence/recovery/workflow/shell/process targeted gate113passed,19.54s,
  `artifacts/segment14-targeted.log`/XML, including actual foreign-process owner
  exclusion. Existing tests were not loosened or removed.
- PyInstaller6.22.3 build+offscreen executable spike exit0; frozen thumbnail spawn
  actually succeeds (`artifacts/segment14-executable-thumbnail.json`,348PNGbytes).
  Runtime dependencies tested Python3.12.12/PySide6+Qt6.10.2/Pillow12.3.0 unchanged.
  Final packaging/native verification commands and artifact hashes are recorded
  in [evidence14](evidence/segment14-verification.json).
- Final `scripts/check.ps1 package` offline exit0 after the owner-thread capture
  adjustment; isolated installed wheel also spawns its QGui thumbnail successfully
  (`artifacts/segment14-wheel-thumbnail.json`). Native workflow+shell20passed,
  9.30s (`artifacts/segment14-native.log`/XML). No physical-input claim.

## Run and pending manual checks

Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run.ps1`.
File→Autosave interval:0off,10–3600seconds; default120. Recovery area defaults to
`%LOCALAPPDATA%/ltechDesign Studio/recovery`; use `LTECHDESIGN_DATA_DIR` for an
isolated profile. Duplicate opens dirty tab; Save asks for a normal `.ltechdesign`.
Import opens a complete portable document. Autosave does not mark manual Save clean.

`.venv/Scripts/python.exe scripts/demo_projects.py` reproduces native captures
and Restore→normal Save with an isolated artifact profile. Process evidence:
`.venv/Scripts/python.exe -m pytest tests/test_recovery_processes.py`.

Pending physical scenarios22/24: edit two tabs/unnamed draft, configure interval,
wait for timestamp, OS termination, restore/discard/later with keyboard/mouse;
unwritable/removable storage, foreign editor conflict, screen reader, monitor DPI
and clean Windows release machine. Separate from executed Qt/process automation.

## Limits and handoff

Process kill is not power-loss evidence. Two-generation basic recovery is not full
session restore/named snapshots/advanced recovery manager39. Busy I/O can defer a
tick; serialized worker prevents overlapping publication. Restore is unsaved copy
and never implicitly acquires source ownership. Missing font may alter appearance.
Thumbnail optional/first nonempty page, never restore authority. Future real
migrations must use existing verified backup-before-replace; unsupported versions
remain rejected. Export jobs/MCP15–19/release22/24 retain ownership. Segment15 is
not automatically started.
