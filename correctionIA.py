from sentence_transformers import SentenceTransformer, util
import numpy as np

# Charger un modèle NLP multilingue léger
modele_bert = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Base interne d’adresses de référence
BASE_ADRESSES = [
    "12 Rue de la République, Paris",
    "5 Avenue des Champs-Élysées, Paris",
    "8 Rue Victor Hugo, Lyon",
    "10 Boulevard Saint-Germain, Paris",
    "3 Rue Nationale, Lille"
]

# Encoder une seule fois les adresses de référence
embeddings_base = modele_bert.encode(BASE_ADRESSES)

def corriger_adresse_ia(adresse):
    """
    Corrige une adresse en cherchant la correspondance la plus proche dans la base via BERT.
    """
    # Encoder l’adresse saisie
    emb_adresse = modele_bert.encode([adresse])[0]
    
    # Calculer la similarité cosinus avec toutes les adresses de référence
    scores = util.cos_sim(emb_adresse, embeddings_base)[0].cpu().numpy()
    
    best_idx = np.argmax(scores)
    best_score = scores[best_idx]
    
    if best_score > 0.75:  # Seuil de confiance
        return BASE_ADRESSES[best_idx], best_score
    else:
        return adresse, best_score
