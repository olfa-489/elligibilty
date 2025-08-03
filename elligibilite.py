import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime
import sqlite3
import plotly.io as pio

# NLP
from sentence_transformers import SentenceTransformer, util
import numpy as np

# Graphiques
import plotly.express as px

# PDF
from fpdf import FPDF
import plotly.io as pio

# Optional: For encoding detection
import chardet

# ==================== CONFIG STREAMLIT ====================
st.set_page_config(page_title="📡 Vérification Éligibilité FTTH ", layout="wide")

st.title("📡 Vérification automatique d'éligibilité FTTH- Orange")

# ==================== DB SQLITE ====================
def init_db():
    conn = sqlite3.connect("historique_eligibilite.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS historique (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adresse_saisie TEXT,
        adresse_corrigee TEXT,
        statut TEXT,
        date_verif TEXT
    )
    """)
    conn.commit()
    conn.close()

def sauvegarder_resultats(df):
    conn = sqlite3.connect("historique_eligibilite.db")
    for _, row in df.iterrows():
        conn.execute("INSERT INTO historique (adresse_saisie, adresse_corrigee, statut, date_verif) VALUES (?, ?, ?, ?)", 
                     (row['Adresse saisie'], row['Adresse corrigée'], row['Statut éligibilité'], datetime.now().isoformat()))
    conn.commit()
    conn.close()

def charger_historique():
    conn = sqlite3.connect("historique_eligibilite.db")
    df_hist = pd.read_sql_query("SELECT * FROM historique ORDER BY date_verif DESC LIMIT 100", conn)
    conn.close()
    return df_hist

# Init DB
init_db()

# ==================== BASE ADRESSES DE RÉFÉRENCE ====================
BASE_ADRESSES = [
    "12 Rue de la République, Paris",
    "5 Avenue des Champs-Élysées, Paris",
    "8 Rue Victor Hugo, Lyon",
    "10 Boulevard Saint-Germain, Paris",
    "3 Rue Nationale, Lille"
]

# ==================== IA NLP POUR CORRECTION ====================
st.sidebar.write("⏳ Chargement du modèle NLP...")
modele_bert = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
embeddings_base = modele_bert.encode(BASE_ADRESSES)

def corriger_adresse_ia(adresse):
    emb_adresse = modele_bert.encode([adresse])[0]
    scores = util.cos_sim(emb_adresse, embeddings_base)[0].cpu().numpy()
    best_idx = np.argmax(scores)
    best_score = scores[best_idx]
    if best_score > 0.75:
        return BASE_ADRESSES[best_idx], best_score
    else:
        return adresse, best_score

# ==================== SELENIUM POUR ORANGE ====================
def verifier_liste_eligibilite_orange(liste_adresses):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 12)
    results = []
    
    try:
        driver.get("https://boutique.orange.fr/internet/eligibilite")
        time.sleep(3)
        
        # Accepter cookies si présent
        try:
            btn_cookie = wait.until(EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button")))
            btn_cookie.click()
            time.sleep(1)
        except:
            pass
        
        # Vérification en boucle
        for adresse in liste_adresses:
            try:
                champ = wait.until(EC.presence_of_element_located((By.NAME, "elig_address")))
                champ.clear()
                champ.send_keys(adresse)
                time.sleep(1)
                champ.send_keys(Keys.RETURN)
                
                resultat_elem = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.eligibility-result"))
                )
                texte_resultat = resultat_elem.text.strip()
                
                results.append((adresse, texte_resultat))
                
                # Retour page accueil
                driver.get("https://boutique.orange.fr/internet/eligibilite")
                time.sleep(2)
            
            except Exception as e:
                print(f"Erreur pour {adresse} :", e)
                results.append((adresse, "❌ Impossible de vérifier"))
                driver.get("https://boutique.orange.fr/internet/eligibilite")
                time.sleep(2)
        
        return results
    
    finally:
        driver.quit()

# ==================== ANALYSE DES RÉSULTATS ====================
def analyser_resultats(df):
    df['Éligible ?'] = df['Statut éligibilité'].apply(
        lambda x: "Éligible" if "éligible" in x.lower() else "Non éligible"
    )
    stats = df['Éligible ?'].value_counts().reset_index()
    stats.columns = ["Statut", "Nombre"]
    
    fig = px.pie(stats, values='Nombre', names='Statut', 
                 color='Statut',
                 color_discrete_map={"Éligible":"green", "Non éligible":"red"},
                 title="Répartition des adresses éligibles / non éligibles")
    return df, stats, fig

# ==================== EXPORT PDF PRO ====================
import tempfile, os
pio.kaleido.scope.default_format = "png"


def exporter_pdf(df, fig_pie, nom_pdf="rapport_eligibilite.pdf", auteur="Entreprise XYZ", logo_path="logo_orange.png"):
    temp_dir = tempfile.mkdtemp()
    graph_path = os.path.join(temp_dir, "graph.png")

    # ✅ Essayer de sauver le graphique
    try:
        fig_pie.write_image(graph_path, format="png")
    except Exception as e:
        print("Erreur en sauvegardant le graphique :", e)
        graph_path = None
    
    total = len(df)
    nb_eligibles = len(df[df['Éligible ?']=="Éligible"])
    nb_non = total - nb_eligibles
    date_rapport = datetime.now().strftime("%d/%m/%Y %H:%M")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ✅ PAGE 1
    pdf.add_page()

    # ✅ Logo (si disponible)
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 15, "Rapport d'éligibilité FTTH/FTTO", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, f"Généré par : {auteur}", ln=True, align="R")
    pdf.cell(0, 10, f"Date du rapport : {date_rapport}", ln=True, align="R")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, f"""
✅ Nombre total d'adresses vérifiées : {total}
✅ Nombre d'adresses éligibles : {nb_eligibles}
❌ Nombre d'adresses non éligibles : {nb_non}
""")

    pdf.ln(10)
    if graph_path:
        pdf.cell(0, 10, "Graphique de répartition :", ln=True)
        pdf.image(graph_path, x=30, w=150)
    else:
        pdf.cell(0, 10, "⚠️ Graphique non disponible (problème de génération).", ln=True)

    # ✅ PAGE 2 (détails)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Détail des résultats", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(60, 8, "Adresse saisie", 1)
    pdf.cell(60, 8, "Adresse corrigée", 1)
    pdf.cell(70, 8, "Statut", 1)
    pdf.ln(8)

    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        pdf.cell(60, 8, row['Adresse saisie'][:35], 1)
        pdf.cell(60, 8, row['Adresse corrigée'][:35], 1)
        pdf.cell(70, 8, row['Statut éligibilité'][:40], 1)
        pdf.ln(8)

    pdf.output(nom_pdf)
    return nom_pdf


# ==================== CHATBOT GUIDE ====================
import random

# Base de réponses prédéfinies
faq_reponses = {
    "bonjour": "👋 Bonjour ! Je suis votre guide pour l'outil d'éligibilité FTTH/FTTO. Comment puis-je vous aider ?",
    "comment ça marche": "👉 Cet outil corrige vos adresses avec une IA NLP, vérifie l’éligibilité via Orange, et vous donne un rapport (Excel/PDF).",
    "importer": "📂 Vous pouvez importer un fichier CSV ou Excel contenant une colonne 'adresse'.",
    "historique": "📜 L’onglet Historique affiche les 100 dernières vérifications enregistrées dans la base SQLite.",
    "pdf": "📄 Après vérification, vous pouvez générer un rapport PDF professionnel avec logo, auteur et date.",
    "excel": "📊 Oui, vous pouvez exporter les résultats au format Excel.",
    "aide": "✅ Vous pouvez me demander :\n- Comment corriger une adresse\n- Comment importer un fichier\n- Comment générer un PDF\n- Comment voir l’historique"
}

def repondre_chatbot(message):
    msg = message.lower()
    for cle, rep in faq_reponses.items():
        if cle in msg:
            return rep
    # Réponse par défaut
    return random.choice([
        "🤔 Je ne suis pas sûr… Essayez 'aide' pour voir ce que je peux faire.",
        "💡 Tapez 'aide' pour la liste des commandes.",
        "Pouvez-vous préciser votre question ? Tapez 'aide' si besoin."
    ])

# ==================== INTERFACE CHATBOT ====================
def afficher_chatbot():
    st.subheader("🤖 Chatbot Guide")

    # Historique en session
    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = [
            {"role": "bot", "text": "👋 Bonjour ! Je suis votre guide. Tapez 'aide' pour voir ce que je peux faire."}
        ]

    # ✅ Afficher l’historique
    for msg in st.session_state.chatbot_messages:
        if msg["role"] == "bot":
            st.markdown(f"**🤖 Bot:** {msg['text']}")
        else:
            st.markdown(f"**🧑 Vous:** {msg['text']}")

    # ✅ Champ de saisie utilisateur
    user_msg = st.text_input("💬 Posez une question au guide :", key="chatbot_input")

    if st.button("Envoyer", key="chatbot_send"):
        if user_msg.strip():
            # Ajout du message utilisateur
            st.session_state.chatbot_messages.append({"role": "user", "text": user_msg})

            # Réponse automatique
            bot_reply = repondre_chatbot(user_msg)
            st.session_state.chatbot_messages.append({"role": "bot", "text": bot_reply})

            # ✅ PAS besoin de rerun → Streamlit va réafficher tout seul
            # Si tu veux forcer un rafraîchissement, mets ça :
            # try:
            #     st.rerun()
            # except:
            #     st.experimental_rerun()


# ==================== INTERFACE STREAMLIT ====================
menu = st.sidebar.radio("Navigation", ["Vérification", "Historique", "Guide Chatbot"])

if menu == "Vérification":
    mode = st.radio("Mode d'entrée", ["Saisie manuelle", "Import CSV/Excel"])
    
    if mode == "Saisie manuelle":
        adresses_input = st.text_area("Entrez les adresses (une par ligne)")
        if st.button("Vérifier"):
            if adresses_input.strip() == "":
                st.warning("Veuillez entrer au moins une adresse.")
            else:
                liste_adresses = [adr.strip() for adr in adresses_input.split("\n") if adr.strip()]
                
                # ✅ Correction IA NLP
                adresses_corrigees = []
                for adr in liste_adresses:
                    adr_corrigee, score = corriger_adresse_ia(adr)
                    adresses_corrigees.append(adr_corrigee)
                
                # ✅ Vérification Selenium
                resultats_selenium = verifier_liste_eligibilite_orange(adresses_corrigees)
                
                # Fusion
                final_results = []
                for i, (adr_corr, res) in enumerate(resultats_selenium):
                    final_results.append([liste_adresses[i], adr_corr, res])
                
                df_resultats = pd.DataFrame(final_results, columns=["Adresse saisie", "Adresse corrigée", "Statut éligibilité"])
                st.dataframe(df_resultats)
                
                # ✅ Analyse Dashboard
                df_resultats, stats, fig_pie = analyser_resultats(df_resultats)
                
                st.subheader("📊 Dashboard Éligibilité")
                st.write(f"**Total d’adresses vérifiées : {len(df_resultats)}**")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("### Statistiques")
                    st.dataframe(stats)
                with col2:
                    st.write("### Graphique de répartition")
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                # ✅ Sauvegarde DB
                sauvegarder_resultats(df_resultats)
                
                # ✅ Export Excel
                df_resultats.to_excel("resultats_eligibilite.xlsx", index=False)
                with open("resultats_eligibilite.xlsx", "rb") as f:
                    st.download_button("⬇️ Télécharger les résultats Excel", f, "eligibilite.xlsx")
                
                # ✅ Export PDF
                if st.button("📄 Générer un rapport PDF professionnel"):
                    pdf_file = exporter_pdf(df_resultats, fig_pie, auteur="Ton Entreprise", logo_path="logo_orange.png")
                    with open(pdf_file, "rb") as f:
                        st.download_button("⬇️ Télécharger le rapport PDF", f, "rapport_eligibilite.pdf", mime="application/pdf")

    else:
        fichier = st.file_uploader("Chargez un fichier CSV/Excel contenant une colonne 'adresse'")
        if fichier:
            try:
                df = pd.read_excel(fichier) if fichier.name.endswith("xlsx") else pd.read_csv(fichier, encoding='ISO-8859-1')
                st.write("Aperçu du fichier :", df.head())
                
                if 'adresse' not in df.columns:
                    st.error("Le fichier doit contenir une colonne nommée 'adresse'")
                else:
                    if st.button("Vérifier"):
                        liste_adresses = df['adresse'].dropna().tolist()
                        
                        # Correction IA
                        adresses_corrigees = [corriger_adresse_ia(adr)[0] for adr in liste_adresses]
                        
                        # Vérif Selenium
                        resultats_selenium = verifier_liste_eligibilite_orange(adresses_corrigees)
                        
                        # Fusion
                        final_results = []
                        for i, (adr_corr, res) in enumerate(resultats_selenium):
                            final_results.append([liste_adresses[i], adr_corr, res])
                        
                        df_resultats = pd.DataFrame(final_results, columns=["Adresse saisie", "Adresse corrigée", "Statut éligibilité"])
                        st.dataframe(df_resultats)
                        
                        # Dashboard
                        df_resultats, stats, fig_pie = analyser_resultats(df_resultats)
                        
                        st.subheader("📊 Dashboard Éligibilité")
                        st.plotly_chart(fig_pie)
                        
                        sauvegarder_resultats(df_resultats)
                        
                        df_resultats.to_excel("resultats_eligibilite.xlsx", index=False)
                        with open("resultats_eligibilite.xlsx", "rb") as f:
                            st.download_button("⬇️ Télécharger les résultats Excel", f, "eligibilite.xlsx")
            except UnicodeDecodeError:
                st.error("Erreur de lecture du fichier CSV. Le fichier contient des caractères non compatibles avec UTF-8. Essayez un encodage comme 'Windows-1252' ou vérifiez le fichier.")
                # Optional: Uncomment the following to enable encoding detection with chardet
                """
                fichier.seek(0)  # Reset file pointer
                raw_data = fichier.read()
                encoding = chardet.detect(raw_data)['encoding']
                fichier.seek(0)  # Reset file pointer again
                try:
                    df = pd.read_csv(fichier, encoding=encoding)
                    st.write(f"Encodage détecté : {encoding}")
                    st.write("Aperçu du fichier :", df.head())
                except Exception as e:
                    st.error(f"Erreur lors de la lecture avec l'encodage détecté ({encoding}) : {str(e)}")
                """

elif menu == "Historique":
    st.subheader("📜 Historique des vérifications")
    df_hist = charger_historique()
    st.dataframe(df_hist)

elif menu == "Guide Chatbot":
    afficher_chatbot()

