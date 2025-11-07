# Image Renamer

Alat CLI sederhana untuk mengganti nama file gambar di sebuah folder menjadi urutan angka.

Fitur
- Ganti nama gambar menjadi urutan seperti IMG_001.jpg, IMG_002.jpg, …
- Mendukung berbagai ekstensi gambar umum (bisa dikonfigurasi)
- Penyortiran alami berdasarkan nama atau berdasarkan waktu modifikasi (mtime)
- Mode uji coba (dry-run) tanpa perubahan nyata
- Penggantian nama aman dari tabrakan (menambahkan _1, _2 jika diperlukan)

Penggunaan cepat

Lihat rencana perubahan terlebih dulu (dry-run):

```
python rename_images.py --dir "." --prefix IMG --start 1 --padding 3 --dry-run
```

Jalankan perubahan sebenarnya dengan menghapus `--dry-run`:

```
python rename_images.py --dir "." --prefix IMG --start 1 --padding 3
```

Penamaan berbasis pola (pattern)

Anda bisa memakai `--pattern` dengan sintaks format Python dan variabel `n` untuk nomor urut. Contoh:

```
python rename_images.py --dir . --pattern "test_board_{n}"
python rename_images.py --dir . --pattern "test_board_{n:03d}"    # dengan zero-padding
python rename_images.py --dir . --pattern "test_board_{n:03d}.png" # mengatur ekstensi secara eksplisit
```

Jika `--pattern` digunakan, opsi ini akan mengabaikan `--prefix`, `--sep`, dan `--padding`.

Ekspor mapping (name_raw / name_change)

Anda bisa mengekspor CSV berisi pasangan nama asli dan nama baru dengan `--map-csv`.
CSV berisi dua kolom: `name_raw` dan `name_change`, berguna untuk pencatatan atau membuat skrip undo.

```
python rename_images.py --dir . --pattern "test_board_{n:03d}" --map-csv mapping.csv --dry-run
```

Terapkan mapping CSV (rename dari name_raw -> name_change)

Buat CSV dengan header `name_raw,name_change` (hanya basename). Contoh `mapping.csv`:

```
name_raw,name_change
IMG_001.jpg,test_board_001.jpg
IMG_002.jpg,test_board_002.jpg
```

Lalu jalankan:

```
python rename_images.py --dir . --apply-csv mapping.csv --dry-run
python rename_images.py --dir . --apply-csv mapping.csv
```

Script akan mencoba pencocokan tidak peka huruf besar-kecil jika `name_raw` tidak ditemukan persis, akan mempertahankan ekstensi jika `name_change` tidak mencantumkan ekstensi, dan menghindari tabrakan nama dengan menambahkan `_1`, `_2`, dst.


## Parameter CLI

Berikut daftar parameter untuk perintah `rename_images.py`:

- `--dir <path>`: Folder yang berisi gambar yang akan di-rename. Default: `.` (folder saat ini).
- `--pattern "teks"`: Pola nama berbasis format Python dengan variabel `n`, contoh: `"test_board_{n:03d}"`. Jika diisi, opsi `--prefix`, `--sep`, `--padding` diabaikan. Default: tidak ada.
- `--prefix "Teks"`: Prefix nama file saat tidak memakai `--pattern`. Contoh hasil: `PREFIX_001.jpg`. Default: `IMG`.
- `--sep "_"`: Pemisah antara prefix dan nomor urut. Default: `_`.
- `--start N`: Nomor awal urutan. Default: `1`.
- `--padding K`: Banyak digit untuk zero-padding nomor, mis. `3` → `001`. Default: `3`.
- `--exts "jpg,jpeg,png,gif,webp,bmp"`: Daftar ekstensi yang diproses, dipisahkan koma. Default: `jpg,jpeg,png,gif,webp,bmp`.
- `--sort name|mtime`: Urutan pemrosesan file: `name` (natural) atau `mtime` (waktu modifikasi). Default: `name`.
- `--dry-run`: Tampilkan rencana perubahan tanpa melakukan rename. Default: off.
- `--map-csv mapping.csv`: Ekspor rencana rename ke CSV dengan kolom `name_raw,name_change`. Default: tidak ada.
- `--apply-csv mapping.csv`: Terapkan rename berdasarkan CSV `name_raw -> name_change`. Default: tidak ada.

Contoh singkat:

```
# 1) Rename berurutan dengan prefix
python rename_images.py --dir . --prefix IMG --start 1 --padding 3

# 2) Pakai pattern dengan zero-padding dan ekstensi PNG
python rename_images.py --dir . --pattern "test_board_{n:03d}.png"

# 3) Ekspor mapping tanpa mengubah apapun (dry-run)
python rename_images.py --dir . --pattern "test_board_{n:03d}" --map-csv mapping.csv --dry-run

# 4) Terapkan mapping hasil edit manual
python rename_images.py --dir . --apply-csv mapping.csv
```

Catatan
- Proses rename dilakukan di tempat (in-place). Pastikan melakukan backup jika perlu mempertahankan nama asli.
- Jika terjadi tabrakan nama, script akan menambahkan akhiran `_1`, `_2`, dst.
- Di Windows, jika path mengandung spasi, gunakan tanda kutip: `"C:\\Folder Dengan Spasi"`.

Kompatibilitas
- Memerlukan Python 3.7+

## Build Windows .exe (PyInstaller)

Anda bisa membuat executable mandiri untuk CLI dan GUI.

Opsi A — gunakan skrip build yang disediakan:

```
build.bat
```

Hasilnya:
- `dist/ImageRenamerCLI.exe`
- `dist/ImageRenamerGUI.exe`

Opsi B — jalankan perintah manual (cmd):

```
pyinstaller --noconfirm --onefile --name ImageRenamerCLI "rename_images.py"
pyinstaller --noconfirm --onefile --windowed --name ImageRenamerGUI "gui_rename.py"
```

