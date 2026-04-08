import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
from fpdf import FPDF

# --- CONFIGURATION ---
st.set_page_config(page_title="GenApAgiE - Gestion Recherche", layout="wide")

def init_db():
    conn = sqlite3.connect('genapagie_final.db')
    c = conn.cursor()
    # Ajout des colonnes age et sexe
    c.execute('''CREATE TABLE IF NOT EXISTS patients 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, age INTEGER, 
                  sexe TEXT, cancer_type TEXT, qdv INTEGER, ecog INTEGER)''')
    conn.commit()
    return conn

conn = init_db()

# --- GÉNÉRATEUR DE RAPPORT PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'GenApAgiE - Rapport Clinique Anonymisé', 0, 1, 'C')
        self.ln(5)

# --- PAGES ---

def questionnaire_page():
    st.header("📝 Nouvelle Inclusion Patient")
    
    with st.expander("📄 Consentement Éclairé", expanded=False):
        consent = st.checkbox("Le patient a signé le formulaire de consentement.")

    if not consent:
        st.warning("Le consentement est obligatoire.")
        return

    with st.form("form_patient"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Âge du patient", min_value=18, max_value=120, value=50)
            sexe = st.radio("Sexe biologique", ["Masculin", "Féminin"], horizontal=True)
        with col2:
            cancer_type = st.selectbox("Localisation", ["Poumon", "Sein", "Colorectal", "Autre"])
            qdv = st.slider("Qualité de Vie (1-10)", 1, 10, 5)
        
        ecog = st.select_slider("Score ECOG", options=[0, 1, 2, 3, 4])
        
        submit = st.form_submit_button("Enregistrer le patient")
        
        if submit:
            c = conn.cursor()
            c.execute("INSERT INTO patients (date, age, sexe, cancer_type, qdv, ecog) VALUES (?, ?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d"), age, sexe, cancer_type, qdv, ecog))
            conn.commit()
            st.success(f"Patient enregistré avec succès. ID généré automatiquement.")

def admin_page():
    st.header("⚙️ Gestion des Données (Admin)")
    df = pd.read_sql_query("SELECT * FROM patients", conn)
    
    if not df.empty:
        st.write("### Base de données actuelle")
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("🗑️ Supprimer un enregistrement")
        id_to_delete = st.number_input("Entrez l'ID du patient à supprimer", min_value=1, step=1)
        
        if st.button("Supprimer définitivement"):
            c = conn.cursor()
            c.execute("DELETE FROM patients WHERE id = ?", (id_to_delete,))
            conn.commit()
            st.warning(f"L'entrée ID {id_to_delete} a été supprimée.")
            st.rerun() # Rafraîchit la page pour voir les changements
    else:
        st.info("La base de données est vide.")

def export_page():
    st.header("💾 Exportation")
    df = pd.read_sql_query("SELECT * FROM patients", conn)
    if not df.empty:
        # Export Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Télécharger Excel pour R", output.getvalue(), "GenApAgiE_Data.xlsx")
    else:
        st.warning("Rien à exporter.")

# --- NAVIGATION ---
st.sidebar.title("🔬 GenApAgiE")
menu = st.sidebar.radio("Aller à :", ["Saisie Patient", "Gestion & Suppression", "Export R"])

if menu == "Saisie Patient": questionnaire_page()
elif menu == "Gestion & Suppression": admin_page()
elif menu == "Export R": export_page()
