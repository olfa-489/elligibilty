def verifier_liste_eligibilite_orange(liste_adresses):
    """
    Vérifie plusieurs adresses d'un coup en réutilisant UNE seule session Selenium.
    Retourne une liste [(adresse, resultat), ...]
    """
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    # Options Chrome headless (sans interface)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    
    results = []
    
    try:
        # Ouvre la page une seule fois
        driver.get("https://boutique.orange.fr/internet/eligibilite")
        time.sleep(3)
        
        # Accepter les cookies si présent
        try:
            btn_cookie = wait.until(EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button")))
            btn_cookie.click()
            time.sleep(1)
        except:
            pass
        
        # Boucle sur toutes les adresses
        for adresse in liste_adresses:
            try:
                # Trouver le champ adresse
                champ = wait.until(EC.presence_of_element_located((By.NAME, "elig_address")))
                champ.clear()
                champ.send_keys(adresse)
                time.sleep(1)
                champ.send_keys(Keys.RETURN)
                
                # Attendre le résultat
                resultat_elem = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.eligibility-result"))
                )
                texte_resultat = resultat_elem.text.strip()
                
                results.append((adresse, texte_resultat))
                
                # Retour à la page d'accueil pour saisir une nouvelle adresse
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
