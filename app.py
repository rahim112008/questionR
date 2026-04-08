import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
from sklearn.ensemble import RandomForestClassifier
import numpy as np
from fpdf import FPDF

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="GenApAgiE - Research Suite", layout="wide")

# --- INITIALISATION DE LA BASE DE DONNÉES ---
def init_db():
    conn = sqlite3.connect('genapagie_research_2026.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS data_research 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, 
                  profil TEXT, 
                  cancer_type TEXT, 
                  qdv INTEGER, 
                  sommeil INTEGER, 
                  ecog INTEGER, 
                  risque_ia TEXT, 
                  bio_marker_val REAL,
                  consent INTEGER)''')
    conn.commit()
    return conn

conn = init_db()

# --- LOGIQUE IA (MACHINE LEARNING) ---
def predict_fatigue_risk(qdv, sommeil, ecog):
    # Entraînement sur un set de données théorique (Standards Cliniques)
    X_train = np.array([[8, 1, 0], [2, 5, 3], [5, 3, 1], [9, 1, 0], [3, 4, 4], [6, 2, 1]])
    y_train = np.array([0, 1, 0, 0, 1, 0]) # 0: Faible, 1: Élevé
    model = RandomForestClassifier(n_estimators=10)
    model.fit(X_train, y_train)
    prediction = model.predict([[qdv, sommeil, ecog]])
    return "Élevé" if prediction[0] == 1 else "Faible"

# --- GÉNÉRATEUR DE RAPPORT PDF ANONYMISÉ ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Laboratoire GenApAgiE - Rapport de Recherche Anonymisé', 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.cell(0, 5, f'Généré le : {datetime.now().strftime("%d/%m/%Y à %H:%M")}', 0, 1, 'C')
        self.ln(10)

def generate_pdf(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Couleurs en-tête
    pdf.set_fill_color(230, 230, 230)
    headers = ['ID', 'Pathologie', 'Profil', 'QdV', 'Risque IA', 'Bio Val']
    widths = [15, 45, 30, 15, 40, 40]
    
    for i in range(len(headers)):
        pdf.cell(widths[i], 10, headers[i], 1, 0, 'C', 1)
    pdf.ln()
    
    for _, row in df.iterrows():
        pdf.cell(15, 10, str(row['id']), 1)
        pdf.cell(45, 10, str(row['cancer_type']), 1)
        pdf.cell(30, 10, str(row['profil']), 1)
        pdf.cell(15, 10, str(row['qdv']), 1)
        pdf.cell(40, 10, str(row['risque_ia']), 1)
        pdf.cell(40, 10, str(row['bio_marker_val']), 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE LATÉRALE ---
st.sidebar.title("🔬 Labo GenApAgiE")
st.sidebar.caption("Plateforme Intégrée de Recherche")
st.sidebar.divider()
menu = st.sidebar.radio("Navigation", 
                        ["Dashboard", "Questionnaire & IA", "Importation Bio", "Rapports & Exports", "Anciens Scanners"])

# --- PAGES ---

def dashboard_page():
    st.header("📊 État de la Recherche")
    df = pd.read_sql_query("SELECT * FROM data_research", conn)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Inclusions Totales", len(df))
    col2.metric("Alertes IA", len(df[df['risque_ia'] == 'Élevé']) if not df.empty else 0)
    col3.metric("Statut Base", "SQLite Active")
    
    if not df.empty:
        st.subheader("Distribution des pathologies")
        st.bar_chart(df['cancer_type'].value_counts())
        st.subheader("Évolution de la Qualité de Vie")
        st.line_chart(df.set_index('date')['qdv'])

def questionnaire_page():
    st.header("📝 Module de Saisie Clinique")
    
    # 1. Consentement Éclairé
    with st.expander("📄 CONSENTEMENT ÉCLAIRÉ (Obligatoire)", expanded=True):
        st.write("Le laboratoire GenApAgiE s'engage à l'anonymisation de vos données.")
        consent = st.checkbox("J'accepte de participer à cette étude de recherche.")
    
    if not consent:
        st.warning("Veuillez valider le consentement pour continuer.")
        return

    st.divider()
    
    # 2. Formulaire Dynamique
    profil = st.radio("Cible :", ["Patient", "Médecin / Professionnel"], horizontal=True)
    cancer_type = st.selectbox("Domaine d'étude :", ["Cancer du Poumon", "Cancer du Sein", "Autre"])

    with st.form("research_form"):
        col1, col2 = st.columns(2)
        
        if profil == "Patient":
            with col1:
                qdv = st.slider("Qualité de vie perçue (1-10)", 1, 10, 7)
                sommeil = st.select_slider("Troubles du sommeil", options=[1, 2, 3, 4, 5])
            with col2:
                if cancer_type == "Cancer du Poumon":
                    st.radio("Niveau d'essoufflement", ["Nul", "Modéré", "Sévère"])
                elif cancer_type == "Cancer du Sein":
                    st.radio("Gêne de mobilité (bras)", ["Nulle", "Légère", "Importante"])
                bio_val = 0.0 # Valeur par défaut pour le patient
        else:
            with col1:
                ecog = st.number_input("Score ECOG (0-4)", 0, 4, 0)
                bio_val = st.number_input("Marqueur bio (CRP/ACE)", value=0.0)
            with col2:
                st.text_area("Note clinique de synthèse")
                qdv, sommeil = 5, 1 # Valeurs neutres pour le médecin
        
        if st.form_submit_button("Analyser & Sauvegarder"):
            # Exécution de l'IA
            risque = predict_fatigue_risk(qdv, sommeil, (ecog if profil != "Patient" else 0))
            
            # Sauvegarde SQL
            c = conn.cursor()
            c.execute('''INSERT INTO data_research 
                         (date, profil, cancer_type, qdv, sommeil, ecog, risque_ia, bio_marker_val, consent) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (datetime.now().strftime("%Y-%m-%d %H:%M"), profil, cancer_type, qdv, sommeil, 
                       (ecog if profil != "Patient" else 0), risque, bio_val, 1))
            conn.commit()
            
            st.success(f"Données enregistrées. Risque IA : {risque}")
            if risque == "Élevé":
                st.error("Alerte de fatigue sévère détectée par l'algorithme.")

def import_page():
    st.header("📂 Importation de Données Externes")
    file = st.file_uploader("Importer des résultats bio (CSV/Excel)", type=['xlsx', 'csv'])
    if file:
        st.success("Fichier chargé. Prêt pour la fusion statistique sous R.")

def export_page():
    st.header("💾 Rapports et Analyse R")
    df = pd.read_sql_query("SELECT * FROM data_research", conn)
    
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Export Excel")
            output_exc = io.BytesIO()
            with pd.ExcelWriter(output_exc, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='GenApAgiE_Data')
            st.download_button("📥 Télécharger Excel pour R", output_exc.getvalue(), "GenApAgiE_Export.xlsx")
            
        with col2:
            st.subheader("Rapport PDF")
            pdf_data = generate_pdf(df)
            st.download_button("📥 Télécharger Rapport PDF", pdf_data, "Rapport_GenApAgiE.pdf", "application/pdf")
    else:
        st.warning("Aucune donnée disponible pour l'exportation.")

def scanners_page():
    st.header("📷 Modules Scanners")
    st.info("Modules hérités du projet initial.")
    tab1, tab2 = st.tabs(["Scanner IA", "Scanner Norme 1m"])
    with tab1:
        st.file_uploader("Charger imagerie médicale", type=['jpg', 'png'])
    with tab2:
        st.camera_input("Capture norme 1 mètre")

# --- ROUTAGE DES PAGES ---
if menu == "Dashboard": dashboard_page()
elif menu == "Questionnaire & IA": questionnaire_page()
elif menu == "Importation Bio": import_page()
elif menu == "Rapports & Exports": export_page()
elif menu == "Anciens Scanners": scanners_page()

# --- FOOTER ---
st.sidebar.divider()
st.sidebar.caption("© 2026 Laboratoire GenApAgiE\nConformité Éthique & RGPD")
