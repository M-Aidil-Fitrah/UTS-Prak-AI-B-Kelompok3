import streamlit as st
from pathlib import Path
from ui.theming import page_header
from database.database_manager import DatabaseManager

@st.cache_resource
def get_db():
    db = DatabaseManager(Path("database"))
    db.load_all()
    return db

def run():
    page_header("Knowledge Acquisition", "Tambah / ubah / hapus entri KB penyakit ikan.")

    db = get_db()
    tab1, tab2, tab3 = st.tabs(["➕ Gejala", "➕ Penyakit", "➕ Rule"])

    with tab1:
        st.subheader("Tambah Gejala")
        sid = st.text_input("ID (snake_case)", placeholder="mis. bintik_putih")
        name = st.text_input("Nama", placeholder="Bintik Putih")
        desc = st.text_area("Deskripsi", placeholder="Bercak putih pada permukaan tubuh/sirip.")
        species = st.multiselect("Terkait Spesies (opsional)", ["Lele", "Nila", "Gurame"])
        weight = st.slider("Bobot default", 0.0, 1.0, 1.0, 0.05)
        if st.button("Simpan Gejala"):
            try:
                payload = {"id": sid, "name": name, "description": desc, "weight": weight}
                if species:
                    payload["species"] = species
                db.add_symptom(payload)
                st.success(f"Gejala '{sid}' ditambahkan.")
            except Exception as e:
                st.error(str(e))

    with tab2:
        st.subheader("Tambah Penyakit")
        did = st.text_input("ID Penyakit", placeholder="mis. white_spot_disease")
        dname = st.text_input("Nama Penyakit", placeholder="Bintik Putih (Ich)")
        ddesc = st.text_area("Deskripsi", placeholder="Infeksi protozoa Ichthyophthirius multifiliis.")
        treatments = st.text_area("Tatalaksana (baris-baru)", placeholder="Karantina\nNaikkan suhu bertahap\nGaram ikan dosis X").splitlines()
        prevention = st.text_area("Pencegahan (baris-baru)", placeholder="Karantina ikan baru\nKualitas air stabil\nKepadatan tebar sesuai").splitlines()
        if st.button("Simpan Penyakit"):
            try:
                db.add_disease({
                    "id": did, "name": dname, "description": ddesc,
                    "treatments": treatments, "prevention": prevention
                })
                st.success(f"Penyakit '{did}' ditambahkan.")
            except Exception as e:
                st.error(str(e))

    with tab3:
        st.subheader("Tambah/Perbarui Rule")
        rid = st.text_input("ID Rule", placeholder="mis. R1")
        cond = st.text_area("IF (symptom/derived, pisahkan baris)", placeholder="bintik_putih\nmenggesek_badan").splitlines()
        then = st.text_input("THEN (disease/derived)", placeholder="white_spot_disease")
        cf = st.slider("CF Pakar", 0.0, 1.0, 0.8, 0.05)
        ask_why = st.text_input("WHY (opsional)", placeholder="Bintik putih khas infeksi Ich.")
        recommendation = st.text_input("Rekomendasi (opsional)")
        source = st.text_input("Sumber (opsional, ID dari sources.txt)", placeholder="S1")
        if st.button("Simpan Rule"):
            try:
                db.upsert_rule(rid, {
                    "IF": [c.strip() for c in cond if c.strip()],
                    "THEN": then.strip(),
                    "CF": cf,
                    "ask_why": ask_why or None,
                    "recommendation": recommendation or None,
                    "source": source or None
                })
                st.success(f"Rule '{rid}' disimpan.")
            except Exception as e:
                st.error(str(e))

if __name__ == "__main__":
    run()
