"""
Halaman untuk menjelajahi Knowledge Base (KB) sistem pakar.

Memungkinkan pengguna untuk mencari, memfilter, dan melihat detail dari:
- Gejala (Symptoms)
- Penyakit (Diseases)
- Aturan (Rules)

Menggunakan modul `search_filter` untuk logika pencarian dan `database_manager`
untuk akses data.
"""
import streamlit as st
from core.search_filter import SearchFilter
import pandas as pd

# Inisialisasi search filter
sf = SearchFilter()

def show_symptoms_explorer():
    """Tampilkan UI untuk eksplorasi gejala."""
    st.subheader("Symptom Explorer")

    # Ambil semua gejala untuk mendapatkan daftar spesies
    all_symptoms = sf.get_all_symptoms()
    # Correctly iterate over object attributes
    all_species = sorted(list(set(
        species_item
        for s in all_symptoms.values()
        if hasattr(s, 'species') and s.species
        for species_item in s.species
    )))


    # Filter UI
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Cari berdasarkan nama, ID, atau deskripsi gejala:", key="symptom_query")
    with col2:
        species_filter = st.multiselect("Filter berdasarkan spesies:", options=all_species, key="symptom_species")

    # Panggil fungsi search
    results = sf.search_symptoms(query=query, species_filter=species_filter, sort_by="id")

    st.write(f"Menampilkan **{len(results)}** dari **{len(all_symptoms)}** gejala.")

    if not results:
        st.warning("Tidak ada gejala yang cocok dengan kriteria pencarian Anda.")
        return

    # Tampilkan hasil dalam bentuk tabel
    display_data = []
    for r in results:
        display_data.append({
            "ID": r.id,
            "Nama Gejala": r.nama,
            "Spesies": ", ".join(r.species) if hasattr(r, 'species') and r.species else "Umum"
        })
    
    st.dataframe(pd.DataFrame(display_data), width="stretch")


def show_diseases_explorer():
    """Tampilkan UI untuk eksplorasi penyakit."""
    st.subheader("Disease Explorer")

    all_diseases = sf.get_all_diseases()
    # Correctly iterate over object attributes
    all_species = sorted(list(set(
        species_item
        for d in all_diseases.values()
        if hasattr(d, 'species') and d.species
        for species_item in d.species
    )))

    # Filter UI
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Cari berdasarkan nama, ID, atau deskripsi penyakit:", key="disease_query")
    with col2:
        species_filter = st.multiselect("Filter berdasarkan spesies:", options=all_species, key="disease_species")

    results = sf.search_diseases(query=query, species_filter=species_filter, sort_by="id")

    st.write(f"Menampilkan **{len(results)}** dari **{len(all_diseases)}** penyakit.")

    if not results:
        st.warning("Tidak ada penyakit yang cocok dengan kriteria pencarian Anda.")
        return

    # Tampilkan hasil dalam expander
    for r in results:
        with st.expander(f"**{r.id}**: {r.nama}"):
            st.markdown(f"**Deskripsi:** {r.deskripsi or '-'}")
            st.markdown(f"**Penyebab:** {r.penyebab or '-'}")
            st.markdown(f"**Pengobatan:** {r.pengobatan or '-'}")
            st.markdown(f"**Pencegahan:** {r.pencegahan or '-'}")
            st.markdown(f"**Spesies:** {', '.join(r.species) if hasattr(r, 'species') and r.species else 'Umum'}")


def show_rules_explorer():
    """Tampilkan UI untuk eksplorasi aturan."""
    st.subheader("Rule Explorer")

    all_rules = sf.get_all_rules()
    all_symptoms = sf.get_all_symptoms()
    all_diseases = sf.get_all_diseases()

    symptom_options = {sid: f"{sid}: {s.nama}" for sid, s in all_symptoms.items()}
    disease_options = {did: f"{did}: {d.nama}" for did, d in all_diseases.items()}

    # Filter UI
    query = st.text_input("Cari berdasarkan ID, why, atau recommendation:", key="rule_query")
    
    col1, col2 = st.columns(2)
    with col1:
        antecedent_filter = st.selectbox(
            "Filter aturan yang mengandung gejala (IF):", 
            options=[""] + list(symptom_options.keys()),
            format_func=lambda x: "Pilih gejala..." if x == "" else symptom_options[x],
            key="rule_antecedent"
        )
    with col2:
        consequent_filter = st.selectbox(
            "Filter aturan yang menghasilkan penyakit (THEN):", 
            options=[""] + list(disease_options.keys()),
            format_func=lambda x: "Pilih penyakit..." if x == "" else disease_options[x],
            key="rule_consequent"
        )

    results = sf.search_rules(
        query=query, 
        antecedent_filter=antecedent_filter or None, 
        consequent_filter=consequent_filter or None,
        sort_by="id"
    )

    st.write(f"Menampilkan **{len(results)}** dari **{len(all_rules)}** aturan.")

    if not results:
        st.warning("Tidak ada aturan yang cocok dengan kriteria pencarian Anda.")
        return

    # Tampilkan hasil
    for r_id, r_body in results.items():
        if_clause = " AND ".join(r_body.get('IF', []))
        then_clause = r_body.get('THEN', '')
        cf_val = r_body.get('CF', 1.0)
        
        st.code(f"RULE {r_id}:\nIF {if_clause}\nTHEN {then_clause}\nCF = {cf_val}", language="plaintext")


def run():
    """Fungsi utama untuk menjalankan halaman KB Explorer."""
    st.set_page_config(page_title="Knowledge Base Explorer", layout="wide")
    st.title("🔍 Knowledge Base Explorer")
    st.markdown("Gunakan halaman ini untuk menjelajahi, mencari, dan memfilter semua data dalam basis pengetahuan sistem pakar.")

    tab1, tab2, tab3 = st.tabs(["Gejala (Symptoms)", "Penyakit (Diseases)", "Aturan (Rules)"])

    with tab1:
        show_symptoms_explorer()

    with tab2:
        show_diseases_explorer()

    with tab3:
        show_rules_explorer()

if __name__ == "__main__":
    run()
