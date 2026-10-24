# Migration registry

Registry 02 hanya mendaftarkan validator 1.0. Tidak ada versi native historis lain
atau migration path yang diklaim. `schema/legacy-00b.json` juga berlabel 1.0 dan
dibaca tanpa transformasi.

`tests/test_domain.py` memakai before/after sintetis inline untuk menguji staging,
report langkah, validasi hasil, gagal atomik, cycle/duplicate registration dan
unsupported version/no path. Saat versi baru nyata ditambahkan, simpan pasangan
fixture historis/final di direktori ini dan uji preservasi ID/blob/extension;
jangan melabeli ulang contoh PRD ilustratif sebagai format lama yang didukung.
