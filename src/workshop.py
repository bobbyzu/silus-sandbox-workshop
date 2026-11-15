#!/usr/bin/env python3
"""Silus Sandbox Workshop — conservative config merger and validation probes."""
import argparse
import copy
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime, timezone

ASK = [
    'Edit(~/.ssh/**)', 'Edit(~/.gnupg/**)',
    'Edit(~/.bashrc)', 'Edit(~/.profile)',
    'Edit(~/.config/autostart/**)', 'Edit(~/.config/systemd/**)',
    'Edit(~/.local/bin/**)', 'Edit(~/.local/share/plasma/**)',
    'Edit(~/.claude/settings.json)',
    'Bash(sudo *)', 'Bash(pkexec *)', 'Bash(systemctl *)',
    'Bash(crontab *)', 'Bash(nmcli *)', 'Bash(nordvpn *)',
    'Bash(apt *)', 'Bash(git push *)', 'Bash(gh *)'
]
ALLOWED = ['Bash(plasmoidviewer *)']
EXCLUDED = ['plasmoidviewer *']
DENY_READ = ['~/.ssh', '~/.gnupg']
ROOT = Path(__file__).resolve().parent.parent
SMILEY = ROOT / 'assets/silus-acid-smiley'


def dump_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(entry):
    """Forme comparable d'un chemin de réglage : « ~/x » et « /home/u/x » sont égaux."""
    return os.path.normpath(os.path.expanduser(entry)) if isinstance(entry, str) else entry


def add_unique(obj, key, values):
    current = obj.setdefault(key, [])
    if not isinstance(current, list) or any(not isinstance(x, str) for x in current):
        raise ValueError('Configuration incompatible : ' + key)
    for value in values:
        # Comparaison sur la forme développée : pas de doublon « ~/x » / « /home/u/x ».
        if norm(value) not in {norm(x) for x in current}:
            current.append(value)


def contains_path(entries, path):
    return isinstance(entries, list) and norm(str(path)) in {norm(x) for x in entries}


def subdict(obj, key):
    result = obj.setdefault(key, {})
    if not isinstance(result, dict):
        raise ValueError('Configuration incompatible : ' + key)
    return result


def merge(original, atelier, shared):
    if not isinstance(original, dict):
        raise ValueError('Racine JSON non objet')
    data = copy.deepcopy(original)
    p = subdict(data, 'permissions')
    p.setdefault('defaultMode', 'default')
    add_unique(p, 'additionalDirectories', [atelier, shared])
    add_unique(p, 'allow', ALLOWED)
    add_unique(p, 'ask', ASK)
    sand = subdict(data, 'sandbox')
    sand['enabled'] = True
    add_unique(sand, 'excludedCommands', EXCLUDED)
    fs = subdict(sand, 'filesystem')
    add_unique(fs, 'allowWrite', [atelier, shared])
    add_unique(fs, 'denyRead', DENY_READ)
    return data


def load_settings(path):
    if not path.exists():
        return {}, None
    if path.is_symlink() or not path.is_file():
        raise ValueError('settings.json doit être un fichier ordinaire')
    raw = path.read_bytes()
    return json.loads(raw), raw


def atomic_write(path, raw, mode=0o600):
    fd, name = tempfile.mkstemp(prefix='.silus-', dir=str(path.parent))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def ensure_target(path):
    if path.exists() and (not path.is_dir() or path.is_symlink()):
        raise ValueError('Atelier/partage : chemin non répertoire ou lien symbolique')


def checked_path(arg):
    """Workspaces must stay under HOME, outside hidden/config roots and symlink chains."""
    home = Path.home().resolve()
    p = Path(os.path.expanduser(arg)).absolute()
    if not p.is_relative_to(home) or p == home:
        raise ValueError('Atelier/partage : choisir un sous-dossier du HOME')
    if any(part.startswith('.') for part in p.relative_to(home).parts):
        raise ValueError('Atelier/partage : dossiers caches et de configuration refuses')
    if p.resolve(strict=False) != p:
        raise ValueError('Atelier/partage : chaine de liens symboliques refusee')
    return p


def settings_path():
    parent = Path.home() / '.claude'
    if parent.is_symlink():
        raise ValueError('~/.claude symbolique : cible refusee')
    return parent / 'settings.json'


def manifest_path():
    return Path.home() / '.claude' / 'silus-workshop-state.json'


def make_plan(args):
    a, s = checked_path(args.atelier), checked_path(args.shared)
    if a == s or a in s.parents or s in a.parents:
        raise ValueError('Atelier et partage doivent être distincts et non imbriques')
    for x in (a, s):
        ensure_target(x)
    current, original = load_settings(settings_path())
    target = merge(current, str(a), str(s))
    return a, s, current, original, target


def install(args):
    atelier, shared, old, raw, target = make_plan(args)
    source_settings = settings_path()
    state_file = manifest_path()
    if state_file.exists() or state_file.is_symlink():
        raise ValueError('Installation déjà enregistrée ; utiliser verify ou rollback')
    data = dump_json(target)
    print('Plan : fusion des permissions, sauvegarde, deux dossiers, puis smiley.')
    print('Fichier : ~/.claude/settings.json ; autres clés conservées.')
    print('Atelier :', atelier, '| Partage :', shared)
    if not args.apply:
        print('Simulation uniquement. Utiliser install --apply pour confirmer.')
        return 0
    parent = source_settings.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = parent / f'settings.json.silus-workshop-{stamp}.bak'
    if raw is not None:
        if backup.exists():
            raise ValueError('Collision de nom de sauvegarde')
        atomic_write(backup, raw, mode=0o600)
    # Save a manifest first, to avoid silently overwriting a prior backup on retry.
    state = {'version': 1, 'backup': str(backup) if raw is not None else None,
             'original_absent': raw is None, 'installed_sha256': sha(data),
             'atelier': str(atelier), 'shared': str(shared)}
    atomic_write(state_file, dump_json(state))
    try:
        atelier.mkdir(parents=True, exist_ok=True, mode=0o755)
        shared.mkdir(parents=True, exist_ok=True, mode=0o755)
        atomic_write(source_settings, data, mode=0o600)
    except Exception:
        # settings.json n'a pas été remplacé : le manifeste ne décrit rien de réel.
        # Le garder bloquerait à la fois install (« déjà enregistrée ») et rollback
        # (« a changé ») ; on le retire, la sauvegarde reste en place.
        state_file.unlink(missing_ok=True)
        print('INSTALLATION ANNULÉE : settings.json inchangé ; sauvegarde conservée.', file=sys.stderr)
        raise
    try:
        dest = atelier / 'silus-acid-smiley'
        if not dest.exists():
            shutil.copytree(SMILEY, dest)
    except Exception:
        print('INSTALLATION INCOMPLÈTE : configuration appliquée, smiley non copié ; rollback disponible.', file=sys.stderr)
        raise
    print('INSTALLATION OK : configuration fusionnée, sauvegarde conservée.')
    print('Prochain test : verify --inside-claude (depuis le shell sandboxé de Claude Code).')
    return 0


def rollback(args):
    state_file = manifest_path()
    if not state_file.exists():
        raise ValueError('Aucun état d’installation géré par ce projet')
    if state_file.is_symlink() or not state_file.is_file():
        raise ValueError('Manifeste non regulier ou symbolique')
    state = json.loads(state_file.read_text())
    if not isinstance(state, dict) or state.get('version') != 1 or not isinstance(state.get('installed_sha256'), str) or not isinstance(state.get('original_absent'), bool):
        raise ValueError('Manifeste invalide')
    current = settings_path()
    _, now = load_settings(current)
    if now is None or sha(now) != state['installed_sha256']:
        raise ValueError('settings.json a changé depuis installation : rollback automatique refusé')
    if not args.apply:
        print('Simulation : restauration de la configuration précédente, sans supprimer les ateliers.')
        return 0
    if state['original_absent']:
        current.unlink()
    else:
        value = state.get('backup')
        if not isinstance(value, str):
            raise ValueError('Sauvegarde invalide')
        backup = Path(value)
        if (backup.parent != current.parent or not backup.name.startswith('settings.json.silus-workshop-')
                or not backup.name.endswith('.bak') or backup.is_symlink() or not backup.is_file()):
            raise ValueError('Sauvegarde hors perimetre ou introuvable')
        atomic_write(current, backup.read_bytes(), mode=0o600)
    state_file.unlink()
    print('ROLLBACK OK. Les dossiers créés restent en place.')
    return 0


REFUSALS = {errno.EACCES, errno.EPERM, errno.EROFS}


def probe_write(directory, expected, label):
    """Vrai seulement si le résultat est prouvé : un refus doit être un refus
    d'accès (EACCES, EPERM, EROFS), pas un dossier absent ou une autre erreur."""
    if not Path(directory).is_dir():
        return (False, f'{label}: NON VÉRIFIÉ (dossier absent : un refus ne prouverait rien)')
    try:
        with tempfile.NamedTemporaryFile(prefix='.silus-probe-', dir=str(directory), delete=True) as f:
            f.write(b'probe')
            f.flush()
    except OSError as exc:
        if exc.errno not in REFUSALS:
            return (False, f'{label}: NON VÉRIFIÉ (erreur inattendue {errno.errorcode.get(exc.errno, exc.errno)})')
        return (not expected, f'{label}: écriture refusée ({errno.errorcode[exc.errno]})')
    return (expected, f'{label}: écriture autorisée')


def masked_by_tmpfs(path):
    """Le bac à sable remplace les dossiers denyRead par un tmpfs vide.
    Un dossier simplement vide ne le prouve pas ; le point de montage, si."""
    target = os.path.realpath(path)
    try:
        with open('/proc/self/mountinfo') as handle:
            for line in handle:
                left, _, right = line.partition(' - ')
                fields = left.split()
                if len(fields) > 4 and fields[4] == target and right.split()[:1] == ['tmpfs']:
                    return True
    except OSError:
        return None
    return False


ESCARGOT = r'''
        @    @
         \  /       La cloison limite les dégâts,
       .--\/--.     elle ne les empêche pas.
      ( (@)    )~~
       `------'     Ayez une autre copie.  🐌
'''
DECLARATION = 'SAUVEGARDE.txt'


def other_copy(atelier):
    """L'atelier a-t-il une autre copie ? Dépôt git (en remontant, sans compter le HOME
    lui-même) ou déclaration écrite par l'humain. Rien n'est lu ni affiché du contenu."""
    home = Path.home().resolve()
    p = Path(atelier).resolve()
    while p != home and p != p.parent:
        git = p / '.git'
        if git.is_dir() and not git.is_symlink() and (git / 'HEAD').is_file():
            return 'git', ('atelier versionné par git (protège des réécritures ; '
                           'un dépôt local ne survit pas à la suppression du dossier)')
        p = p.parent
    decl = Path(atelier) / DECLARATION
    if decl.is_file() and not decl.is_symlink() and decl.stat().st_size > 0:
        return 'déclarée', 'sauvegarde DÉCLARÉE dans ' + DECLARATION + ' (non vérifiable par ce script)'
    return None, ('aucune autre copie : ni dépôt git, ni ' + DECLARATION +
                  " (y écrire où se trouve la sauvegarde de l'atelier)")


def verify(args):
    a, s = checked_path(args.atelier), checked_path(args.shared)
    checks = []
    def report(ok, message):
        checks.append(ok)
        print(('OK   ' if ok else 'ÉCHEC') + '  ' + message)
    # Le malentendu (« nettoie le dossier ») est plus fréquent que la malveillance :
    # dans l'atelier, l'agent peut tout casser. C'est voulu ; il faut donc une autre copie.
    kind, message = other_copy(a)
    report(kind is not None, message)
    copy_missing = kind is None
    try:
        config, _ = load_settings(settings_path())
        reference = merge({}, str(a), str(s))
        p, sand = config['permissions'], config['sandbox']
        fs = sand['filesystem']
        report(sand['enabled'] is True, 'sandbox.enabled')
        for path in (str(a), str(s)):
            report(contains_path(fs['allowWrite'], path) and contains_path(p['additionalDirectories'], path),
                   'accès atelier/partage déclaré : ' + path)
        report(all(x in fs['denyRead'] for x in DENY_READ), 'denyRead SSH/GnuPG configuré')
        report(all(x in p['ask'] for x in ASK), 'règles ask attendues configurées')
        report(all(x in p['allow'] for x in ALLOWED) and all(x in sand['excludedCommands'] for x in EXCLUDED), 'exception graphique déclarée')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report(False, 'configuration invalide/incomplète : ' + str(exc))
    if not args.inside_claude:
        print('NON TESTÉ : confinement réel. Cette commande tourne hors du shell sandboxé de Claude.')
        print('AUCUNE CÉLÉBRATION : exécuter verify --inside-claude dans la session Claude Code.')
        if copy_missing:
            print(ESCARGOT)
        return 2 if all(checks) else 1
    # The CLI flag does not establish the sandbox: results from an unsandboxed shell will FAIL.
    home = Path.home()
    probes = [(a, True, 'atelier'), (s, True, 'partage'),
              (home, False, 'HOME'), (home / '.claude', False, 'configuration Claude')]
    # Zones de persistance : sondées seulement si elles existent (rien n'est créé).
    for rel in ('.config/autostart', '.config/systemd/user', '.local/bin'):
        if (home / rel).is_dir():
            probes.append((home / rel, False, '~/' + rel))
    for directory, expected, label in probes:
        ok, msg = probe_write(directory, expected, label)
        report(ok, msg)
    # Comptes seulement, jamais de noms. La preuve est le masque tmpfs, pas le vide.
    for secret in DENY_READ:
        path = Path(os.path.expanduser(secret))
        if not path.is_dir():
            report(False, secret + ' : NON VÉRIFIÉ (dossier absent)')
            continue
        masked = masked_by_tmpfs(path)
        if masked is None:
            report(False, secret + ' : NON VÉRIFIÉ (/proc/self/mountinfo illisible)')
        else:
            report(masked, secret + (' : masqué par le bac à sable (tmpfs)' if masked
                                     else ' : PAS masqué (un dossier vide ne prouve rien)'))
    if all(checks):
        print('RECETTE AUTOMATISÉE OK (hors tests interactifs).')
        print('SUITE : valider une carte ask manuellement, puis lancer SEUL le plasmoidviewer nu :')
        print('plasmoidviewer -a ' + str(a / 'silus-acid-smiley/org.arche.silus.acid') + ' -s 520x600')
        return 0
    print('RECETTE EN ÉCHEC : pas de smiley.')
    if copy_missing:
        print(ESCARGOT)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atelier', default='~/silus-workshop', help='Dossier atelier')
    parser.add_argument('--shared', default='~/silus-shared', help='Dossier partage')
    cmds = parser.add_subparsers(dest='action', required=True)
    cmds.add_parser('install').add_argument('--apply', action='store_true')
    cmds.add_parser('rollback').add_argument('--apply', action='store_true')
    cmds.add_parser('verify').add_argument('--inside-claude', action='store_true')
    args = parser.parse_args(argv)
    try:
        return {'install': install, 'rollback': rollback, 'verify': verify}[args.action](args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print('ERREUR : ' + str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
