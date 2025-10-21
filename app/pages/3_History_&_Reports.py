import streamlit as st
from ui.theming import page_header

def run():
    page_header("History & Reports", "Riwayat konsultasi dan ekspor laporan.")
    st.info("Placeholder: hubungkan dengan services/reporting.py dan logging_service.py untuk menyimpan & ekspor (CSV/PDF).")
    st.write("- Tampilkan tabel riwayat (waktu, gejala, hasil, CF).")
    st.write("- Tombol ekspor CSV/PDF.")

if __name__ == "__main__":
    run()
