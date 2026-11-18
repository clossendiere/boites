#!/usr/bin/env python3
"""Reconstruit boxes.zip à partir d'une copie du dépôt florianfesti/boxes.

Usage :
    git clone --depth 1 https://github.com/florianfesti/boxes.git
    python3 construire_zip.py boxes

Sont inclus : le cœur de Boxes, le générateur ABox et, depuis le dossier
« ajouts » situé à côté de ce script, le générateur Photophore et le module
svgimport (lecture des dessins SVG).
(svgmerge.py est exclu : il demande rectpack et svgpathtools.)
"""
import os
import sys
import zipfile

ici = os.path.dirname(os.path.abspath(__file__))
depot = sys.argv[1] if len(sys.argv) > 1 else "boxes"
racine = os.path.join(depot, "boxes")
ajouts = os.path.join(ici, "ajouts")

generateurs = ["__init__.py", "abox.py"]       # ABox et son module d'enregistrement
modules_ajoutes = {                             # fichier de « ajouts » -> chemin dans le zip
    "svgimport.py": "boxes/svgimport.py",
    "photophore.py": "boxes/generators/photophore.py",
}

with zipfile.ZipFile(os.path.join(ici, "boxes.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(racine)):
        if f.endswith(".py") and f != "svgmerge.py" and f not in modules_ajoutes:
            z.write(os.path.join(racine, f), "boxes/" + f)
    for f in generateurs:
        z.write(os.path.join(racine, "generators", f), "boxes/generators/" + f)
    for source, cible in modules_ajoutes.items():
        z.write(os.path.join(ajouts, source), cible)

print("boxes.zip :", os.path.getsize(os.path.join(ici, "boxes.zip")) // 1024, "Ko")
