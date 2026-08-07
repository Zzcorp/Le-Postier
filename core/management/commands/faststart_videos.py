# core/management/commands/faststart_videos.py
"""
Rend chaque MP4 de MEDIA_ROOT/animated_cp diffusable progressivement
(« faststart ») en déplaçant l'atome moov avant mdat — sans ré-encodage
et sans dépendance externe (algorithme qtfaststart en Python pur).

Principe : un lecteur ne peut commencer la lecture d'un MP4 en streaming
que lorsqu'il a reçu l'atome moov (l'index). Si le moov est stocké après
le mdat (les données), tout le fichier doit être téléchargé avant le
premier photogramme. La relocalisation réécrit le fichier comme
ftyp + moov corrigé + atomes restants, en ajustant chaque entrée des
tables d'offsets de chunks (stco 32 bits / co64 64 bits) du delta induit
par le déplacement. Les octets du mdat ne sont jamais modifiés.

Garde-fous :
    - moov compressé (cmov) : fichier ignoré avec avertissement (le
      décompresser serait risqué, on ne corrompt jamais).
    - Écriture dans un fichier temporaire du même dossier, puis
      os.replace atomique UNIQUEMENT après re-vérification complète du
      temporaire (moov avant mdat, tailles d'atomes couvrant exactement
      le fichier, taille identique à l'original).
    - Toute erreur d'analyse laisse l'original intact et compte comme
      erreur ; la commande ne s'interrompt jamais en cours de lot.
    - Les .webm sont ignorés silencieusement (streaming progressif natif).

Usage :
    manage.py faststart_videos                    # relocalise tout animated_cp
    manage.py faststart_videos --dry-run          # rapport seul, aucune écriture
    manage.py faststart_videos --backup-dir /bk   # copie les originaux avant
"""

import os
import shutil
import struct
import tempfile
from pathlib import Path
from typing import NamedTuple

from django.conf import settings
from django.core.management.base import BaseCommand

CHUNK_SIZE = 1024 * 1024
UINT32_MAX = 0xFFFFFFFF
MO = 1024 * 1024
TOP_HEADER = struct.Struct('>I4s')

# Conteneurs à traverser dans moov pour atteindre stbl/stco (les tables
# d'offsets ne vivent légitimement que sous trak > mdia > minf > stbl).
MOOV_CONTAINERS = {b'trak', b'mdia', b'minf', b'stbl'}

STATUS_FASTSTART = 'faststart'      # moov déjà avant mdat
STATUS_NEEDS_MOVE = 'needs_move'    # moov après mdat : à relocaliser
STATUS_NOT_MP4 = 'not_mp4'          # inanalysable / pas un MP4 valide
STATUS_CMOV = 'cmov'                # moov compressé : ignoré


class Mp4ParseError(Exception):
    """Fichier illisible en tant que MP4 — l'original ne doit pas être modifié."""


class CompressedMoovError(Exception):
    """Atome moov compressé (cmov) — relocalisation refusée."""


class Atom(NamedTuple):
    type: str          # 4 caractères ASCII ('ftyp', 'moov', 'mdat', …)
    start: int         # offset absolu du début de l'atome
    size: int          # taille totale, en-tête compris
    header_size: int   # 8, ou 16 si taille 64 bits (size == 1)

    @property
    def end(self):
        return self.start + self.size


# ---------------------------------------------------------------------------
# Analyse des atomes de premier niveau
# ---------------------------------------------------------------------------

def _read_top_header(f, file_size):
    """Lit un en-tête d'atome à la position courante. None en fin de fichier."""
    start = f.tell()
    head = f.read(8)
    if not head:
        return None
    if len(head) < 8:
        raise Mp4ParseError(f"en-tête d'atome tronqué à l'offset {start}")
    size, raw_type = TOP_HEADER.unpack(head)
    header_size = 8
    if size == 1:  # taille 64 bits dans les 8 octets suivants
        ext = f.read(8)
        if len(ext) < 8:
            raise Mp4ParseError(f"taille 64 bits tronquée à l'offset {start}")
        (size,) = struct.unpack('>Q', ext)
        header_size = 16
    elif size == 0:  # l'atome s'étend jusqu'à la fin du fichier
        size = file_size - start
    if size < header_size:
        raise Mp4ParseError(f"taille d'atome invalide ({size}) à l'offset {start}")
    if any(b < 32 or b > 126 for b in raw_type):
        raise Mp4ParseError(f"type d'atome illisible à l'offset {start}")
    return Atom(raw_type.decode('ascii'), start, size, header_size)


def parse_top_level_atoms(f, file_size):
    """Retourne les atomes de premier niveau, contigus de 0 à file_size.

    Lève Mp4ParseError si un atome déborde ou si la somme des tailles ne
    couvre pas exactement le fichier (garantie anti-corruption).
    """
    atoms = []
    f.seek(0)
    while f.tell() < file_size:
        atom = _read_top_header(f, file_size)
        if atom is None:
            raise Mp4ParseError('fin de fichier inattendue')
        if atom.end > file_size:
            raise Mp4ParseError(f"l'atome {atom.type} dépasse la fin du fichier")
        atoms.append(atom)
        f.seek(atom.end)
    if not atoms:
        raise Mp4ParseError('aucun atome trouvé (fichier vide ?)')
    if atoms[-1].end != file_size:
        raise Mp4ParseError('les tailles des atomes ne couvrent pas le fichier')
    return atoms


# ---------------------------------------------------------------------------
# Analyse interne du moov : tables stco/co64, détection cmov
# ---------------------------------------------------------------------------

def find_chunk_tables(moov_buf, start, end, tables):
    """Parcourt récursivement les enfants du moov entre start et end.

    Alimente ``tables`` avec (type, offset_des_entrées, nombre_d_entrées)
    pour chaque stco/co64 rencontré. Lève CompressedMoovError sur cmov et
    Mp4ParseError sur toute incohérence structurelle.
    """
    pos = start
    while pos < end:
        if end - pos < 8:
            raise Mp4ParseError('atome enfant tronqué dans moov')
        size, raw_type = TOP_HEADER.unpack_from(moov_buf, pos)
        header_size = 8
        if size == 1:
            if end - pos < 16:
                raise Mp4ParseError('taille 64 bits tronquée dans moov')
            (size,) = struct.unpack_from('>Q', moov_buf, pos + 8)
            header_size = 16
        elif size == 0:
            size = end - pos
        if size < header_size or pos + size > end:
            raise Mp4ParseError(
                f'taille invalide dans moov (offset relatif {pos})')
        if raw_type == b'cmov':
            raise CompressedMoovError('moov compressé (cmov)')
        if raw_type in (b'stco', b'co64'):
            payload = pos + header_size
            if size - header_size < 8:
                raise Mp4ParseError('table stco/co64 tronquée')
            (count,) = struct.unpack_from('>I', moov_buf, payload + 4)
            entry_size = 4 if raw_type == b'stco' else 8
            if 8 + count * entry_size > size - header_size:
                raise Mp4ParseError(
                    'table stco/co64 incohérente (plus d\'entrées que d\'octets)')
            tables.append((raw_type, payload + 8, count))
        elif raw_type in MOOV_CONTAINERS:
            find_chunk_tables(moov_buf, pos + header_size, pos + size, tables)
        pos += size


def patch_chunk_tables(moov_buf, tables, insertion_point, moov_start,
                       moov_end, delta):
    """Ajuste sur place chaque offset de chunk touché par le déplacement.

    Seuls les octets situés entre le point d'insertion (fin du ftyp) et le
    début du moov d'origine reculent de ``delta`` ; ce qui précède le ftyp
    ou suit le moov d'origine ne bouge pas. Retourne le nombre d'entrées
    modifiées.
    """
    patched = 0
    for kind, entries_offset, count in tables:
        fmt, entry_size = ('>I', 4) if kind == b'stco' else ('>Q', 8)
        pos = entries_offset
        for _ in range(count):
            (value,) = struct.unpack_from(fmt, moov_buf, pos)
            if insertion_point <= value < moov_start:
                value += delta
                if kind == b'stco' and value > UINT32_MAX:
                    raise Mp4ParseError(
                        'offset stco > 32 bits après décalage — '
                        'conversion co64 nécessaire, fichier ignoré')
                struct.pack_into(fmt, moov_buf, pos, value)
                patched += 1
            elif moov_start <= value < moov_end:
                raise Mp4ParseError(
                    'offset de chunk pointant dans le moov — fichier suspect')
            pos += entry_size
    return patched


# ---------------------------------------------------------------------------
# Auto-contrôle : utilisé par --dry-run ET par la vérification post-écriture
# ---------------------------------------------------------------------------

def inspect_mp4(path):
    """Classifie un fichier : (statut, atomes, taille_fichier).

    Vérifie que les atomes de premier niveau couvrent exactement le
    fichier, que le moov est unique et structurellement sain (tables
    stco/co64 cohérentes), et détecte les moov compressés.
    """
    path = Path(path)
    file_size = path.stat().st_size
    try:
        with open(path, 'rb') as f:
            atoms = parse_top_level_atoms(f, file_size)
            types = [a.type for a in atoms]
            if 'ftyp' not in types or types.count('moov') != 1:
                return STATUS_NOT_MP4, atoms, file_size
            moov = next(a for a in atoms if a.type == 'moov')
            f.seek(moov.start)
            moov_buf = f.read(moov.size)
            if len(moov_buf) != moov.size:
                raise Mp4ParseError('lecture incomplète du moov')
            tables = []
            find_chunk_tables(moov_buf, moov.header_size, moov.size, tables)
    except CompressedMoovError:
        return STATUS_CMOV, [], file_size
    except (Mp4ParseError, OSError):
        return STATUS_NOT_MP4, [], file_size
    mdats = [a for a in atoms if a.type == 'mdat']
    if mdats and moov.start > mdats[0].start:
        return STATUS_NEEDS_MOVE, atoms, file_size
    return STATUS_FASTSTART, atoms, file_size


# ---------------------------------------------------------------------------
# Relocalisation
# ---------------------------------------------------------------------------

def _copy_range(src, dst, start, length):
    src.seek(start)
    remaining = length
    while remaining:
        chunk = src.read(min(CHUNK_SIZE, remaining))
        if not chunk:
            raise Mp4ParseError('lecture incomplète pendant la copie')
        dst.write(chunk)
        remaining -= len(chunk)


def relocate_moov(path):
    """Réécrit ``path`` avec le moov avant le mdat, atomiquement.

    Écrit dans un temporaire du même dossier, re-vérifie le temporaire
    avec inspect_mp4, puis os.replace. Lève Mp4ParseError ou
    CompressedMoovError en laissant l'original intact.
    """
    path = Path(path)
    file_size = path.stat().st_size
    tmp_name = None
    try:
        with open(path, 'rb') as src:
            atoms = parse_top_level_atoms(src, file_size)
            types = [a.type for a in atoms]
            if types.count('moov') != 1 or 'ftyp' not in types:
                raise Mp4ParseError('structure inattendue (ftyp/moov)')
            moov = next(a for a in atoms if a.type == 'moov')
            ftyp = next(a for a in atoms if a.type == 'ftyp')

            src.seek(moov.start)
            moov_buf = bytearray(src.read(moov.size))
            if len(moov_buf) != moov.size:
                raise Mp4ParseError('lecture incomplète du moov')

            tables = []
            find_chunk_tables(moov_buf, moov.header_size, moov.size, tables)
            if not tables:
                raise Mp4ParseError(
                    'aucune table stco/co64 dans le moov — relocalisation refusée')

            # Si le champ taille du moov valait 0 (« jusqu'à la fin du
            # fichier »), il doit devenir explicite avant déplacement.
            (stored_size,) = struct.unpack_from('>I', moov_buf, 0)
            if stored_size == 0:
                if moov.header_size != 8 or moov.size > UINT32_MAX:
                    raise Mp4ParseError('taille de moov non représentable')
                struct.pack_into('>I', moov_buf, 0, moov.size)

            insertion_point = ftyp.end  # le moov ira juste après le ftyp
            patch_chunk_tables(moov_buf, tables, insertion_point,
                               moov.start, moov.end, moov.size)

            fd, tmp_name = tempfile.mkstemp(
                prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
            with os.fdopen(fd, 'wb') as dst:
                for atom in atoms:
                    if atom is moov:
                        continue
                    _copy_range(src, dst, atom.start, atom.size)
                    if atom is ftyp:
                        dst.write(moov_buf)
                dst.flush()
                os.fsync(dst.fileno())

        # Ici source ET temporaire sont fermés — indispensable pour
        # os.replace sous Windows (on ne remplace pas un fichier ouvert).
        # Auto-contrôle complet du temporaire avant remplacement.
        status, _, new_size = inspect_mp4(tmp_name)
        if status != STATUS_FASTSTART:
            raise Mp4ParseError(
                f'vérification du fichier réécrit échouée (statut {status})')
        if new_size != file_size:
            raise Mp4ParseError(
                f'taille réécrite {new_size} ≠ originale {file_size}')

        os.replace(tmp_name, path)
    except BaseException:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        raise


# ---------------------------------------------------------------------------
# Commande
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = ("Rend les MP4 de animated_cp diffusables progressivement en "
            "déplaçant l'atome moov avant mdat (qtfaststart pur Python, "
            "sans ré-encodage), avec écriture atomique vérifiée")

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Analyser et rapporter sans rien écrire',
        )
        parser.add_argument(
            '--backup-dir',
            help='Copier chaque original dans ce dossier avant réécriture '
                 '(facultatif : l\'opération est vérifiée sans perte)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        media_root = Path(settings.MEDIA_ROOT)
        directory = media_root / 'animated_cp'
        backup_root = Path(options['backup_dir']) if options['backup_dir'] else None

        self.stdout.write(f'Dossier vidéos : {directory} (existe : {directory.exists()})')
        if backup_root:
            self.stdout.write(f'Sauvegarde     : {backup_root}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — aucune écriture'))
        self.stdout.write('')

        if not directory.exists():
            self.stderr.write(self.style.ERROR(f'Dossier introuvable : {directory}'))
            return

        counts = {
            'examined': 0, 'faststart': 0, 'needs_move': 0, 'moved': 0,
            'not_mp4': 0, 'cmov': 0, 'webm': 0, 'other': 0, 'errors': 0,
        }
        mp4_sizes = []  # (taille, nom) pour le palmarès final

        for path in sorted(directory.iterdir()):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix == '.webm':
                counts['webm'] += 1  # streaming progressif natif : silencieux
                continue
            if suffix != '.mp4':
                counts['other'] += 1
                continue

            counts['examined'] += 1
            size = path.stat().st_size
            mo = size / MO
            mp4_sizes.append((size, path.name))

            status, _, _ = inspect_mp4(path)

            if status == STATUS_FASTSTART:
                counts['faststart'] += 1
                self.stdout.write(f'  = déjà faststart : {path.name} ({mo:.1f} Mo)')
            elif status == STATUS_NOT_MP4:
                counts['not_mp4'] += 1
                self.stdout.write(self.style.WARNING(
                    f'  ? pas un MP4 valide : {path.name} ({mo:.1f} Mo)'))
            elif status == STATUS_CMOV:
                counts['cmov'] += 1
                self.stdout.write(self.style.WARNING(
                    f'  ! moov compressé (cmov), ignoré : {path.name} ({mo:.1f} Mo)'))
            elif dry_run:
                counts['needs_move'] += 1
                self.stdout.write(f'  > à relocaliser : {path.name} ({mo:.1f} Mo)')
            else:
                if backup_root is not None:
                    backup_path = backup_root / 'animated_cp' / path.name
                    try:
                        backup_path.parent.mkdir(parents=True, exist_ok=True)
                        if not backup_path.exists():
                            shutil.copy2(path, backup_path)
                    except OSError as exc:
                        counts['errors'] += 1
                        self.stderr.write(self.style.ERROR(
                            f'  ! sauvegarde impossible pour {path.name} — {exc} '
                            f'(original intact, non traité)'))
                        continue
                try:
                    relocate_moov(path)
                except (Mp4ParseError, CompressedMoovError, OSError) as exc:
                    counts['errors'] += 1
                    self.stderr.write(self.style.ERROR(
                        f'  ! échec sur {path.name} — {exc} (original intact)'))
                    continue
                counts['moved'] += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  + relocalisé : {path.name} ({mo:.1f} Mo)'))

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('RÉSUMÉ FASTSTART')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Fichiers MP4 examinés :          {counts["examined"]}')
        self.stdout.write(f'Déjà faststart :                 {counts["faststart"]}')
        if dry_run:
            self.stdout.write(f'À relocaliser :                  {counts["needs_move"]}')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Relocalisés :                    {counts["moved"]}'))
        self.stdout.write(f'Pas des MP4 valides :            {counts["not_mp4"]}')
        self.stdout.write(f'Moov compressé (ignorés) :       {counts["cmov"]}')
        self.stdout.write(f'WebM ignorés (streaming natif) : {counts["webm"]}')
        if counts['other']:
            self.stdout.write(f'Autres fichiers ignorés :        {counts["other"]}')
        if counts['errors']:
            self.stdout.write(self.style.ERROR(
                f'Erreurs (originaux intacts) :    {counts["errors"]}'))
        else:
            self.stdout.write(f'Erreurs :                        {counts["errors"]}')

        if mp4_sizes:
            self.stdout.write('')
            self.stdout.write('Fichiers les plus lourds (candidats à une recompression)')
            for rank, (size, name) in enumerate(
                    sorted(mp4_sizes, reverse=True)[:10], start=1):
                self.stdout.write(f'  {rank:>2}. {name}  {size / MO:.1f} Mo')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('--dry-run : rien n\'a été écrit'))
        self.stdout.write('')
        self.stdout.write('Les noms de fichiers sont inchangés — aucune '
                          'reconstruction d\'index nécessaire.')
