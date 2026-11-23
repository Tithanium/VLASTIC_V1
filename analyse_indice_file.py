import os
import tkinter as tk
from tkinter import filedialog


def selectionner_dossier():
    root = tk.Tk()
    dossier_defaut = r"C:\Users\connessn\Datas\02_RECHERCHE\03_suction\06_tests\Plaques_silicone\HCERES"
    root.withdraw()
    dossier = filedialog.askdirectory(
        title="Sélectionner un dossier à analyser",
        initialdir=dossier_defaut if os.path.exists(dossier_defaut) else os.path.expanduser("~"),
    )
    return dossier


def condenser_lignes(numeros):
    """Convertit une liste de numéros en chaîne avec plages condensées.
    Ex : [42, 56, 57, 58, 59, 10300] -> '42 56-59 10300'
    """
    if not numeros:
        return ""

    numeros = sorted(set(numeros))
    groupes = []
    debut = numeros[0]
    fin = numeros[0]

    for n in numeros[1:]:
        if n == fin + 1:
            fin = n
        else:
            groupes.append(str(debut) if debut == fin else f"{debut}-{fin}")
            debut = n
            fin = n

    groupes.append(str(debut) if debut == fin else f"{debut}-{fin}")

    return " ".join(groupes)


def analyser_fichier(chemin_fichier):
    """Retourne la liste des numéros de lignes présentant une anomalie."""
    lignes_anomalies = []

    with open(chemin_fichier, 'r', encoding='utf-8') as f:
        lignes = f.readlines()

    index_precedent = None
    numero_ligne_fichier = 0

    for ligne in lignes:
        numero_ligne_fichier += 1
        ligne = ligne.strip()

        if not ligne:
            continue

        colonnes = ligne.split(';')
        try:
            index_actuel = int(colonnes[0])
        except (ValueError, IndexError):
            lignes_anomalies.append(numero_ligne_fichier)
            index_precedent = None
            continue

        if index_precedent is not None:
            increment_attendu = (index_precedent + 1) % 256
            if index_actuel != increment_attendu:
                lignes_anomalies.append(numero_ligne_fichier)

        index_precedent = index_actuel

    return lignes_anomalies


def collecter_fichiers_txt(dossier_racine, fichier_bilan):
    """Parcourt récursivement le dossier et retourne tous les chemins de fichiers .txt,
    en excluant le fichier bilan lui-même."""
    fichiers_txt = []
    for dossier_courant, sous_dossiers, fichiers in os.walk(dossier_racine):
        for fichier in fichiers:
            if fichier.lower().endswith('.txt'):
                chemin_complet = os.path.join(dossier_courant, fichier)
                if os.path.abspath(chemin_complet) != os.path.abspath(fichier_bilan):
                    fichiers_txt.append(chemin_complet)
    return fichiers_txt


def main():
    print("=== Analyse d'incréments de fichiers .txt (récursif) ===\n")

    dossier = selectionner_dossier()

    if not dossier:
        print("Aucun dossier sélectionné. Programme terminé.")
        return

    print(f"Dossier sélectionné : {dossier}\n")

    chemin_bilan = os.path.join(dossier, "bilan_anomalies.txt")
    fichiers = collecter_fichiers_txt(dossier, chemin_bilan)

    if not fichiers:
        print("Aucun fichier .txt trouvé dans ce dossier.")
        return

    print(f"{len(fichiers)} fichier(s) .txt trouvé(s). Analyse en cours...\n")

    lignes_bilan = []
    total_anomalies = 0
    fichiers_avec_anomalies = 0

    for chemin in fichiers:
        try:
            lignes_anomalies = analyser_fichier(chemin)
        except Exception as e:
            print(f"❌ Erreur lecture : {chemin} -> {e}")
            continue

        if lignes_anomalies:
            fichiers_avec_anomalies += 1
            total_anomalies += len(lignes_anomalies)
            condensed = condenser_lignes(lignes_anomalies)
            ligne_bilan = f"{chemin} [{condensed}]"
            lignes_bilan.append(ligne_bilan)
            print(ligne_bilan)

    # Écriture du fichier bilan
    with open(chemin_bilan, 'w', encoding='utf-8') as f:
        f.write("\n".join(lignes_bilan))
        f.write("\n")

    # Résumé console
    print(f"\n{'=' * 70}")
    print(f"Fichiers analysés         : {len(fichiers)}")
    print(f"Fichiers avec anomalie(s) : {fichiers_avec_anomalies}")
    print(f"Total anomalies           : {total_anomalies}")
    print(f"Bilan sauvegardé dans     : {chemin_bilan}")
    print("Analyse terminée.")


if __name__ == "__main__":
    main()