# Générateur de boîte dans le navigateur (Boxes.py + GitHub Pages)

Cette page fait tourner le générateur **ABox** de [Boxes.py](https://github.com/florianfesti/boxes)
directement dans le navigateur, grâce à [Pyodide](https://pyodide.org) (Python compilé en WebAssembly).
GitHub Pages ne sert que des fichiers statiques : tout le calcul se fait chez le visiteur.

## Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | la page, le formulaire et le code JavaScript |
| `boxes.zip` | le code Python de Boxes (cœur + générateur ABox) |
| `LICENSE.txt` | licence GPL v3 de Boxes.py |
| `construire_zip.py` | script pour régénérer `boxes.zip` depuis le dépôt officiel |

## Mise en ligne

1. Créez un dépôt sur GitHub et déposez-y ces fichiers à la racine.
2. *Settings → Pages → Build and deployment* : source **Deploy from a branch**, branche `main`, dossier `/ (root)`.
3. Après une minute, la page est disponible sur `https://VOTRE-NOM.github.io/NOM-DU-DEPOT/`.

## Tester chez soi

Ouvrir `index.html` directement ne fonctionne pas (le navigateur bloque `fetch` en `file://`).
Lancer plutôt un petit serveur local :

```
python3 -m http.server 8000
```

puis ouvrir http://localhost:8000.

## Ajouter d'autres boîtes

Le formulaire est écrit à la main pour ABox. Pour un autre générateur :

1. ajouter son fichier dans la liste `generateurs` de `construire_zip.py` et relancer le script ;
2. dans `index.html`, adapter l'import dans `CODE_PYTHON` et les champs du formulaire.
   La liste des paramètres d'un générateur s'obtient avec `python3 -c "from boxes.generators.xxx import Xxx; b=Xxx(); print([a.dest for a in b.argparser._actions])"`.

## Remarques

- Le premier chargement est long (Pyodide, shapely, numpy), les suivants sont rapides grâce au cache.
- `qrcode` est installé depuis PyPI au chargement (`micropip`), donc une connexion internet est nécessaire.
- La version de Pyodide est fixée dans `index.html` (`v314.0.8`). Pour la mettre à jour, changer l'adresse du script.
- Licence : Boxes.py est sous GPL v3. Ce dépôt doit donc rester sous GPL v3 et conserver la mention de l'auteur.
