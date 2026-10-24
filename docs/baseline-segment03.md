# Baseline segmen 03

Tanggal: 22 Oktober 2026 (Asia/Jakarta). Status: verified pada lingkup engine domain
dan kontrak integrasi fondasi. Baseline Git `54162c5f1c7300d5701dd841b0fb961592540d8b`;
implementasi berada di working tree, tanpa commit otomatis. Perubahan pengguna pada
`prd.md` dipertahankan. Tidak ditemukan AGENTS.md pada workspace/ancestor atau source.

## Hasil dan checkpoint

- 03A verified: typed create/update/delete/move/reparent/reorder/group/ungroup/duplicate,
  style/text/font/token minimum; hierarchy, transform dan binding validation.
- 03B verified: satu owner dispatcher, batch atomik, revision/history/undo/redo,
  dirty checkpoint, post-commit event dan structured errors; hook layout atomik.
- 03C verified: ledger digest/scope/in-flight/retry/error/retention/capacity, history
  memory budget, staging/retention port dan conformance double GC/cancellation.
- 03D verified: tes perilaku, regresi core/desktop, lint/type, format fixtures/docs,
  package/wheel smoke dan handoff. Batas runtime adapter ada di ADR 0013.

Source utama: `src/ltechdesign/commands/contracts.py`, `planning.py`, `dispatcher.py`,
`retention.py`; pengujian `tests/test_commands.py`. Domain immutable 02 tidak di-rewrite.
Kontrak dipertegas di [ADR 0013](adr/0013-command-dispatcher-runtime.md).

## Demo domain

Jalankan `uv run --offline --locked pytest tests/test_commands.py -v` untuk skenario
yang dapat diulang tanpa GUI. Contoh pemakaian di Python environment proyek:

```python
from ltechdesign.commands import Create, Dispatcher, Request
from ltechdesign.domain import DocumentSession, create_node, create_project

dispatcher = Dispatcher(DocumentSession(project=create_project()))
node = create_node("rectangle", dispatcher.snapshot.project.document.pages[0].id)
request = Request(
    session_id=dispatcher.snapshot.session_id,
    expected_revision=0, request_id="create-1", action_name="Create rectangle",
    source="GUI", operations=(Create(node=node),),
)
result = dispatcher.dispatch(request, client_id="local-user")
assert result.ok and dispatcher.snapshot.revision == 1
assert dispatcher.dispatch(request, client_id="local-user") is result
undo = Request(
    session_id=dispatcher.snapshot.session_id,
    expected_revision=1, request_id="undo-1", action_name="Undo create",
    source="GUI", action="undo",
)
assert dispatcher.dispatch(undo, client_id="local-user").ok
assert dispatcher.snapshot.revision == 2
assert not dispatcher.snapshot.project.document.nodes
```

Satu drag kelak mengirim satu `Move`/`Update` atau satu batch pada release, memakai
revision saat gesture mulai. Motion preview tidak di-dispatch dan tidak masuk history.
Source `AI` memakai jalur yang sama. `SetTokens` menyertakan registry/bindings lengkap;
perubahan materialized node values harus satu batch. Final project dapat memakai
`dump_project`/`load_project` 02; hash inventory dihitung ulang oleh serializer.

## Verifikasi aktual

Environment yang benar-benar diuji: Python 3.12.12; PySide6/Qt 6.10.2;
pytest 8.4.2; pytest-qt 4.5.0; ruff 0.14.0; mypy 1.18.2; uv 0.12.1.
Dependency/lockfile/rendering/packaging configuration tidak berubah.

| Perintah | Hasil aktual |
| --- | --- |
| Dot-source `scripts/common.ps1` dari shell awal | Gagal karena execution policy; uv ikut gagal mengakses cache default. Tidak ada tes dijalankan oleh percobaan ini. Dipulihkan dengan env cache lokal workspace dan runner `-ExecutionPolicy Bypass` yang sudah digunakan proyek |
| `uv run --offline --locked pytest tests/test_commands.py -q` | Iterasi awal: 25 passed/1 failed (kode error layout), diperbaiki. Dedicated run berikutnya: 36 passed. Setelah tambahan self-parent regression, 37 tes command lulus pada gate penuh di bawah |
| `uv run --offline --locked ruff check .` dan `uv run --offline --locked mypy` | Final exit 0; strict type check 28 source files. Temuan lint/type awal diperbaiki, tanpa menurunkan checks |
| `$env:UV_OFFLINE = 'true'; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1` | Final exit 0: 230 core + 5 desktop offscreen passed; lint/format/type/fixture/docs lulus; sdist/wheel build, isolated install, CLI/domain JSON dan GUI startup/shutdown smoke lulus |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1 -Subsystem docs` | Exit 0 setelah update handoff/matrix/ADR: 184 matrix rows, 79 segments/checkpoints, 37 tools, 22 Markdown files |
| `.cache/package-smoke/Scripts/python.exe -I -c ...` (Create + retry identik melalui Dispatcher) | Isolated installed-wheel dispatcher/dedup smoke lulus; satu revision, retry mengembalikan result yang sama |
| `git diff --check` | Exit 0; file baru belum tracked sehingga whitespace juga diperiksa oleh ruff/docs audit |

Tes baru mencakup rollback tengah batch/final validation/layout/asset prepare,
redo branch tetap ada setelah gagal dan hilang setelah edit sukses, monotonic
undo/redo, dirty pada late-save/undo, snapshot hierarchy/style/bindings, duplicate
remap, nested rotated reparent/group/ungroup, normalization tanpa drift, cross-page
ownership/cycle/index rejection (termasuk self-parent create sebelum traversal), round-trip style/text/font/token/aset, no Qt import,
stale/conflicting requests, cached success/error, in-flight shared Future,
30-minute retention/capacity, close/reopen, payload/batch limits, owner thread,
listener failure/reentrancy, revision overflow, budget/whole-entry eviction,
live/undo/redo/external asset roots dan cancellation sebelum/sesudah barrier.

## Batas dan integrasi tertunda

Tidak ada blocker bagi segmen 04. Safe untuk melanjutkan setelah instruksi pengguna;
04 tetap not_started dan tidak dikerjakan otomatis.

- 04/04A: byte store, native ZIP, save jobs/checkpoint manifest, canonical ownership,
  baseline external-change dan adapter retention nyata. Default port menolak import
  baru; conformance double bukan bukti I/O/decoder/ZIP atau GC lintas restart.
- 05/08/09: registry GUI, subscriptions, gesture preview/drag release, inspector,
  anchor resize dan UI history-limit notice. Low-level Update mensyaratkan geometri
  serta pivot eksplisit; handler resize terikat anchor merupakan pekerjaan 08.
- 06/06A/11/15–17: renderer/canvas/preview/export mengonsumsi snapshot domain yang sama;
  belum ada hasil painted pixels untuk fitur ini.
- 13: evaluator stack/constraints nyata; hook transaksi diuji dengan fungsi domain,
  layout aktif tetap ditolak eksplisit.
- 18/19/22: authenticated transport/client mapping, queue IPC, reconnect/lost response
  dua proses dan acceptance GUI/MCP. Tidak ada persistent dedup journal atau janji
  exactly-once setelah crash/restart/expiry.
- 23–25: benchmark RSS/latency 1.000 node, clean Windows release dan CI remote pending.
  Traversal budget sekarang konservatif per entry, bukan hasil benchmark RSS.

Tidak ada pemeriksaan visual interaktif yang dilakukan. Tes desktop dan wheel GUI
hanya regresi otomatis offscreen. Skenario manual saat adapter GUI tersedia: drag
beberapa node lalu satu Undo; Undo/Redo delete group memulihkan urutan/style;
AI edit selama drag menolak stale release; save snapshot lama tetap dirty bila ada
edit baru; history-limit notice terlihat dan Undo image tetap menampilkan bytes.
Semua skenario manual tersebut belum dijalankan, bukan klaim lulus.
