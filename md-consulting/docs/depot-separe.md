# Sortir ce projet du dépôt du site

Ce dossier vit aujourd'hui dans `nouveausiterbi`, le dépôt du site Rite Brith
Israël, qui est **publié sur Internet**. Un outil qui traite des données de
mineurs n'a rien à y faire. Ces instructions le déménagent sans rien perdre.

## Pourquoi ce n'est pas déjà fait

L'intégration GitHub de cette session n'a pas le droit de créer un dépôt
(`403 Resource not accessible by integration`). La création se fait donc à la
main — le reste est préparé.

**Choix du compte.** Le seul compte GitHub accessible ici est
`contactbrithisrael-tech`, celui de l'association. Ce projet appartient à
MD Consulting, pas au Rite. Créer le dépôt sous un compte MD Consulting évite
qu'un outil professionnel dépende plus tard des accès d'une association.

## Les commandes

Le fichier `md-consulting.bundle` contient **tout l'historique** du projet,
les fichiers déjà à la racine.

```bash
# 1. Sur GitHub : créer un dépôt vide et PRIVÉ, sans README,
#    par exemple « md-consulting-orientation ».

# 2. Reconstituer le dépôt depuis le paquet :
git clone md-consulting.bundle md-consulting
cd md-consulting

# 3. Le faire pointer vers le nouveau dépôt :
git remote set-url origin https://github.com/<compte>/md-consulting-orientation.git

# 4. Envoyer :
git push -u origin main
```

Vérifier ensuite que tout fonctionne dans le nouveau dépôt :

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./lancer_tests.sh      # 62 tests
streamlit run app.py
```

Le paquet a été vérifié : cloné à neuf, les 62 tests passent.

## Ensuite

Une fois le nouveau dépôt en place, le dossier `md-consulting/` et la règle
`/md-consulting/*` de `_redirects` doivent disparaître de `nouveausiterbi`.
Tant que ce n'est pas fait, le code reste dans un dépôt publié — l'historique
Git le conserve de toute façon, la suppression ne perd rien.

## Le dépôt privé n'est pas une option

Un dépôt public exposerait le code, pas les données (`*.db` et `exports/` sont
exclus par `.gitignore`). Mais la moindre erreur de manipulation y deviendrait
définitive et publique. **Privé.**
