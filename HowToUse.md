# 🧭 Panduan Singkat Penggunaan Program

## ⚙️ 1. Prasyarat
Sebelum menjalankan aplikasi, pastikan hal berikut sudah terpasang di perangkat Anda:

- **Python 3.9 atau lebih baru**
- **pip** (biasanya sudah terpasang bersama Python)
- **Koneksi internet aktif** (untuk instalasi dependensi)

---

## 💻 2. Membuat Virtual Environment (opsional tapi disarankan)

### Windows
```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 📦 3. Instalasi Dependensi
Setelah environment aktif, jalankan perintah berikut di terminal:
```bash
pip install -r requirements.txt
```

Isi minimal file `requirements.txt`:
```
streamlit
pandas
pyyaml
pydantic
```

---

## 🚀 4. Menjalankan Program
Masuk ke folder proyek lalu jalankan perintah:
```bash
streamlit run app/main.py
```

Jika berhasil, akan muncul pesan seperti:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```
Klik tautan tersebut atau buka manual di browser Anda.

---

## 🧱 5. Struktur Folder Utama
Pastikan susunan folder seperti berikut:
```
UTS-Prak-AI-B-Kelompok3/
├── app/
│   ├── main.py
│   └── pages/
│       ├── 1_Diagnosis.py
│       ├── 2_Knowledge_Acquisition.py
│       ├── 3_History_&_Reports.py
│       └── 4_KB_Explorer.py
├── core/
│   └── inference_engine.py
├── database/
│   ├── database_manager.py
│   ├── symptoms.json
│   ├── diseases.json
│   └── rules.json
└── requirements.txt
```

---

## ✅ 6. Selesai
Aplikasi siap digunakan.  
Buka di browser pada alamat:
```
http://localhost:8501
```

Untuk menghentikan aplikasi, tekan `Ctrl + C` di terminal.
