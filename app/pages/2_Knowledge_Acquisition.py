import streamlit as st
from pathlib import Path
from ui.theming import page_header
from database.database_manager import DatabaseManager
from core.search_filter import SearchFilter

@st.cache_resource
def get_db():
    # Get absolute path to database directory
    db_path = Path(__file__).parent.parent / "database"
    db = DatabaseManager(db_path)
    db.load_all()
    return db

@st.cache_resource
def get_sf():
    return SearchFilter()

def run():
    page_header("Knowledge Acquisition", "Tambah / ubah / hapus entri KB penyakit ikan.")

    db = get_db()
    sf = get_sf()
    tab1, tab2, tab3 = st.tabs(["➕ Gejala", "➕ Penyakit", "➕ Rule"])

    with tab1:
        st.subheader("Tambah Gejala")
        
        search_query = st.text_input("Cek Gejala yang Sudah Ada", placeholder="Ketik nama gejala untuk cek duplikasi...")
        if search_query:
            results = sf.search_symptoms(query=search_query, sort_by="nama")
            if results:
                st.warning(f"Ditemukan {len(results)} gejala yang mirip:")
                for r in results[:5]: # Show top 5
                    st.info(f"**ID:** {r.id}, **Nama:** {r.nama}")
            else:
                st.success("Tidak ada gejala yang mirip. Aman untuk ditambahkan.")

        with st.form("form_gejala", clear_on_submit=True):
            sid = st.text_input("ID Gejala", placeholder="mis. G12")
            name = st.text_input("Nama", placeholder="Bintik Putih")
            desc = st.text_area("Deskripsi", placeholder="Bercak putih pada permukaan tubuh/sirip.")
            species = st.multiselect("Terkait Spesies (opsional)", ["Lele", "Nila", "Gurame"])
            
            submitted = st.form_submit_button("Simpan Gejala")
            if submitted:
                if not sid or not name:
                    st.error("❌ ID Gejala dan Nama harus diisi!")
                else:
                    try:
                        db.add_symptom(sid.strip(), name.strip(), desc.strip(), species)
                        st.success(f"✅ Gejala '{name}' berhasil disimpan.")
                        st.cache_resource.clear() # Reload DB on next run
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    with tab2:
        st.subheader("Tambah Penyakit")

        search_query_disease = st.text_input("Cek Penyakit yang Sudah Ada", placeholder="Ketik nama penyakit untuk cek duplikasi...")
        if search_query_disease:
            results = sf.search_diseases(query=search_query_disease, sort_by="nama")
            if results:
                st.warning(f"Ditemukan {len(results)} penyakit yang mirip:")
                for r in results[:5]: # Show top 5
                    st.info(f"**ID:** {r.id}, **Nama:** {r.nama}")
            else:
                st.success("Tidak ada penyakit yang mirip. Aman untuk ditambahkan.")

        with st.form("form_penyakit", clear_on_submit=True):
            did = st.text_input("ID Penyakit", placeholder="mis. P7")
            dname = st.text_input("Nama Penyakit", placeholder="Bintik Putih (Ich)")
            ddesc = st.text_area("Deskripsi", placeholder="Infeksi protozoa Ichthyophthirius multifiliis.")
            cause = st.text_area("Penyebab", placeholder="Parasit Ichthyophthirius multifiliis")
            treatments = st.text_area("Pengobatan (pisahkan dengan baris baru)", placeholder="Karantina\nNaikkan suhu bertahap\nGaram ikan")
            prevention = st.text_area("Pencegahan (pisahkan dengan baris baru)", placeholder="Karantina ikan baru\nKualitas air stabil")
            
            submitted = st.form_submit_button("Simpan Penyakit")
            if submitted:
                if not did or not dname:
                    st.error("❌ ID Penyakit dan Nama Penyakit harus diisi!")
                else:
                    try:
                        db.add_disease(did.strip(), dname.strip(), ddesc.strip(), cause.strip(), treatments, prevention)
                        st.success(f"✅ Penyakit '{dname}' berhasil disimpan.")
                        st.cache_resource.clear() # Reload DB on next run
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    with tab3:
        st.subheader("Tambah/Perbarui Rule")
        with st.form("form_rule", clear_on_submit=True):
            rid = st.text_input("ID Rule", placeholder="mis. R99")
            cond = st.text_area("IF (symptom IDs, pisahkan baris)", placeholder="G3\nG9").splitlines()
            then = st.text_input("THEN (disease ID)", placeholder="P1")
            cf = st.slider("CF Pakar", 0.0, 1.0, 0.8, 0.05)
            
            submitted = st.form_submit_button("Simpan Rule")
            if submitted:
                try:
                    symptoms_list = [c.strip() for c in cond if c.strip()]
                    disease_id = then.strip()
                    
                    if not rid or not symptoms_list or not disease_id:
                        st.error("❌ Semua field harus diisi!")
                    else:
                        db.add_rule(rid.strip(), symptoms_list, disease_id, cf)
                        st.success(f"✅ Rule '{rid}' disimpan.")
                        st.cache_resource.clear()  # Clear cache to reload DB
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    run()
