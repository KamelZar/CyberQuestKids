#!/usr/bin/env python3
"""
CyberQuestKids — Testeur de Robustesse de Mot de Passe
───────────────────────────────────────────────────────
Outil PEDAGOGIQUE : montre combien de temps il faut pour
deviner un mot de passe par attaque dictionnaire + brute force.

Regles :
  - Testez UNIQUEMENT vos propres mots de passe.
  - Le mot de passe n'est JAMAIS stocke ni affiche.
  - Timeout = 60 secondes ; au-dela le mdp est considere sur.
"""

import hashlib
import itertools
import string
import time
import sys
import os
from getpass import getpass

# ── Configuration ──────────────────────────────────────────────────────────────
TIMEOUT_SECONDS = 60

# Chemin relatif vers les dictionnaires (meme repo, dossier Html/)
_HERE = os.path.dirname(os.path.abspath(__file__))
DICT_DIR = os.path.join(_HERE, "Html")
DICTIONARIES = [
    ("rockyou-75",  os.path.join(DICT_DIR, "rockyou-75.txt")),
    ("10-million",  os.path.join(DICT_DIR, "10-million.txt")),
]

# Jeux de caracteres pour le brute force (du plus simple au plus large)
CHARSETS = [
    ("minuscules",          string.ascii_lowercase),
    ("chiffres+minus",      string.ascii_lowercase + string.digits),
    ("alphanum complet",    string.ascii_letters   + string.digits),
    ("alphanum+symboles",   string.ascii_letters   + string.digits + string.punctuation),
]

# Le brute force tente toutes les longueurs de 1 a MAX_BF_LENGTH
# Au-dela de 6 chars le temps explose => on laisse le timeout decider
MAX_BF_LENGTH = 8


# ── Couleurs ANSI (desactivees si pas de TTY) ──────────────────────────────────

def _c(text, code):
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text

def green(t):  return _c(t, "92")
def red(t):    return _c(t, "91")
def yellow(t): return _c(t, "93")
def cyan(t):   return _c(t, "96")
def bold(t):   return _c(t, "1")


# ── Hachage ────────────────────────────────────────────────────────────────────

def _sha256(plain: str) -> str:
    """Retourne le hash SHA-256 d'une chaine. Jamais de stockage du plain text."""
    return hashlib.sha256(plain.encode("utf-8", errors="replace")).hexdigest()


# ── Affichage progression ──────────────────────────────────────────────────────

def show_progress(label: str, count: int, elapsed: float):
    bar_filled = int((elapsed / TIMEOUT_SECONDS) * 20)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    rate = count / elapsed if elapsed > 0 else 0
    print(
        f"\r  {cyan('⟳')} [{bar}] {label} — "
        f"{count:,} essais | {rate:,.0f}/s | {elapsed:.0f}s/{TIMEOUT_SECONDS}s   ",
        end="",
        flush=True,
    )


# ── Phase 1 : Attaque dictionnaire ────────────────────────────────────────────

def dictionary_attack(target_hash: str, deadline: float) -> tuple:
    """
    Parcourt les fichiers dictionnaire ligne par ligne.
    Compare les hashes uniquement — jamais le mot de passe en clair.
    Retourne (mot_trouve | None, nb_tentatives).
    """
    total_attempts = 0

    for dict_name, path in DICTIONARIES:
        if not os.path.exists(path):
            print(f"\n  {yellow('⚠')}  Dictionnaire introuvable : {path}")
            continue

        print(f"\n  {cyan('📖')} Dictionnaire : {bold(dict_name)}")
        attempts = 0
        start_phase = time.time()

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if time.time() >= deadline:
                        print()
                        return None, total_attempts + attempts

                    candidate = line.rstrip("\n")
                    attempts += 1

                    if attempts % 50_000 == 0:
                        show_progress(dict_name, total_attempts + attempts,
                                      time.time() - (deadline - TIMEOUT_SECONDS))

                    if _sha256(candidate) == target_hash:
                        print()
                        return candidate, total_attempts + attempts

        except OSError as exc:
            print(f"\n  {red('✗')} Erreur lecture {dict_name} : {exc}")

        total_attempts += attempts
        elapsed = time.time() - start_phase
        print(f"\n  {green('✓')} {dict_name} termine — {attempts:,} mots en {elapsed:.1f}s")

    return None, total_attempts


# ── Phase 2 : Brute force ──────────────────────────────────────────────────────

def brute_force(target_hash: str, deadline: float) -> tuple:
    """
    Genere toutes les combinaisons possibles jusqu'a MAX_BF_LENGTH chars.
    Logique : longueur 1, 2, … 6 x chaque jeu de caracteres.
    Retourne (mot_trouve | None, nb_tentatives).
    """
    total_attempts = 0
    start_phase = time.time()

    for length in range(1, MAX_BF_LENGTH + 1):
        for cs_name, charset in CHARSETS:
            label = f"len={length} [{cs_name}]"
            print(f"\n  {cyan('⚙')}  Brute force {label}")
            attempts = 0

            for combo in itertools.product(charset, repeat=length):
                if time.time() >= deadline:
                    print()
                    return None, total_attempts + attempts

                candidate = "".join(combo)
                attempts += 1

                if attempts % 200_000 == 0:
                    show_progress(label, total_attempts + attempts,
                                  time.time() - start_phase)

                if _sha256(candidate) == target_hash:
                    print()
                    return candidate, total_attempts + attempts

            total_attempts += attempts
            print(f"\n  {green('✓')} {label} — {attempts:,} combo")

    return None, total_attempts


# ── Rapport final ──────────────────────────────────────────────────────────────

def print_result(found, method: str, attempts: int, elapsed: float):
    print("\n" + "═" * 60)

    if found:
        print(f"\n  {red('🔓  MOT DE PASSE TROUVE')} via {bold(method)}")
        print(f"\n  {red('⚠   Votre mot de passe est FAIBLE.')}")
        print(f"      → {attempts:,} tentatives en {elapsed:.2f} secondes")
        print(f"\n  Conseils :")
        print(f"    • Utilisez au moins 12 caracteres")
        print(f"    • Melangez majuscules, chiffres et symboles (!@#...)")
        print(f"    • Evitez les mots du dictionnaire et les variantes simples")
        print(f"    • Utilisez un gestionnaire de mots de passe (Bitwarden, etc.)")
    else:
        print(f"\n  {green('🔒  MOT DE PASSE RESISTE')} — non trouve en {TIMEOUT_SECONDS}s")
        print(f"\n  {green('✓   Votre mot de passe a resiste a l attaque.')} ({attempts:,} essais)")
        print(f"\n  Pour aller plus loin :")
        print(f"    • Visez 16+ caracteres avec symbols pour etre encore plus sur")
        print(f"    • Activez l'authentification a deux facteurs (2FA)")
        print(f"    • Utilisez un gestionnaire de mots de passe")

    print(f"\n  Statistiques : {attempts:,} tentatives | {elapsed:.1f}s ecoulees")
    print("═" * 60 + "\n")


# ── Point d'entree ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 60)
    print(bold("  CyberQuestKids — Testeur de Robustesse de Mot de Passe"))
    print("═" * 60)
    print(f"\n  {yellow('⚠  PEDAGOGIQUE UNIQUEMENT')}")
    print(f"  Testez UNIQUEMENT vos propres mots de passe.")
    print(f"  Timeout : {TIMEOUT_SECONDS}s | Le mot de passe n'est jamais stocke.\n")

    # Saisie masquee (le caractere ne s'affiche pas dans le terminal)
    try:
        pwd = getpass("  Mot de passe a tester : ")
    except (KeyboardInterrupt, EOFError):
        print("\n  Annule.")
        sys.exit(0)

    if not pwd:
        print(red("  ✗ Mot de passe vide, arret."))
        sys.exit(1)

    # -----------------------------------------------------------------
    # Hashage immediat : on ne conserve que le hash en memoire.
    # La variable `pwd` est supprimee juste apres.
    # -----------------------------------------------------------------
    target_hash = _sha256(pwd)
    del pwd          # plus aucune reference au plain text
    # -----------------------------------------------------------------

    deadline = time.time() + TIMEOUT_SECONDS
    start    = time.time()
    found    = None
    method   = "aucun"
    attempts = 0

    # ── Phase 1 : Dictionnaire ────────────────────────────────────────
    print(f"\n  {bold('[ Phase 1/2 — Attaque dictionnaire ]')}")
    found, n = dictionary_attack(target_hash, deadline)
    attempts += n

    if found:
        method = "dictionnaire"

    # ── Phase 2 : Brute force (si toujours pas trouve) ────────────────
    if not found and time.time() < deadline:
        remaining = deadline - time.time()
        print(f"\n  {bold('[ Phase 2/2 — Brute force ]')} ({remaining:.0f}s restantes)")
        found, n = brute_force(target_hash, deadline)
        attempts += n
        if found:
            method = "brute force"

    elapsed = time.time() - start
    del target_hash   # nettoyage final

    print_result(found, method, attempts, elapsed)


if __name__ == "__main__":
    main()
