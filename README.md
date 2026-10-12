# Distributed Prime Number Finder — Master

Implementasi sisi Master untuk tugas Komputasi Paralel dan Terdistribusi.

- **Master:** Galang Maulid Nugraha (247006111109)
- **Worker:** Muhammad Zicco Alfarozi (247006111113)
- **PC 1 / Master:** Windows 11, Python 3.14.0, Wi-Fi `192.168.1.52`
- **PC 2 / Worker:** Python 3.14.2, Wi-Fi `192.168.1.42`

## Struktur

- `master.py`: antarmuka CLI dan penanganan error tingkat atas.
- `benchmark.py`: koneksi persisten, pengukuran, verifikasi, dan ekspor CSV.
- `prime_utils.py`: trial division yang identik untuk baseline dan PC 1.
- `protocol.py`: JSON UTF-8 dengan prefix panjang 4-byte unsigned big-endian.
- `generate_charts.py`: membaca summary CSV dan menghasilkan tiga grafik.
- `tests/`: unit test algoritma dan framing lokal.
- `results/`: CSV detail dan ringkasan hasil nyata.

## Kontrak integrasi

Worker adalah TCP server pada `192.168.1.42:5000`; Master adalah client. Setiap
pesan diawali panjang payload 4 byte (`!I`), lalu JSON UTF-8. Rentang bersifat
inklusif. Master mempertahankan satu koneksi untuk seluruh TASK dan memvalidasi
`type`, `task_id`, `start`, `end`, `prime_count`, serta `compute_seconds` dari
setiap RESULT.

Contoh TASK:

```json
{"type":"TASK","task_id":"run-001","start":500001,"end":1000000}
```

Worker harus menjawab:

```json
{"type":"RESULT","task_id":"run-001","start":500001,"end":1000000,"prime_count":JUMLAH_PRIMA,"compute_seconds":WAKTU_KOMPUTASI}
```

Algoritma menangani nilai `< 2`, memeriksa `2`, menolak bilangan genap lainnya,
lalu mencoba pembagi ganjil sampai `math.isqrt(number)`.

## Instalasi dan tes lokal

Instal dependensi visualisasi:

```powershell
py -3.14 -m pip install -r .\requirements.txt
# atau langsung:
py -3.14 -m pip install matplotlib
```

Dari PowerShell di folder proyek:

```powershell
py -3.14 -m unittest discover -s tests -v
```

Tes ini tidak membuktikan komunikasi dua PC; tes hanya memeriksa algoritma,
pembagian rentang, pembacaan TCP parsial, beberapa frame dalam satu koneksi, dan
validasi RESULT.

## Menjalankan Master

Pastikan kedua laptop berada pada jaringan yang sama, Worker sudah listening,
dan Windows Firewall PC 2 mengizinkan inbound TCP port 5000. Kemudian jalankan:

```powershell
py -3.14 .\master.py --worker-host 192.168.1.42 --worker-port 5000 --sizes 100000 500000 1000000 --repeats 5 --timeout 120
```

Setelah benchmark selesai, tiga PNG otomatis disimpan pada `results/charts/`
dan jendela grafik ditampilkan jika GUI tersedia. Gunakan `--no-show` untuk
hanya menyimpan PNG. Kegagalan GUI tidak menggagalkan benchmark atau menghapus
grafik yang sudah tersimpan.

Pada setiap run, terminal menampilkan jumlah data total; rentang, beban, dan
hasil prima masing-masing PC; hasil gabungan dan pembanding sequential; waktu
sequential/distributed; waktu komputasi Worker; speedup; efficiency; serta status
verifikasi. Seluruh nilai berasal dari objek hasil run yang sama dengan data CSV.

Untuk membuat grafik dari hasil lama **tanpa menjalankan benchmark**:

```powershell
py -3.14 .\master.py --from-summary .\results\summary-20261012-124153.csv
py -3.14 .\master.py --from-summary .\results\summary-20261012-124153.csv --no-show
```

Modul visualisasi juga dapat dijalankan langsung:

```powershell
py -3.14 .\generate_charts.py .\results\summary-20261012-124153.csv --no-show
```

Uji integrasi kecil dapat dilakukan lebih dahulu:

```powershell
Test-NetConnection 192.168.1.42 -Port 5000
py -3.14 .\master.py --sizes 1000 --repeats 1
```

Selain Matplotlib untuk grafik, tidak ada dependensi pihak ketiga. Jika Worker gagal, timeout, menutup koneksi,
atau mengirim respons invalid, program berhenti dengan error dan **tidak**
menggantinya dengan komputasi lokal.

## Metode benchmark

Rentang `[2, N]` dibagi pada titik tengah numerik. PC 1 menghitung bagian bawah
di satu thread lokal sementara PC 2 menghitung bagian atas. Thread dipakai agar
I/O jaringan dan kerja pada PC 2 berlangsung bersamaan dengan PC 1; thread tidak
menghilangkan keterbatasan GIL untuk dua pekerjaan CPU-bound di interpreter
Python yang sama. Implementasi ini tidak menjalankan komputasi CPU-bound kedua
di PC 1 sebagai pengganti Worker.

Untuk setiap repetisi, baseline sequential dihitung di PC 1 menggunakan algoritma
yang sama. Waktu distributed dimulai sebelum thread lokal dan pengiriman TASK,
serta berakhir setelah RESULT diterima, divalidasi, dan kedua hasil digabung.
Jadi waktu tersebut mencakup komunikasi, komputasi kedua PC, dan penggabungan;
handshake koneksi awal tidak dimasukkan ke tiap run karena koneksi digunakan
ulang. Rumusnya:

```text
speedup    = T_sequential / T_distributed
efficiency = speedup / 2 * 100%
```

Output `results/runs-*.csv` berisi tiap run, termasuk `size` (N), `data_count`
(banyak bilangan pada `[2,N]`), rentang kedua PC, dan hasil parsial.
`results/summary-*.csv` berisi mean per ukuran data. Repository sengaja tidak
menyertakan angka benchmark buatan;
CSV hasil baru tercipta setelah integrasi nyata dengan Worker berhasil.
