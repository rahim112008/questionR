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

def init_db():
    conn = sqlite3.connect('genapagie_full_research.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS data_research 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type_cancer TEXT, 
                  qdv INTEGER, sommeil INTEGER, ecog INTEGER, risque_ia TEXT, bio_marker_val REAL)''')
    conn.commit()
    return conn

conn = init_db()

# --- LOGIQUE IA ---
def predict_fatigue_risk(qdv, sommeil, ecog):
    X_train = np.array([[8, 1, 0], [2, 5, 3], [5, 3, 1], [9, 1, 0], [3, 4, 4], [6, 2, 1]])
    y_train = np.array([0, 1, 0, 0, 1, 0]) 
    model = RandomForestClassifier(n_estimators=10)
    model.fit(X_train, y_train)
    prediction = model.predict([[qdv, sommeil, ecog]])
    return "Élevé" if prediction[0] == 1 else "Faible"

# --- GÉNÉRATEUR DE RAPPORT PDF (ANONYMISÉ) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Laboratoire GenApAgiE - Rapport de Recherche Anonymisé', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Date de génération : {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')
        self.ln(10)

def generate_pdf(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # En-tête du tableau
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(30, 10, 'ID Data', 1, 0, 'C', 1)
    pdf.cell(40, 10, 'Pathologie', 1, 0, 'C', 1)
    pdf.cell(20, 10, 'QdV', 1, 0, 'C', 1)
    pdf.cell(30, 10, 'Risque IA', 1, 0, 'C', 1)
    pdf.cell(40, 10, 'Bio Marqueur', 1, 1, 'C', 1)
    
    # Données
    for index, row in df.iterrows():
        pdf.cell(30, 10, str(row['id']), 1)
        pdf.cell(40, 10, str(row['type_cancer']), 1)
        pdf.cell(20, 10, str(row['qdv']), 1)
        pdf.cell(30, 10, str(row['risque_ia']), 1)
        pdf.cell(40, 10, str(row['bio_marker_val']), 1, 1)
        
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.title("🔬 Labo GenApAgiE")
st.sidebar.caption("Plateforme de Recherche Clinique")
st.sidebar.divider()
menu = st.sidebar.radio("Navigation", ["Dashboard", "Saisie & IA", "Import Bio", "Rapports & Export"])

# --- PAGES ---

def dashboard_page():
    st.header("📊 Tableau de Bord")
    df = pd.read_sql_query("SELECT * FROM data_research", conn)
    if not df.empty:
        col1, col2 = st.columns(2)
        col1.metric("Inclusions", len(df))
        col2.metric("Alertes IA", len(df[df['risque_ia'] == 'Élevé']))
        st.line_chart(df.set_index('date')['qdv'])

def questionnaire_ia_page():
    st.header("📝 Saisie & IA")
    with st.form("main_form"):
        t_cancer = st.selectbox("Type de cancer", ["Sein", "Poumon", "Colorectal", "Autre"])
        qdv = st.slider("Qualité de vie (1-10)", 1, 10, 7)
        sommeil = st.select_slider("Troubles sommeil", options=[1, 2, 3, 4, 5])
        ecog = st.number_input("Score ECOG", 0, 4, 0)
        bio_val = st.number_input("Marqueur bio", value=0.0)
        
        if st.form_submit_button("Analyser & Enregistrer"):
            risque = predict_fatigue_risk(qdv, sommeil, ecog)
            c = conn.cursor()
            c.execute("INSERT INTO data_research (date, type_cancer, qdv, sommeil, ecog, risque_ia, bio_marker_val) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M"), t_cancer, qdv, sommeil, ecog, risque, bio_val))
            conn.commit()
            st.success(f"Données enregistrées. Analyse prédictive terminée.")

def import_bio_page():
    st.header("📂 Importation")
    st.file_uploader("Fichier Labo", type=['xlsx', 'csv'])

def export_page():
    st.header("💾 Rapports et Exports")
    df = pd.read_sql_query("SELECT * FROM data_research", conn)
    
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Base Excel")
            output_exc = io.BytesIO()
            with pd.ExcelWriter(output_exc, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Télécharger Excel", output_exc.getvalue(), "Export_Labo.xlsx")
            
        with col2:
            st.subheader("Rapport PDF")
            pdf_data = generate_pdf(df)
            st.download_button("📥 Générer le Rapport Anonyme", pdf_data, "Rapport_Anonymise.pdf", "application/pdf")
    else:
        st.warning("Aucune donnée disponible.")

# --- ROUTAGE ---
if menu == "Dashboard": dashboard_page()
elif menu == "Saisie & IA": questionnaire_ia_page()
elif menu == "Import Bio": import_bio_page()
elif menu == "Rapports & Export": export_page()

st.sidebar.divider()
st.sidebar.caption("© 2026 GenApAgiE | Data Persistence Active")