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
