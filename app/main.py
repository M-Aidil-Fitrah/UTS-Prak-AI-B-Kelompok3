import streamlit as st
from pathlib import Path
import yaml

CONFIG_PATH = Path("configs/app.yaml")

@st.cache_resource
def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "app": {"name": "Sistem Pakar Ikan Air Tawar – Kelompok 3", "theme": "dark"},
        "inference": {"mode": "forward", "min_confidence": 0.6},
        "database": {"path": "database/", "auto_reload": True},
        "ui": {"show_trace": True, "max_symptoms_selectable": 10}
    }

CONFIG = load_config()

st.set_page_config(
    page_title=CONFIG["app"]["name"],
    page_icon="🐟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar hanya untuk informasi, tidak ada navigasi manual
st.sidebar.title("🐟 " + CONFIG["app"]["name"])
st.sidebar.caption("Frontend GUI – Streamlit")

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ Konfigurasi Sistem")
st.sidebar.info(f"**Mode Inferensi:** {CONFIG['inference']['mode'].upper()}")
st.sidebar.info(f"**Threshold CF:** {CONFIG['inference']['min_confidence']}")
st.sidebar.info(f"**Database:** `{CONFIG['database']['path']}`")

st.sidebar.divider()
st.sidebar.markdown("### 📚 Tentang Sistem")
st.sidebar.markdown("""
**Kelompok 3**  
Sistem Pakar untuk mendiagnosis penyakit pada ikan air tawar menggunakan metode Forward Chaining dan Certainty Factor.
""")

# Konten halaman utama
st.title("🐟 Sistem Pakar Penyakit Ikan Air Tawar")
st.markdown("### Selamat Datang di Sistem Diagnosis Penyakit Ikan")

# Hero section
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    **Sistem Pakar** ini dirancang untuk membantu pembudidaya ikan air tawar dalam mendiagnosis penyakit 
    yang menyerang ikan budidaya mereka, khususnya **Lele, Nila, dan Gurame**.
    
    #### 🎯 Cara Kerja Sistem:
    1. **Pilih gejala** yang dialami ikan Anda
    2. **Tentukan tingkat keyakinan** terhadap gejala tersebut
    3. Sistem akan **menganalisis** menggunakan Forward Chaining & Certainty Factor
    4. **Dapatkan hasil diagnosis** lengkap dengan rekomendasi pengobatan
    
    #### 🔬 Metode yang Digunakan:
    - **Forward Chaining**: Metode inferensi dari gejala ke kesimpulan
    - **Certainty Factor (CF)**: Menghitung tingkat kepastian diagnosis
    """)

with col2:
    st.info("""
    **📊 Statistik Knowledge Base**
    
    - 🔴 **19 Gejala**
    - 🟢 **11 Penyakit**  
    - 🔵 **11 Rules**
    - 🟡 **3 Jenis Ikan**
    """)
    
    st.success("✅ Sistem Aktif")
    st.caption("Database siap digunakan")

st.divider()

# Fitur-fitur utama
st.markdown("### 🚀 Fitur-Fitur Sistem")

feature_cols = st.columns(4)

with feature_cols[0]:
    st.markdown("#### 🔍 Diagnosis")
    st.markdown("""
    Diagnosa penyakit berdasarkan gejala yang dipilih dengan tingkat kepastian tinggi.
    """)

with feature_cols[1]:
    st.markdown("#### 📝 Knowledge Acquisition")
    st.markdown("""
    Tambah, edit, atau hapus rules, gejala, dan penyakit pada knowledge base.
    """)

with feature_cols[2]:
    st.markdown("#### 📊 History & Reports")
    st.markdown("""
    Lihat riwayat diagnosis dan buat laporan dalam format TXT, PDF, atau CSV.
    """)

with feature_cols[3]:
    st.markdown("#### 🗂️ KB Explorer")
    st.markdown("""
    Jelajahi isi knowledge base: symptoms, diseases, dan rules yang tersedia.
    """)

st.divider()

# Informasi gejala yang tersedia
st.markdown("### 🔍 Gejala yang Dapat Diidentifikasi")

symptom_cols = st.columns(3)

with symptom_cols[0]:
    st.markdown("#### Gejala Fisik")
    st.markdown("""
    - Bintik putih pada kulit/sirip
    - Luka atau borok
    - Insang pucat/rusak
    - Sirip rusak/terkikis
    - Warna tubuh memucat
    - Mata menonjol/bengkak
    - Perdarahan pada sirip/tubuh
    - Sisik terlepas/mengelupas
    - Perut kembung (dropsy)
    """)

with symptom_cols[1]:
    st.markdown("#### Gejala Perilaku")
    st.markdown("""
    - Nafsu makan menurun
    - Berenang tidak normal
    - Megap-megap di permukaan
    - Menggosok tubuh ke dasar
    - Lemas & diam di dasar
    """)

with symptom_cols[2]:
    st.markdown("#### Gejala Lingkungan")
    st.markdown("""
    - Tubuh berlendir berlebih
    - Kutu air menempel
    - Permukaan kasar/kusam
    - Lapisan kapas putih/abu-abu
    - Air kolam keruh/berbau
    """)

st.divider()

# Informasi penyakit umum
st.markdown("### 🦠 Penyakit yang Dapat Didiagnosis")

disease_info = st.columns(3)

with disease_info[0]:
    with st.expander("🔴 Penyakit Bakterial"):
        st.markdown("""
        - **P2**: Aeromonas hydrophila (Borok)
        - **P3**: Bacterial Gill Disease (BGD)
        - **P5**: Streptococcosis
        - **P7**: Motile Aeromonad Septicemia (MAS)
        - **P10**: Pseudomoniasis
        """)

with disease_info[1]:
    with st.expander("🟡 Penyakit Parasit"):
        st.markdown("""
        - **P1**: White Spot Disease (Ichthyophthiriasis)
        - **P4**: Argulosis (Kutu Air)
        - **P6**: Infestasi Ektoparasit Protozoa
        - **P8**: Ichthyophthiriasis (White Spot)
        """)

with disease_info[2]:
    with st.expander("🟢 Penyakit Jamur & Lingkungan"):
        st.markdown("""
        - **P9**: Saprolegniasis (Jamur Kapas)
        - **P11**: Masalah Kualitas Air (Stres Lingkungan)
        """)

st.divider()

# Panduan singkat
st.markdown("### 📖 Panduan Penggunaan")

guide_cols = st.columns(2)

with guide_cols[0]:
    st.markdown("""
    #### Untuk Diagnosis Baru:
    1. Buka halaman **Diagnosis** dari menu navigasi
    2. Pilih jenis ikan (Lele/Nila/Gurame) - opsional
    3. Pilih gejala yang terlihat (maksimal 10)
    4. Atur tingkat keyakinan (0.0 - 1.0)
    5. Klik **Jalankan Diagnosis**
    6. Lihat hasil dan rekomendasi pengobatan
    7. Sistem juga memberikan saran gejala tambahan jika diperlukan
    """)

with guide_cols[1]:
    st.markdown("""
    #### Mengelola Knowledge Base:
    1. Buka halaman **Knowledge Acquisition**
    2. Pilih tab: Rules, Symptoms, atau Diseases
    3. Tambah data baru atau edit yang sudah ada
    4. Validasi perubahan dengan benar
    5. Simpan ke database
    6. Sistem akan otomatis reload data
    """)

st.divider()

# Informasi metode
st.markdown("### 🧠 Metode Inferensi")

method_cols = st.columns(2)

with method_cols[0]:
    st.markdown("#### Forward Chaining")
    st.markdown("""
    Sistem menggunakan metode **Forward Chaining** (data-driven reasoning) dimana:
    - Dimulai dari **fakta** (gejala yang dipilih pengguna)
    - Sistem mencari **rules** yang sesuai dengan gejala
    - Mengevaluasi semua kemungkinan penyakit
    - Memberikan **kesimpulan** berdasarkan CF tertinggi
    
    **Keuntungan:**
    - Sesuai untuk diagnosis medis/veteriner
    - Efisien untuk multiple conclusions
    - Trace reasoning dapat dijelaskan
    """)

with method_cols[1]:
    st.markdown("#### Certainty Factor (CF)")
    st.markdown("""
    **Certainty Factor** digunakan untuk menghitung tingkat kepastian dengan rumus:
    
    ```
    CF(H,E) = CF(H) × CF(E)
    ```
    
    Dimana:
    - **CF(H)**: Certainty Factor dari rule (pakar)
    - **CF(E)**: Certainty Factor dari user (keyakinan)
    - **CF(H,E)**: Hasil kombinasi (0.0 - 1.0)
    
    **Threshold Sistem:** 0.6 (60%)
    
    Penyakit dengan CF ≥ 0.6 akan ditampilkan sebagai diagnosis.
    """)

st.divider()

# Footer
st.markdown("---")
footer_cols = st.columns([2, 1])

with footer_cols[0]:
    st.caption("""
    **Sistem Pakar Penyakit Ikan Air Tawar** | Kelompok 3  
    Universitas [Nama Universitas] | Mata Kuliah: Praktikum AI
    """)

with footer_cols[1]:
    st.caption("""
    💡 **Mulai diagnosis** dengan memilih menu **Diagnosis** di sidebar →
    """)
