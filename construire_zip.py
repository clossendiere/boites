#!/usr/bin/env python3
"""Reconstruit boxes.zip à partir d'une copie du dépôt florianfesti/boxes.

Usage :
    git clone --depth 1 https://github.com/florianfesti/boxes.git
    python3 construire_zip.py boxes

Seuls le cœur de Boxes et le générateur ABox sont inclus, pour que
le téléchargement dans le navigateur reste léger.
(svgmerge.py est exclu : il demande rectpack et svgpathtools.)
"""
import os
import sys
import zipfile

depot = sys.argv[1] if len(sys.argv) > 1 else "boxes"
racine = os.path.join(depot, "boxes")
generateurs = ["__init__.py", "abox.py"]  # ajouter ici d'autres boîtes

with zipfile.ZipFile("boxes.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(racine)):
        if f.endswith(".py") and f != "svgmerge.py":
            z.write(os.path.join(racine, f), "boxes/" + f)
    for f in generateurs:
        z.write(os.path.join(racine, "generators", f), "boxes/generators/" + f)

print("boxes.zip :", os.path.getsize("boxes.zip") // 1024, "Ko")
