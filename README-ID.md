# Outlook Commander TUI

Aplikasi terminal interaktif untuk melihat inbox Outlook, Hotmail, dan Live dari banyak akun. Seluruh sumber aplikasi berada di satu file: `outlook_commander.py`.

Bahasa: [English](README.md) | **Bahasa Indonesia**

## Fitur

- Login Microsoft device flow dan penyimpanan refresh token.
- Dashboard inbox multi-akun melalui Microsoft Graph.
- Pencarian subject/pengirim, timestamp waktu lokal, dan pembaca email plain-text.
- Pengambilan email terbaru atau berdasarkan rentang tanggal.
- Proxy HTTP/HTTPS dan SOCKS5 dengan autentikasi serta tombol pengujian koneksi.
- File data portabel yang disimpan di samping EXE.

## Menjalankan dari Kode Sumber

Kebutuhan: Windows, Python 3.14 x64, dan terminal yang mendukung Textual.

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 outlook_commander.py
```

Saat pertama dijalankan, aplikasi membuat file berikut di samping `outlook_commander.py`:

- `email_list.txt` — satu alamat email per baris; metadata password opsional dapat ditulis setelah `|`.
- `accounts_with_tokens.txt` — refresh token dan client ID Microsoft yang tersimpan.

## Membuat EXE Windows

Buat satu file EXE portabel dengan:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-Executable.ps1
```

Output berada di `dist\OutlookCommander.exe`. Pengguna EXE tidak perlu memasang Python maupun package Python. EXE tetap membuka terminal karena antarmukanya memakai Textual.

Saat EXE dijalankan, `email_list.txt` dan `accounts_with_tokens.txt` dibuat dan dibaca di folder EXE, meskipun shortcut memakai working directory berbeda. Simpan EXE di folder yang dapat ditulis; jangan gunakan `Program Files` kecuali pengguna memiliki izin tulis.

## Konfigurasi Pertama

1. Jalankan aplikasi satu kali agar `email_list.txt` dibuat di folder aplikasi.
2. Isi alamat email di `email_list.txt`.
3. Kembali ke aplikasi lalu pilih **Generate New Token**. Jika generator sudah terbuka ketika file diedit, tutup dan buka kembali generator agar daftar akun dimuat ulang.
4. Pilih file input, akun, dan preset client ID.
5. Buka URL Microsoft yang ditampilkan, masukkan device code, lalu setujui akses.
6. Kembali ke Home lalu pilih **Manage Email**.

## Format Data

`email_list.txt` menerima satu akun per baris:

```text
account@example.com
account@example.com|metadata-password-opsional
```

`accounts_with_tokens.txt` menerima salah satu format:

```text
account@example.com|refresh_token|client_id
account@example.com|metadata-password-opsional|refresh_token|client_id
```

Jangan gunakan karakter `|` di dalam nilai field.

## Shortcut

| Tombol | Aksi |
| --- | --- |
| `q` | Keluar |
| `e` | Membuka dashboard dari Home |
| `g` | Membuat token |
| `h` | Kembali ke Home dari dashboard |
| `r` | Memuat ulang inbox aktif |
| `l` | Memuat ulang akun dari file token |
| `Esc` | Menutup atau melewati modal |

## Keamanan

`accounts_with_tokens.txt` berisi kredensial yang dapat mengakses email. Perlakukan sebagai rahasia, jangan commit atau bagikan, dan cabut/rotasi token yang terpapar. `email_list.txt` juga dapat berisi metadata password. Kedua file tidak dibundel ke EXE.

## Struktur Proyek

```text
outlook_commander.py       # Seluruh kode aplikasi
requirements.txt           # Dependensi runtime Python
requirements-build.txt     # Dependensi PyInstaller untuk build
scripts/Build-Executable.ps1
README.md
README-ID.md
dist/OutlookCommander.exe  # Output hasil build
```
