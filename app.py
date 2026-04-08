import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
from sklearn.ensemble import RandomForestClassifier
import numpy as np
from fpdf import FPDF

# --- CONFIGURATION ET IDENTITÉ ---
st.set_page_config(page_title="GenApAgiE Research Suite", layout="wide")

# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect('genapagie_2026.db')
    c = conn.cursor()
    # Table unique avec toutes les variables nécessaires
    c.execute('''CREATE TABLE IF NOT EXISTS research_data 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, 
                  age INTEGER, 
                  sexe TEXT, 
                  cancer_type TEXT, 
                  qdv INTEGER, 
                  sommeil INTEGER, 
                  ecog INTEGER, 
                  risque_ia TEXT, 
                  bio_marker REAL,
                  consent INTEGER)''')
    conn.commit()
    return conn

conn = init_db()

# --- LOGIQUE IA PRÉDICTIVE ---
def predict_fatigue_risk(qdv, sommeil, ecog):
    # Modèle simplifié pour démo (à entraîner avec vos données réelles sous R plus tard)
    X_train = np.array([[8, 1, 0], [2, 5, 3], [5, 3, 1], [9, 1, 0], [3, 4, 4]])
    y_train = np.array([0, 1, 0, 0, 1]) # 0: Faible, 1: Élevé
    model = RandomForestClassifier(n_estimators=10)
    model.fit(X_train, y_train)
    prediction = model.predict([[qdv, sommeil, ecog]])
    return "Élevé" if prediction[0] == 1 else "Faible"

# --- GÉNÉRATEUR DE RAPPORT PDF (ANONYME) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Laboratoire GenApAgiE - Rapport Clinique Anonymisé', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Généré le : {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)

def generate_pdf(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=9)
    # En-tête du tableau
    pdf.set_fill_color(240, 240, 240)
    cols = ['ID', 'Âge', 'Sexe', 'Pathologie', 'QdV', 'Risque IA']
    w = [15, 15, 20, 50, 20, 40]
    for i in range(len(cols)):
        pdf.cell(w[i], 10, cols[i], 1, 0, 'C', 1)
    pdf.ln()
    # Lignes
    for _, row in df.iterrows():
        pdf.cell(w[0], 10, str(row['id']), 1)
        pdf.cell(w[1], 10, str(row['age']), 1)
        pdf.cell(w[2], 10, str(row['sexe']), 1)
        pdf.cell(w[3], 10, str(row['cancer_type']), 1)
        pdf.cell(w[4], 10, str(row['qdv']), 1)
        pdf.cell(w[5], 10, str(row['risque_ia']), 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE LATÉRALE ---
st.sidebar.title("🔬 Labo GenApAgiE")
st.sidebar.caption("Plateforme Intégrée de Recherche")
st.sidebar.divider()
menu = st.sidebar.radio("Navigation", 
                        ["Dashboard", "Saisie Patient & IA", "Gestion & Suppression", "Export & Rapports"])

# --- PAGES ---

def dashboard_page():
    st.header("📊 Vue d'ensemble des données")
    df = pd.read_sql_query("SELECT * FROM research_data", conn)
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Patients", len(df))
        c2.metric("Âge Moyen", round(df['age'].mean(), 1))
        c3.metric("Alertes IA", len(df[df['risque_ia'] == 'Élevé']))
        st.subheader("Répartition par Pathologie")
        st.bar_chart(df['cancer_type'].value_counts())
    else:
        st.info("La base de données est actuellement vide.")

def questionnaire_page():
    st.header("📝 Nouvelle Inclusion")
    
    with st.expander("📄 Consentement Éclairé", expanded=True):
        st.write("Le patient accepte l'utilisation anonymisée de ses données pour le labo GenApAgiE.")
        consent = st.checkbox("Consentement obtenu")

    if not consent:
        st.warning("Veuillez valider le consentement pour débloquer le formulaire.")
        return

    with st.form("main_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Âge du patient", 18, 110, 55)
            sexe = st.radio("Sexe", ["Masculin", "Féminin"], horizontal=True)
            cancer_type = st.selectbox("Type de cancer", ["Poumon", "Sein", "Colorectal", "Autre"])
        with col2:
            qdv = st.slider("Qualité de vie (1-10)", 1, 10, 7)
            sommeil = st.select_slider("Qualité du sommeil", options=[1, 2, 3, 4, 5])
            ecog = st.number_input("Score ECOG (0-4)", 0, 4, 0)
        
        bio_marker = st.number_input("Valeur Biomarqueur (optionnel)", value=0.0)
        
        if st.form_submit_button("Enregistrer et Analyser"):
            risque = predict_fatigue_risk(qdv, sommeil, ecog)
            c = conn.cursor()
            c.execute('''INSERT INTO research_data 
                         (date, age, sexe, cancer_type, qdv, sommeil, ecog, risque_ia, bio_marker, consent) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (datetime.now().strftime("%Y-%m-%d"), age, sexe, cancer_type, qdv, sommeil, ecog, risque, bio_marker, 1))
            conn.commit()
            st.success(f"Patient enregistré. ID généré automatiquement. Risque IA : {risque}")
            if risque == "Élevé": st.error("Alerte : Risque de fatigue sévère détecté.")

def admin_page():
    st.header("⚙️ Gestion de la Base de Données")
    df = pd.read_sql_query("SELECT * FROM research_data", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.divider()
        st.subheader("🗑️ Supprimer une entrée")
        id_del = st.number_input("ID à supprimer", min_value=1, step=1)
        if st.button("Confirmer la suppression"):
            c = conn.cursor()
            c.execute("DELETE FROM research_data WHERE id = ?", (id_del,))
            conn.commit()
            st.warning(f"Entrée ID {id_del} supprimée.")
            st.rerun()
    else:
        st.info("Aucune donnée à gérer.")

def export_page():
    st.header("💾 Exportation & Rapports PDF")
    df = pd.read_sql_query("SELECT * FROM research_data", conn)
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Export Excel (Analyse R)")
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='xlsxwriter')
            st.download_button("📥 Télécharger Excel", towrite.getvalue(), "GenApAgiE_Data.xlsx")
        with col2:
            st.subheader("Rapport PDF (Synthèse)")
            pdf_bytes = generate_pdf(df)
            st.download_button("📥 Télécharger PDF Anonyme", pdf_bytes, "Rapport_GenApAgiE.pdf")
    else:
        st.warning("Pas de données disponibles pour l'export.")

# --- ROUTAGE ---
if menu == "Dashboard": dashboard_page()
elif menu == "Saisie Patient & IA": questionnaire_page()
elif menu == "Gestion & Suppression": admin_page()
elif menu == "Export & Rapports": export_page()

st.sidebar.divider()
st.sidebar.caption("© 2026 GenApAgiE Lab | GH-Algeria")
