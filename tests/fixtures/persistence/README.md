# Native persistence fixture

Fixture ZIP berada di [examples/proyek-contoh.ltechdesign](../../../examples/proyek-contoh.ltechdesign).
`scripts/generate_native_fixture.py` menghasilkan container deterministik dari
fixture nested 02 dengan PNG RGBA valid. Fixture JSON historis/final tetap utuh:
PNG lamanya mempunyai CRC IDAT rusak dan harus ditolak decoder produksi.

`scripts/generate_fixtures.py --check` memeriksa drift native fixture juga.
Loader produksi tidak mengimpor generator. Font embedded memakai Abel berlisensi
SIL OFL yang sama dengan fixtures/fonts, tanpa mengambil font dari mesin pengguna.
Tambahan fitur layout/advanced/native GUI fixtures mengikuti segmen pemiliknya.
