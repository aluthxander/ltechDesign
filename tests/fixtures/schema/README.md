# Fixture schema 1.0

`nested-v1.json` adalah fixture final normatif dan identik dengan
`docs/examples/ltechdesign-v1-contract.json`. Wrapper dokumentasi memuat `members`
dan base64 blobs; ia bukan container ZIP. Generator menghitung inventory dari
UTF-8 compact JSON final. Semua 10 node, nested transforms, two-page/root order,
group opacity, rounded clip, multiline Unicode, raster, SVG, embedded font dan
property-path token bindings diuji melalui boundary domain.

`legacy-00b.json` adalah salinan byte persis contoh 00B sebelum freeze, dipin
SHA-256 dalam generator. Ia tetap diterima sebagai schema 1.0 tanpa migrasi.
Jangan regenerate fixture historis ini untuk membuat tes kompatibilitas lulus.

`json-schema/` dihasilkan dari anotasi typed model yang sama dengan parser dan
disalin ke `docs/schemas/`. Regenerate/check melalui `scripts/generate_fixtures.py`.
Cross-references, geometry, finite numbers dan integrity tetap memerlukan validator
Python; JSON Schema saja tidak cukup. Lihat `tests/test_domain.py` dan
`tests/test_project_format.py` untuk corruption cases dan semantic round-trip.
