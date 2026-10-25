# Format proyek ltechDesign Studio — `.ltechdesign` 1.0

Status: schema 1.0 frozen dan teruji pada segmen 02; baseline normatif awal ditetapkan 21 Oktober 2026 atas permintaan pengguna pada segmen 00B. Dokumen ini **baru disusun**, bukan salinan spesifikasi lama. Acuan: PRD 1.2 bagian 6.2, 9, 20.1–20.4 dan [arsitektur](architecture.md). Format ID `ltechdesign.project`; versi container `1.0`; versi schema dokumen `1.0`. Ketiga versi format, aplikasi, dan PRD mempunyai lifecycle terpisah. Keputusan baseline tercatat di [ADR 0010](adr/0010-native-format-baseline.md).

Kata **wajib**, **dilarang** dan **boleh** menyatakan kontrak reader/writer yang akan dibangun. Dokumentasi ini tidak berarti reader/writer ZIP, GUI restore, migrasi historis atau renderer sudah tersedia. Typed validators/JSON Schema dan fixture final tersedia pada 02 (bagian 13); codec ZIP/asset store milik 04; AT-31–AT-34 lengkap milik 22.

Update implementasi 04: reader/writer ZIP produksi dan byte store kini tersedia
di `src/ltechdesign/persistence` dan `assets`, dengan bukti pada
[baseline 04](baseline-segment04.md). Kontrak versi/schema tidak berubah.
[ADR 0014](adr/0014-native-persistence.md) merinci batas I/O/decode/lock yang diuji.
Pada baseline04, GUI restore, font resolver, renderer dan migrasi historis belum diklaim.
Fixture native baru memakai PNG valid; fixture JSON historis tetap utuh dan PNG
CRC-rusaknya ditolak decoder produksi. Format conformance JSON tidak sama dengan
validasi actual media.

Update11: GUI restore05, shared renderer06A dan font/inline text11 kini teruji pada lingkupnya. [Baseline11](baseline-segment11.md) membuktikan editable text/style/font metadata, embedded font bytes dan hasil layout setelah reopen; tidak mengubah schema1.0. Migrasi historis/full acceptance22 serta production export15–17 tetap pemilik masing-masing.

## 1. Tujuan dan batas portabilitas

Satu file wajib memuat model desain editable, token/font metadata dan byte seluruh aset terdaftar yang disimpan. Restore tidak memerlukan absolute asset path, database/settings mesin asal, login, internet, thumbnail atau preview flatten. Open Project dan Import Project memakai validator/loader yang sama dan membuka satu dokumen/tab lengkap dari path sumber, tanpa merge layer ke dokumen aktif. Ekstensi file bukan bukti format valid; periksa manifest dan semua payload.

Yang tidak disimpan: session/server/client/job/request IDs, dedup ledger, history undo/redo, lock, baseline fingerprint, credential, runtime font resolution, cache, selection authority dan status koneksi. Resource `pydesign://` tetap namespace internal MCP, bukan format proyek atau external asset locator. Native file tidak mengandung scripts atau instruksi yang dieksekusi reader.

## 2. Container, encoding dan batas

Container ZIP memakai file biasa, compression store/deflate, tanpa enkripsi atau symlink. ZIP64 boleh hanya jika semua batas tetap dipenuhi. Writer memakai UTF-8 untuk nama entry dan JSON tanpa BOM, JSON object root, key unik di setiap object, tanpa NaN/Infinity; tidak ada komentar/trailing comma. Angka harus finite, integer sesuai field; boolean bukan angka. String konten Unicode dipreservasi, tidak dinormalisasi diam-diam. Urutan key object dan whitespace JSON tidak semantik; urutan array semantik.

Nama entry relatif POSIX dengan `/`, case tepat seperti spesifikasi. Dilarang absolute path, drive/UNC prefix, backslash, `.`/`..`, empty path component, NUL/control character, alternate data stream, trailing dot/space atau Windows reserved device basename. Tolak duplikat baik nama identik maupun alias case-insensitive setelah normalisasi Unicode NFC. Nama entry harus sudah NFC. Directory entry opsional boleh diabaikan hanya bila sesuai direktori inventory dan tetap dihitung dalam limit. Tidak mengekstrak entry ke lokasi asal atau mengikuti link.

| Entry | Wajib | Isi |
| --- | --- | --- |
| `manifest.json` | Ya | Identitas/versi/capabilities/inventory |
| `document.json` | Ya | Pages, registry node, geometry/style/layout/text |
| `assets/index.json` | Ya | Asset IDs, media type, path, ukuran dan SHA-256 |
| `assets/data/<sha256>` | Untuk setiap blob terdaftar | Byte asli, nama lowercase 64-hex tanpa ekstensi |
| `tokens.json` | Ya, boleh kosong | Typed token store dan bindings |
| `fonts.json` | Ya, boleh kosong | Font metadata/fallback dan embedded asset refs |
| `workspace.json` | Tidak | View state portabel opsional |
| `thumbnails/<name>.png` | Tidak | Preview opsional, bukan sumber restore |
| `extensions/<extension_id>/<name>` | Sesuai deklarasi | Payload extension yang diinventarisasi |

Batas default PRD: archive maksimum 10.000 entry dan 512 MiB total uncompressed; aset maksimum 50 MiB/blob; decoded raster maksimum 40 megapixel. JSON member maksimum 4 MiB; nesting maksimum 64 level sebagai budget awal schema. ZIP compressed size, declared sizes, actual streamed bytes dan decompression harus bounded; header bukan satu-satunya bukti ukuran. Batas aman dapat dikonfigurasi, tetapi file yang melewati batas reader ditolak dengan `limit_exceeded`, tidak dipotong. Limit render 64 megapixel/output terpisah dari kelayakan file. Perubahan budget operasional memerlukan bukti dan dokumentasi, bukan perubahan versi file otomatis.

## 3. Manifest dan inventory

Semua field berikut wajib kecuali disebut nullable. Unknown core field memerlukan penanganan bagian 10, bukan diabaikan.

| Field `manifest.json` | Tipe / aturan |
| --- | --- |
| `format_id` | String tepat `ltechdesign.project` |
| `format_version` | String tepat `1.0` untuk reader versi ini |
| `document_schema_version` | String tepat `1.0` |
| `document_id` | ID yang sama dengan document.json |
| `saved_at` | UTC timestamp RFC3339 `YYYY-MM-DDTHH:MM:SS[.fraction]Z`; valid calendar, detik 00..59 (tanpa literal leap-second); metadata writer, bukan urutan commit global |
| `saved_revision` | Integer 0..9007199254740991; checkpoint revision snapshot pada sesi yang menyimpan; bukan counter yang dipakai kembali saat open |
| `writer` | Object `name` dan `version` string nonempty; identitas aplikasi/generator, bukan session/user |
| `required_capabilities` | Array string capability unik, urutan tidak semantik |
| `optional_capabilities` | Array string unik, disjoint dengan required |
| `files` | Array inventory, satu record untuk setiap file selain manifest sendiri |
| `extensions` | Array descriptor extension; kosong pada proyek core |

Inventory record tepat `{path, media_type, byte_length, sha256}`. `byte_length` integer nonnegative ukuran byte setelah decompression; `sha256` lowercase 64-hex dari byte payload yang persis disimpan, bukan dari parse/reformat JSON. JSON members memakai media type `application/json`. Manifest dikecualikan dari inventory untuk menghindari hash rekursif; batas ukuran/schema tetap berlaku. Semua file lain, termasuk thumbnail/extension, wajib ada dan tepat sekali di inventory; undeclared extra file ditolak. Array inventory ditulis urut leksikografis path untuk reproducibility, reader tidak menganggap urutan itu z-order.

Hash membuktikan integritas internal, bukan autentisitas pembuat. Manifest dan seluruh hash dapat diganti penyerang; validasi schema/path/media/decode tetap wajib. Metadata ZIP, saved_at dan urutan entry tidak dipakai sebagai identitas konten.

## 4. Identitas dan `document.json`

ID adalah string ASCII `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`; bukan path. Writer baru menghasilkan UUID4 lowercase; ID lama yang sah, seperti `node-001`, dipreservasi. ID unik dalam masing-masing registry dan page list; page ID dan node ID juga tidak boleh bertabrakan. Referensi memakai field bertipe, bukan menebak namespace berdasarkan prefix. Document ID tidak wajib berbeda dari asset/token/font ID karena registry-nya terpisah; code menggunakan tipe ID terpisah.

Root document tepat `{schema_version, document_id, name, pages, nodes}`. `schema_version` = `1.0`; name string; pages array minimal satu page; nodes object key NodeId → Node. Tidak ada `session_id` atau `revision` di document. Open memberi session ID baru dan runtime revision awal 0; manifest.saved_revision hanya metadata snapshot. Save As mempertahankan document/content IDs; Duplicate Project membuat document/page/node/token/font/asset ID baru dan meremap semua referensi yang didukung, sementara byte/hash aset boleh sama.

Page tepat `{id, name, root_ids}`. Root IDs terurut dan setiap node menjadi anggota tepat satu page. Registry node mempunyai `id` sama dengan key, `page_id`, `parent_id` nullable dan `children` array. Root harus `parent_id=null` dan terdaftar tepat sekali di root_ids page-nya. Nonroot harus terdaftar tepat sekali pada children parent yang ada di page sama. Tolak cycle, orphan, duplicate children/root, missing refs, parent/child contradiction atau node pada dua page. Urutan root/children dari bawah ke atas adalah z-order; urutan registry object tidak berpengaruh.

### 4.1 Field umum node

Setiap Node wajib memiliki semua field ini: `id`, `type`, `name`, `page_id`, `parent_id`, `children`, `x`, `y`, `width`, `height`, `rotation`, `pivot`, `scale`, `visible`, `locked`, `opacity`, `clip_content`, `style`, `layout`, `constraints`, `data`.

- `type`: artboard, frame, group, rectangle, ellipse, line, polygon, text, image atau svg. Artboard hanya root; artboard/frame/group container, tipe lain children kosong.
- `x/y`: finite logical pixel relatif parent; geometry lokal origin (0,0), bukan scene minimum. `pivot={x,y}` finite dalam koordinat lokal, boleh di luar geometry jika eksplisit. `rotation` finite derajat searah jarum jam; `scale` finite >0 uniform. `opacity` 0..1, visible/locked/clip_content boolean. Writer tidak membulatkan transform ke integer.
- Width/height finite >0 untuk leaf selain line dan untuk artboard/frame; group boleh extent nol bila geometry isinya demikian atau kosong. Line boleh satu extent nol, endpoints berbeda. Polygon minimal tiga titik dengan extent positif. Dimensi positif memakai perbandingan strict >0 tanpa epsilon. Verifikasi derived group geometry memakai abs 1e-9 logical px dan rel 1e-12; endpoint/vertex extent wajib sama persis dengan dimensi tersimpan.
- Local matrix `T(x,y) T(pivot) R(rotation) S(scale) T(-pivot)`; world matrix hasil komposisi ancestor. Tidak ada shear, flip, negative atau nonuniform scale. Resize/reparent/normalisasi group harus mempertahankan anchor/matriks sesuai PRD 20.2; serialized geometry tidak diganti dengan visual bounds.
- Geometry group adalah union subtree geometry tanpa stroke/shadow, termasuk hidden nodes, dinormalisasi bersama kompensasi transform anak; empty group width/height/pivot nol. Width/height group adalah derived geometry yang disimpan untuk verifikasi, bukan freeform scale controls. Group resize mengubah uniform scale; frame resize mengubah geometry dan menjalankan layout dalam satu transaksi.
- Default saat create (writer tetap menuliskan field): rotation=0, scale=1, visible=true, locked=false, opacity=1, pivot pusat geometry, artboard clip=true, frame/group clip=false; leaf clip_content=false. Leaf clipping gambar/rounded fill memakai primitive style yang ditentukan di bawah.

### 4.2 Style

`style` tepat `{fill, stroke, radius, shadows}`. `fill` null atau `{type:"solid", color:"#RRGGBBAA"}`; warna delapan digit hex uppercase sRGB straight-alpha, termasuk alpha eksplisit. `stroke` null atau `{color, width}` dengan width finite >0 logical pixel, center-aligned; cap/join/dash advanced perlu capability baru. `radius` array empat angka nonnegative urutan top-left/top-right/bottom-right/bottom-left; hanya rectangle/frame/artboard/image/svg memakai radius, tipe lain wajib nol. Renderer membatasi radius agar berpasangan muat geometry dengan faktor skala seragam, path fill/clip sama.

`shadows` array maksimal delapan record `{offset_x, offset_y, blur, spread, color}`; offset finite, blur/spread finite nonnegative logical pixel, color seperti fill. Blur adalah Gaussian sigma; support efek dibatasi 3 sigma, dan spread menambah support sebelum offset. Kontrak ini wajib dipakai shared renderer. Basic drop shadow tersedia dalam kontrak P0; efek lanjut harus dideklarasikan capability, tidak dibuang. Group fill/stroke wajib null dan radius nol; shadow boleh diterapkan pada hasil komposit. Group opacity diterapkan sekali pada children composite terisolasi. Raster fallback juga berlaku preview/export; PDF melaporkan rasterisasi. Geometry, visual (stroke/shadow/clip) dan screen-tolerant hit bounds tidak dicampur atau disimpan sebagai geometry yang baru.

### 4.3 Payload per tipe

| Tipe | `data` dan aturan |
| --- | --- |
| rectangle, ellipse, group | Object kosong `{}` |
| artboard, frame | `{unit, dpi, background}`; unit px/mm/cm/in, dpi finite >0, background color atau null; width/height selalu logical pixels, bukan angka unit fisik |
| line | `{start:{x,y}, end:{x,y}}`; minimum koordinat endpoints per sumbu =0, max = width/height; boleh horizontal/vertical, bukan dua endpoints sama |
| polygon | `{points:[{x,y},...]}` minimal tiga; finite local vertices, bounds min=0/max=width,height; closed polygon |
| text | `{text, typography}`; text Unicode termasuk newline; typography dijelaskan di bawah |
| image, svg | `{asset_id, fit, crop}`; asset sesuai media type, fit = fit/fill/stretch; crop = `{x,y,width,height}` normalized source rectangle, x/y≥0, width/height>0, x+width dan y+height≤1 |

Image/svg crop memilih source rect lebih dahulu, kemudian fit/fill/stretch memetakan source rect ke container geometry. Fill dan rounded image clipping mengikuti container, bukan menulis ulang byte aset; original byte tetap utuh. SVG adalah objek vektor berbasis asset sumber untuk subset yang dinyatakan didukung, bukan janji semua XML menjadi node editable individual. Script/external fetch/unsafe SVG ditolak; unsupported semantics tidak boleh diraster diam-diam pada native save.

Typography tepat `{font_id, font_size, font_weight, italic, alignment, vertical_alignment, line_height, letter_spacing, sizing}`. FontId wajib ada dalam fonts registry; font_size finite >0 logical pixel; font_weight integer 1..1000; italic boolean; alignment left/center/right/justify; vertical_alignment top/center/bottom; line_height `{unit:"multiplier"|"px", value:positive finite}`; letter_spacing finite logical pixel; sizing fixed/auto_width/auto_height. Warna teks memakai style.fill. Explicit newline disimpan `\n`; reader tidak mengubah string atau metadata font karena fallback. Rich spans/variable axes/text-on-path bukan core 1.0, perlu capability/schema extension di 31.

Semantik11: line_height menentukan jarak baseline (`value × font_size` untuk multiplier, literal logical px untuk px); letter_spacing adalah tambahan advance logical px melalui AbsoluteSpacing. Fixed dan auto_height membungkus pada width; auto_width hanya explicit newline. Auto dimensions dimaterialisasi pada node width/height (ceil1/64px), sehingga editable restore tidak memerlukan preview. Runtime resolver/IME composition tidak serialized. Font yang tidak tersedia memberi warning tanpa mengganti metadata; outline emoji monokrom hanya bila tersedia. Rincian [ADR0023](adr/0023-inline-text-and-layout.md), tanpa perubahan schema/native1.0.

### 4.4 Layout dan constraints

`layout` null atau `{type:"stack", direction, padding, gap, align_main, align_cross, sizing_x, sizing_y}` pada frame/artboard. Direction horizontal/vertical; padding empat finite nonnegative angka top/right/bottom/left; gap nonnegative; align_main start/center/end; align_cross start/center/end/stretch; sizing_x/y fixed/hug/fill. Group tidak memiliki stack layout. Leaf boleh `layout=null`; ukuran item fixed/hug/fill terhadap stack dinyatakan melalui constraints.sizing_x/y.

`constraints` null atau `{horizontal, vertical, sizing_x, sizing_y}`; horizontal/vertical start/end/center/stretch; sizing_x/y fixed/hug/fill. Null berarti fixed size dan anchor start. Kombinasi yang membentuk cyclic hug/fill atau tidak didukung solver tidak boleh menghasilkan nilai perkiraan: reader harus mempertahankan data dan menolak edit/read-only dengan error capability/layout yang jelas sampai solver tersedia. Stored node geometry adalah hasil terakhir layout, wajib konsisten dengan evaluator deterministik yang didukung. Freeze solver/rules overflow berada di 13; format ini tidak mengklaim solver sudah diimplementasikan. Advanced min/max/aliases/component refs bukan core 1.0.

## 5. Asset store

`assets/index.json` tepat `{schema_version:"1.0", assets:[...]}`. Tiap record tepat `{id, path, media_type, byte_length, sha256}`. Path wajib `assets/data/` + sha256; byte_length/hash identik dengan inventory manifest dan actual bytes. Beberapa asset ID boleh memakai blob path/hash sama; satu asset ID tidak boleh mendefinisikan dua blob. Seluruh asset dalam registry, termasuk registered asset yang belum dipakai node, harus memiliki byte embedded. Writer tidak menghapus registry diam-diam sebagai efek save.

Core media types: image/png, image/jpeg, image/webp, image/svg+xml, font/ttf, font/otf. Decoder memverifikasi actual content dan limits, bukan hanya ekstensi/media label. Linked/import path hanya input import lokal; path asal tidak dipakai untuk restore dan tidak diserialisasi sebagai asset authority. Font/system resolution tidak membuat absolute path portabel. Unsupported media/capability ditangani bagian 10, bukan byte dihilangkan.

GC runtime mempertahankan live document/history/redo/snapshot/recovery/job references. Container hanya memuat asset registry snapshot yang disimpan; history/lease runtime tidak masuk file. Recovery dan named snapshot memakai inventory mereka sendiri dan tidak boleh kehilangan blob karena native save/cleanup. Implementasi retention berada di 03/04/14/39B.

## 6. Tokens dan bindings minimum P0

`tokens.json` tepat `{schema_version:"1.0", tokens:[...], bindings:[...]}`. Token record `{id,name,type,value}`; type color/number/string; color `#RRGGBBAA`, number finite, string Unicode. ID unik, nama tidak menjadi ID. Alias/themes/structured typography/shadow tokens P1 perlu extension/capability berversi, bukan opaque value yang diterka.

Binding record tepat `{node_id, property, token_id}`. Pasangan node/property unik. Core property paths yang boleh dibind:

| Property | Tipe token / validasi nilai |
| --- | --- |
| `style.fill.color`, `style.stroke.color` | color; fill/stroke target harus ada |
| `x`, `y`, `width`, `height`, `rotation`, `scale`, `opacity` | number dengan range/invariant field target |
| `data.typography.font_size`, `data.typography.letter_spacing` | number; target harus node text dan range sesuai |
| `data.text` | string; target harus text |

Tidak ada JSONPath/expression/script di property path. Unknown path atau token referensi hilang ditolak, bukan silent fallback. Nilai literal target tetap disimpan sebagai materialized value dan wajib setara nilai binding yang di-resolve pada snapshot; perubahan token memperbaruinya melalui satu transaksi beserta layout. Pembaca tanpa binding evaluator tidak boleh membuang binding untuk membuat file seolah editable. P0 wajib mempertahankan/baca-tulis token minimum dan bindings yang digunakan; UI binding/aliases/themes P1 di 26.

## 7. Fonts

`fonts.json` tepat `{schema_version:"1.0", fonts:[...]}`. Record tepat `{id, family, style, weight, italic, postscript_name, source, asset_id, fallback_families, license}`. Family/style string, weight 1..1000 integer, italic boolean, postscript_name string atau null; source system/embedded. Embedded wajib asset_id ke font/ttf atau font/otf; system wajib asset_id=null. Fallback_families array nama family, ordered. License null atau `{identifier, url, embedding_allowed}`; url metadata saja, tidak di-fetch. Embedding hanya jika embedding_allowed=true dan hak distribusi memang telah diperiksa, bukan berdasarkan boolean file tidak tepercaya saja.

Font system hilang tidak menggagalkan struktur restore: laporkan warning per font/node, gunakan resolver fallback tanpa mengubah metadata asli. Ini pengecualian dependency font lokal, bukan izin missing embedded asset; font embedded yang byte-nya hilang/hash salah membuat validation gagal. Pilihan fallback runtime, absolute font path dan hasil substitusi aktual tidak ditulis ulang ke metadata desain kecuali command pengguna eksplisit. Portable pixel-identical rendering memerlukan font yang sama/embedded legal; editable restore tetap mungkin dengan warning font missing. Shared renderer dan resolver dipakai canvas/preview/export.

## 8. Workspace dan thumbnail

`workspace.json` tepat `{schema_version:"1.0", active_page_id, views:[{page_id, pan:{x,y}, zoom}]}`. Page refs harus ada, satu view per page, pan finite logical pixel, zoom finite >0. Member ini opsional: malformed view schema/references boleh diabaikan dengan warning dan default viewport setelah integrity checks file berhasil. Workspace tidak mengubah content revision/undo. Tidak memuat selected node IDs, open tabs, session/connection/client IDs, user path atau credentials.

Thumbnail PNG opsional wajib hash/inventory benar, dimensions/decode bounded, dan tidak dipakai untuk restore konten jika document/assets invalid. Thumbnail outdated boleh dirender ulang; saved_revision manifest menunjukkan snapshot konten, thumbnail writer wajib dibuat dari snapshot yang sama. Tidak adanya thumbnail bukan error file.

## 9. Capabilities dan extensions

Capability string berversi persis, tanpa negosiasi semantik berdasarkan prefix. Project core selalu required `document.core/1`, `geometry.similarity/1`, `assets.embedded/1`, `tokens.core/1`, `fonts.metadata/1`, bahkan jika store kosong. Tambahkan required berikut bila payload menggunakannya: `render.isolated-opacity/1` (group opacity bukan 1), `render.clipping/1` (clip_content true atau radius clip), `layout.stack/1` (layout nonnull), `tokens.bindings/1` (bindings nonempty), `assets.svg/1` (SVG node/asset), `fonts.embedded/1` (embedded font). Capability table ini menetapkan kontrak data; dukungan reader nyata baru boleh diiklankan setelah tes implementasi.

`workspace.view/1` dan `preview.thumbnail/1` hanya optional. Required capability yang tidak didukung: tolak editable admission dengan `unsupported_capability`; boleh diagnostic/read-only inspection yang tidak menulis ulang file dan tidak mengklaim restore penuh. Reader tidak boleh menganggap fitur P1 otomatis didukung karena container version sama.

Extension descriptor tepat `{id, version, capability, paths, edit_policy, asset_ids}`. ID `[a-z][a-z0-9._-]{0,63}`, version string nonempty, paths unik di extensions/id/ dan inventory. Edit_policy = requires_support atau preserve_opaque. Requires_support wajib capability pada required list. Preserve_opaque hanya untuk metadata yang tidak mengubah geometry/render/relationships/tokens/layout core; capability pada optional list; payload bytes wajib dipreservasi persis. Asset_ids mendeklarasikan semua asset refs untuk retention dan wajib ada. Extension optional yang memengaruhi konten memerlukan support atau read-only, bukan dianggap metadata secara otomatis.

Reader tanpa adapter extension tidak mengeksekusi payload. Semua asset refs extension dipertahankan; untuk Duplicate Project/remap IDs, unknown extension harus ditolak (`unsupported_capability`) sampai ada adapter remap yang teruji; Save As tetap dapat preserve IDs/opaque bytes. Tidak menghapus opaque extension agar clone/edit berhasil. Future components/path/rich text/effects memakai extension/capability yang didefinisikan pada segmennya atau versi schema baru dengan migrasi, tidak menyelipkan field core tak dikenal.

## 10. Versions, unknown fields dan migration

Reader baseline hanya mengklaim format/schema tepat 1.0. Unknown format major/minor atau document/member schema ditolak `unsupported_version` sampai ada reader/migration yang teruji; tidak menganggap minor pasti kompatibel. Setiap core JSON object menolak duplicate keys dan field tambahan yang tidak didefinisikan. Inspector read-only boleh menampilkan raw data dengan warning; editable loader tidak membuangnya. Unknown optional extension yang memenuhi kontrak metadata pada bagian 9 boleh dipreservasi opaque.

Migration registry version-to-version tersedia di `domain/migrations.py` (02); orchestration IO/backup berada di 04. Registry baseline hanya validator 1.0, tanpa edge migrasi historis. Migrasi bekerja pada staging, mempertahankan ID/assets/extension bytes sejauh didukung, menghasilkan laporan perubahan dan memvalidasi hasil penuh. Original tidak ditulis ulang saat Open. Sebelum save hasil migrasi ke sumber, simpan backup versi lama, periksa ownership/baseline dan minta intent pengguna yang sesuai lifecycle. Failed migration tidak mengganti tab/model/file lama. Belum ada migration path atau backward compatibility ke format native lain yang diklaim oleh segmen 00.

## 11. Urutan load/save dan errors

Load: authorize/canonicalize source → acquire writer lock atau read-only → bounded ZIP inventory → parse manifest/version/capabilities → validate declared entries/hashes/size → parse strict core JSON → graph/token/font/asset cross-validation → supported layout/geometry validation → publish admission baru. Baseline berasal dari byte yang benar-benar dimuat dan file identity yang stabil saat baca; external change saat load membatalkan admission. Gagal tidak mengganti tab aktif, tidak mendaftarkan asset/session parsial dan melepaskan resource staging.

Save: pin snapshot revision dan closure bytes registry → serialize seluruh core/opaque payload ke temp pada filesystem tujuan → validate container temp → recheck canonical identity/baseline → atomic replace → baseline/checkpoint baru. Source lock ditahan sampai Save As target berhasil; target lock dan baseline/absent marker wajib; Save As ID tetap, Duplicate Project remap. Tidak menyimpan session ID untuk membawa ownership ke mesin lain. Read-only tidak menulis sumber; Save As ke target baru tersedia. Lock sidecar dan fingerprint di luar ZIP, mengikuti architecture/PRD 20.1. Lock aplikasi tidak menjamin program asing mematuhi protokol.

| Kegagalan | Kode service rencana / detail |
| --- | --- |
| ZIP rusak, missing member, duplicate/path invalid, invalid JSON/graph/binding | `invalid_project`; reason terstruktur seperti invalid_archive, missing_entry, duplicate_entry, unsafe_path, invalid_json, invalid_hierarchy, invalid_binding |
| Hash/byte length berbeda atau missing embedded blob | `asset_integrity_error` atau `invalid_project` dengan member path dan reason integrity_mismatch, tanpa isi secret/path mesin |
| Versi/capability tidak dikenal | `unsupported_version`, `unsupported_capability`; actual/required/supported fields |
| Ukuran/count/decode melampaui batas | `limit_exceeded`; limit name/actual/maximum |
| Tidak punya izin/ownership atau file berubah | `path_not_allowed`, `file_owned`, `read_only`, `external_change_conflict` |
| Write/cancel sebelum barrier | `io_error` atau job cancelled; temp/staging dibersihkan, file lama tetap |

Exception domain dibekukan 02 sebagai `ModelError(code, reason, path, details)`; DTO service/IO dilengkapi 04 dan dipetakan GUI/MCP, bukan saluran loader berbeda. Cancel setelah replace tidak boleh melaporkan side effect hilang. Heavy read/write job tidak memblokir GUI thread; mutasi konten tetap di owner dispatcher. Tidak ada journal exactly-once lintas crash dalam container ini.

## 12. Semantic equality dan pembuktian

Semantic equality Load→Save→Load membandingkan document_id, page/node IDs/order, geometry/transforms/pivot/scale/clip, text/style/layout/constraints, token IDs/values/bindings, font metadata, asset records serta actual byte hashes, dan extension bytes/descriptors. Tidak membandingkan JSON key order/whitespace, ZIP timestamps/compression/member order, saved_at/writer/saved_revision, view state atau thumbnail encoding. Normalisasi numeric yang mengubah makna atau asset re-encoding lossy saat save dilarang. Preview comparison memakai toleransi shared renderer yang dibuktikan 06A, bukan syarat raw PNG byte-identical.

Fixture final terbaca mesin: [ltechdesign-v1-contract.json](examples/ltechdesign-v1-contract.json), identik dengan [nested-v1.json](../tests/fixtures/schema/nested-v1.json). Root `example_kind`, `members` dan `asset_blobs` hanya wrapper fixture, tidak dimasukkan ke ZIP. Inventory fixture baru dihitung dari UTF-8 tanpa BOM memakai Python `json.dumps(ensure_ascii=False, allow_nan=False, separators=(",", ":"))` atas urutan key yang tersimpan; blob source memakai base64. Ini encoding generator fixture, bukan canonical JSON wajib untuk writer lain. Codec menghitung inventory dari byte final, tidak menyalin hash contoh setelah serialization berubah.

[Fixture historis 00B](../tests/fixtures/schema/legacy-00b.json) dipreservasi byte persis dan dipin SHA-256 dalam generator. Contoh lama berlabel 1.0 tetap diterima tanpa migrasi, termasuk ID lama, `data.text/data.typography`, FontId dan property-path bindings. Tidak ada klaim kompatibilitas dengan contoh PRD ilustratif atau versi native lain. Contoh ilustratif PRD bagian 9 diganti rujukan fixture final ini.

`scripts/generate_fixtures.py` menghasilkan fixture, contoh docs dan keenam JSON Schema bersama; `--check` mendeteksi drift. `scripts/check-file-format-spec.ps1` sekarang menjalankan `scripts/check_file_format.py`, memakai validator domain yang sama untuk contoh final dan historis, integrity/member references, semantic round-trip dan unsupported required capability. Tes negatif lengkap ada di `tests/test_domain.py` dan `tests/test_project_format.py`. Audit ini belum membaca ZIP, decode aset atau memverifikasi GUI/rendering. FR-002/AT-31 sampai AT-34 belum diklaim selesai.

| Bukti dan ownership | Pemilik |
| --- | --- |
| Strict validators/JSON Schema, domain tanpa Qt, duplicate keys/unknown fields, numeric/geometry/binding fixtures: teruji | 02, lihat baseline-segment02.md |
| Actual ZIP round-trip, inventory/hash, adversarial archive, portability setelah sumber asset dihapus, source file tetap saat failure | 04 |
| Two-process locks, Save As success/failure, external change, runtime session baru | 04A, 05, 19B |
| Shared render fixture/text/font/alpha/clip, PDF/multipage/raster artifacts | 06A, 11, 12, 15–17 |
| GUI/MCP Save/Open/Import/edit/save ulang dan repeated semantic round-trip AT-31–AT-34 | 22 |

## 13. Freeze implementasi segmen 02

Model immutable (`frozen=True`, `slots=True`, tuple dan defensive-copy mapping) ada di [domain/models.py](../src/ltechdesign/domain/models.py). JSON Schema Draft 2020-12 dan typed decoder memakai anotasi yang sama. Schema structural tidak menggantikan validasi graph, finite arithmetic, cross-reference, required capabilities, materialized token values, path aliases atau integrity. Unknown property di setiap core object ditolak; registry `nodes` hanya menerima key NodeId sah. Field runtime tidak masuk schema member.

| Member | Schema | Typed record |
| --- | --- | --- |
| manifest.json | [manifest.schema.json](schemas/manifest.schema.json) | Manifest |
| document.json | [document.schema.json](schemas/document.schema.json) | Document, Page, Node dan union data |
| tokens.json | [tokens.schema.json](schemas/tokens.schema.json) | Tokens, ColorToken/NumberToken/StringToken, Binding |
| fonts.json | [fonts.schema.json](schemas/fonts.schema.json) | Fonts, Font, FontLicense |
| assets/index.json | [assets-index.schema.json](schemas/assets-index.schema.json) | AssetsIndex, Asset |
| workspace.json | [workspace.schema.json](schemas/workspace.schema.json) | Workspace, View |

`from_data`/`loads` memvalidasi member; `load_project` menerima mapping entry ke bytes lengkap dalam memori dan memvalidasi inventory/hash serta referensi. `dump_project` membentuk bytes JSON/member dan inventory baru; belum ZIP/disk writer. Domain tidak mengimpor Qt, filesystem, font resolver, SVG interpreter atau transport. Gate decode/sanitasi aset, ZIP limits/ownership dan atomic IO tetap wajib pada 04/12 sebelum file benar-benar dibuka di aplikasi.

### 13.1 Create defaults dan nilai bertipe

Semua field harus hadir pada file, meski constructor mempunyai default. `create_project` membuat document dengan satu page kosong, registry token/font/asset kosong, revision checkpoint 0 dan schema 1.0. `create_node` membuat UUID4 baru; text wajib `TextData` dengan FontId, image/svg wajib `MediaData` dengan AssetId. Tidak membuat referensi font/aset fiktif. Node langsung memakai type discriminator dan payload bertipe yang harus cocok.

| Field saat create | Default |
| --- | --- |
| Node name, parent, children | empty string, null, empty tuple |
| x/y, rotation, scale, opacity | 0/0, 0 derajat, 1, 1 |
| width/height | 100/100 logical px; empty group 0/0 |
| pivot | pusat geometry, empty group (0,0); eksplisit pada serialized node |
| visible/locked/clip_content | true/false; clip true artboard, false lainnya |
| style | fill/stroke null, radius [0,0,0,0], shadows [] |
| layout/constraints | null/null |
| FrameData | unit px, dpi 96, background null |
| TextData/Typography | text empty, font_size 16 px, weight 400, italic false, left/top, line_height multiplier 1.2, letter_spacing 0 px, sizing fixed; font_id wajib |
| MediaData | fit fit, crop (0,0,1,1); asset_id wajib |
| Stroke / Shadow | black opaque width 1 px / offset 0, blur 0, spread 0, color #00000080 |
| View | pan (0,0), zoom 1; page_id wajib |

Geometry memakai logical px, rotation derajat clockwise, scale dimensionless positif; crop normalized source coordinates; opacity 0..1. Font size/letter spacing dan line_height unit px memakai logical px, line_height multiplier dimensionless. Integer field menolak float dan boolean; angka tidak dikoersi dari string. String Unicode valid dipreservasi tanpa normalisasi. Hierarchy maksimum 64 ancestor levels terpisah dari JSON nesting budget 64. JSON member maksimum 4 MiB, termasuk output codec.

### 13.2 Transform dan bounds

`local_matrix`, `world_matrix`, `relative_node` dan `normalize_group` menggunakan vektor kolom serta order bagian 4.1. Reparent plan memecahkan translasi dari pivot lokal dan inverse parent, menjaga world matrix. Group normalization mengompensasi direct children; hidden descendants dan overflow frame ikut union geometry, stroke/shadow/clip tidak ikut. Similarity decomposition memakai residual relatif/absolute 1e-12 pada koefisien ternormalisasi; reflection, shear, singular dan nonuniform scale ditolak. Rotation tersimpan tidak dibulatkan atau dinormalisasi saat round-trip. `scale_group` hanya mengubah scale uniform dan menolak group berukuran 0 pada kedua sumbu; group berbasis line dengan satu extent nol tetap sah.

`primitive_bounds` dan `subtree_geometry_bounds` mengembalikan geometry. `visual_bounds` mengembalikan conservative world AABB dengan stroke center, support shadow, visibility/opacity dan intersection AABB clipping ancestor. AABB boleh melebihi painted pixels untuk rounded clip, glyph ink atau transparent image; renderer 06A wajib memberi path/pixel semantics yang sama, tidak menggunakan AABB sebagai pengganti path clip. Hit bounds menambah tolerance physical screen px / zoom / DPR ke visual bounds. Tidak satu pun bounds hasil evaluator diserialisasi menggantikan geometry node. Group isolated-opacity tetap metadata komposit satu kali; implementasi raster/render milik 06A.

### 13.3 Admission, error dan migrasi

Supported required capabilities: lima core capability, render.isolated-opacity/1, render.clipping/1, tokens.bindings/1, assets.svg/1, fonts.embedded/1 dan (segmen13) layout.stack/1. Layout/constraints disimpan bersama geometry editable hasil evaluasi. Reader memvalidasi supported combinations dan dependency cycles saat admission; tidak mengubah geometry file diam-diam. Evaluasi command memakai kontrak [ADR0025](adr/0025-deterministic-stack-layout.md), tanpa mengubah schema/format1.0. Extension required selalu ditolak sampai adapter teruji, termasuk descriptor yang meminjam nama capability core. Optional metadata preserve_opaque dipreservasi exact bytes beserta referensi asetnya; dukungan duplicate/remap unknown extension belum tersedia.

Workspace malformed ditolak pada boundary 02. Reader 04 boleh menerapkan fallback eksplisit dengan warning sesuai bagian 8; boundary ini tidak membuang field/view diam-diam. Font system tidak di-resolve oleh domain, tidak membuat warning palsu atau mengganti family; service font kelak memberi warning fallback.

`ModelError.to_dict()` menghasilkan `{code, reason, path, details}`. Path memakai `$`, field name dan registry/index untuk diagnosis, bukan expression executable. Kode 02: invalid_project, unsupported_version, unsupported_capability, limit_exceeded. Reason mencakup unknown_property, missing_property, duplicate_key, invalid_type, nonfinite_number, invalid_unicode, invalid_dimensions, duplicate_id, missing_node, hierarchy_cycle, parent_mismatch, invalid_membership, group_geometry_mismatch, missing_asset/font, binding_type/value_mismatch, integrity_mismatch. Version error menyertakan actual/supported; capability error menyertakan required/supported bila tersedia. Preview/IO/service DTO memakai mapping tambahan pada segmen pemilik.

Migration registry memerlukan validator source/target, satu successor tiap source dan graph tanpa cycle. Callback menerima staging deepcopy; setiap hasil harus memiliki target schema_version dan lolos validator; error tidak menyentuh sumber. Hasil mencakup payload dan daftar source/target/description langkah. Registry default hanya validator 1.0; versi lain atau jalur tidak terdaftar ditolak unsupported_version. Future migrator wajib menguji ID/assets/opaque-byte preservation dan melengkapi fixture before/after serta IO backup 04. [ADR 0012](adr/0012-domain-schema-freeze.md) dan [baseline 02](baseline-segment02.md) mencatat keputusan dan bukti.
