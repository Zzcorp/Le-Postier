# core/imaging.py
"""Traitement des images de signature : encre pure sur fond transparent.

Pipeline partagé par la vue upload_signature et la commande
process_signatures — toute signature stockée passe par ici et devient
un PNG RGBA (600px max) dont le fond blanc/quasi blanc est transparent.
"""
from io import BytesIO

from PIL import Image, ImageChops, ImageOps

# Dimension maximale (largeur ou hauteur) après redimensionnement LANCZOS.
SIGNATURE_MAX_DIM = 600
# min(R,G,B) >= WHITE_CUTOFF  -> alpha 0 (blanc pur / quasi blanc)
WHITE_CUTOFF = 238
# Entre RAMP_START et WHITE_CUTOFF : rampe douce 255 -> 0.
RAMP_START = 200
# Bruit JPEG clair : tout alpha < NOISE_ALPHA_FLOOR est ramené à 0.
NOISE_ALPHA_FLOOR = 20


def _build_alpha_lut():
    """LUT 256 entrées : min(R,G,B) -> alpha (rampe douce vers le blanc)."""
    span = WHITE_CUTOFF - RAMP_START
    lut = []
    for value in range(256):
        if value >= WHITE_CUTOFF:
            lut.append(0)
        elif value <= RAMP_START:
            lut.append(255)
        else:
            lut.append(round(255 * (WHITE_CUTOFF - value) / span))
    return lut


_ALPHA_LUT = _build_alpha_lut()


def process_signature_image(source):
    """Transforme une image de signature en PNG à fond transparent.

    source : objet fichier (uploaded file, BytesIO, fichier ouvert en 'rb').
    Retourne les octets PNG (RGBA, encre seule, aucun cadre blanc).
    Lève une exception Pillow si le fichier n'est pas une image lisible.
    """
    img = Image.open(source)
    img = ImageOps.exif_transpose(img)
    img = img.convert('RGBA')

    if max(img.size) > SIGNATURE_MAX_DIM:
        img.thumbnail((SIGNATURE_MAX_DIM, SIGNATURE_MAX_DIM), Image.Resampling.LANCZOS)

    r, g, b, a = img.split()
    darkest = ImageChops.darker(ImageChops.darker(r, g), b)  # min(R,G,B) par pixel
    computed = darkest.point(_ALPHA_LUT)
    # Respecte une transparence déjà présente dans la source (PNG/GIF).
    alpha = ImageChops.multiply(a, computed)
    alpha = alpha.point(lambda v: 0 if v < NOISE_ALPHA_FLOOR else v)
    img.putalpha(alpha)

    buffer = BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()
