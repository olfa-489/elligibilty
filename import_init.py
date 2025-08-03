import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime
import sqlite3

# NLP
from sentence_transformers import SentenceTransformer, util
import numpy as np

# Graphiques
import plotly.express as px

# PDF
from fpdf import FPDF
import plotly.io as pio

# ==================== CONFIG STREAMLIT ====================
st.set_page_config(page_title="📡 Vérification Éligibilité FTTH/FTTO", layout="wide")

st.title("📡 Vérification automatique d'éligibilité FTTH/FTTO - Orange")

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
