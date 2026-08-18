# ChessAuto

ChessAuto adalah sebuah program otomasi bot catur cerdas yang beroperasi secara lokal menggunakan sistem *Logical State Tracking* berkecepatan tinggi dan terintegrasi dengan model kecerdasan buatan dari Ollama. Program ini dirancang untuk mendeteksi pergerakan bidak secara waktu nyata (real-time) melalui sensor piksel kamera dan mengeksekusi langkah terbaik yang dihasilkan oleh LLM secara mandiri.

## Fitur Utama

1. **Pure Logical Tracking (0ms Delay Sensor)**
   Menggunakan algoritma deteksi pergerakan piksel berbasis BGR (`cv2.absdiff`) yang sangat ringan dan instan. Sensor ini mampu mendeteksi langkah musuh secara seketika tanpa membebani CPU, serta kebal terhadap efek visual tambahan pada layar seperti sorotan (highlight) warna.

2. **Integrasi Local AI (Ollama)**
   Mendukung penggunaan model bahasa besar (LLM) lokal yang dijalankan melalui Ollama. Bot akan mengirimkan format FEN standar kepada AI untuk meminta keputusan langkah selanjutnya.

3. **Injeksi Analisis Taktis Otomatis**
   Program menggunakan pustaka `python-chess` untuk menghitung posisi bidak yang sedang diserang (ancaman) maupun bidak musuh yang dapat dimakan (peluang). Informasi taktis ini disuntikkan secara otomatis ke dalam instruksi utama (prompt) agar AI dapat mengambil keputusan strategis yang presisi.

4. **Eksekusi Fisik Otomatis**
   Sistem terhubung dengan `pyautogui` untuk mengendalikan kursor tetikus secara otomatis guna menjalankan bidak di atas papan catur layar sentuh atau peramban web.

5. **Overlay Visual (ESP)**
   Menampilkan kerangka (grid) papan berukuran 8x8 dan penanda bidak transparan di atas layar permainan untuk memudahkan pemantauan status memori internal bot.

## Prasyarat

Sebelum menjalankan program ini, pastikan sistem Anda telah memenuhi persyaratan berikut:
- Python 3.x terinstal.
- Ollama terinstal dan berjalan di latar belakang (localhost:11434).
- Memiliki setidaknya satu model AI yang telah diunduh di dalam Ollama (contoh: `llama3`, `qwen`, dll).

### Instalasi Pustaka

Pasang seluruh pustaka dependensi Python yang dibutuhkan dengan menjalankan perintah berikut di terminal:

```bash
pip install opencv-python pyautogui keyboard mss numpy chess
```

## Cara Penggunaan

1. Buka antarmuka permainan catur pada layar komputer Anda (misalnya melalui peramban web).
2. Pastikan papan catur masih dalam posisi awal (belum ada bidak yang bergerak).
3. Jalankan program dengan mengeksekusi berkas eksekusi atau menjalankan berkas Python secara langsung:
   ```bash
   python main.py
   ```
4. Pada terminal program, daftar model Ollama yang tersedia akan ditampilkan. Masukkan nomor urut model AI yang ingin Anda gunakan.
5. Proses **Kalibrasi Papan** akan dimulai:
   - Arahkan kursor tetikus tepat ke **SUDUT KIRI ATAS** papan catur, lalu tekan tombol `Enter`.
   - Arahkan kursor tetikus tepat ke **SUDUT KANAN BAWAH** papan catur, lalu tekan tombol `Enter`.
6. Bot akan memindai tingkat kecerahan baris atas dan bawah untuk menentukan apakah Anda bertindak sebagai pemain Putih atau Hitam secara otomatis.
7. Tekan tombol **F10** pada papan tik (keyboard) untuk memulai (AKTIF) atau menghentikan (BERHENTI) bot.
8. Saat aktif, bot akan mulai mendeteksi gerakan dan merespons secara otonom.

## Catatan Keselamatan Keamanan (Safety Mechanism)

Apabila bot sedang dalam keadaan aktif dan Anda menggeser kursor tetikus secara manual (lebih dari 15 piksel), sistem akan mendeteksinya sebagai interupsi manual dan secara otomatis akan mematikan (menonaktifkan) bot untuk mencegah konflik pergerakan kursor. Tekan kembali **F10** jika Anda ingin mengaktifkan ulang bot.
