# ADR 0001 — Package dan domain tanpa Qt

Status: accepted (desain). Tanggal: 21 Oktober 2026.

Konteks: GUI, codec dan MCP harus berbagi Document Model tanpa ketergantungan widget atau transport.

Keputusan: package `ltechdesign`, src layout; GUI `ltechdesign.main:main`, CLI `ltechdesign.cli:main`, module entry CLI. Domain dataclasses frozen/slots dengan nested collections immutable dan validator eksplisit; boundary DTO SDK boleh Pydantic. Commands bergantung domain/ports; UI, MCP, persistence dan drawing adalah adapter. uv + pyproject + lock menjadi alur environment. Pin versi menunggu tes 01; PyInstaller kandidat yang harus dibuktikan 01A.

Alasan: stdlib cukup untuk model, snapshot/equality mudah dikontrol, validator dapat dipakai GUI/file/MCP. Pydantic sebagai seluruh domain akan menambah coupling/coercion yang tidak diperlukan; dataclass sendiri juga tidak menjamin validasi runtime atau deep immutability.

Konsekuensi: 02 harus menguji validator, serialization mapping dan larangan import Qt; tidak membuat dua sumber kebenaran untuk model DTO dan domain. 01 membuktikan entry points dan mencatat versi aktual. Detail: architecture bagian 2–3.
