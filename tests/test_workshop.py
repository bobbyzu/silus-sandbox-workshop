import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'src/workshop.py'

class WorkshopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / '.claude').mkdir()
        self.settings = self.home / '.claude/settings.json'
        self.original = {'permissions': {'defaultMode': 'auto', 'ask': ['Bash(my-command *)']},
                         'custom': {'keep': True}, 'sandbox': {'filesystem': {'denyRead': ['~/.private']}}}
        self.settings.write_text(json.dumps(self.original))

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args):
        env = dict(os.environ, HOME=str(self.home))
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=env,
                              capture_output=True, text=True)

    def test_preview_is_pure(self):
        before = self.settings.read_bytes()
        p = self.run_cmd('install')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertFalse((self.home / 'silus-workshop').exists())

    def test_apply_merge_rollback(self):
        before = self.settings.read_bytes()
        p = self.run_cmd('install', '--apply')
        self.assertEqual(p.returncode, 0, p.stderr)
        changed = json.loads(self.settings.read_text())
        self.assertTrue(changed['sandbox']['enabled'])
        self.assertEqual(changed['permissions']['defaultMode'], 'auto')
        self.assertEqual(changed['custom'], {'keep': True})
        self.assertIn('Bash(my-command *)', changed['permissions']['ask'])
        self.assertIn('~/.private', changed['sandbox']['filesystem']['denyRead'])
        self.assertTrue((self.home / 'silus-workshop/silus-acid-smiley/org.arche.silus.acid/contents/ui/main.qml').is_file())
        (self.home / 'silus-workshop/SAUVEGARDE.txt').write_text('copie : disque externe\n')
        self.assertEqual(self.run_cmd('verify').returncode, 2)  # no false sandbox proof
        self.assertEqual(self.run_cmd('install', '--apply').returncode, 1)
        p = self.run_cmd('rollback', '--apply')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.settings.read_bytes(), before)

    def test_rollback_refuses_modified_settings(self):
        self.assertEqual(self.run_cmd('install', '--apply').returncode, 0)
        modified = json.loads(self.settings.read_text())
        modified['another'] = 1
        self.settings.write_text(json.dumps(modified))
        p = self.run_cmd('rollback', '--apply')
        self.assertEqual(p.returncode, 1)
        self.assertIn('changé', p.stderr)

    def test_existing_claude_absent(self):
        self.settings.unlink()
        self.assertEqual(self.run_cmd('install', '--apply').returncode, 0)
        self.assertEqual(self.run_cmd('rollback', '--apply').returncode, 0)
        self.assertFalse(self.settings.exists())

    def test_invalid_json_refused(self):
        self.settings.write_text('{invalid')
        p = self.run_cmd('install', '--apply')
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.settings.read_text(), '{invalid')

    # --- contre-audit Silus : faux rouges et faux verts ---
    def manual_config(self, atelier, shared):
        """Configuration écrite à la main, chemins en forme « ~/ » (cas réel de l'Arche)."""
        cfg = {'permissions': {'defaultMode': 'default',
                               'additionalDirectories': [atelier, shared],
                               'allow': ['Bash(plasmoidviewer *)'],
                               'ask': ['Edit(~/.ssh/**)', 'Edit(~/.gnupg/**)', 'Edit(~/.bashrc)',
                                       'Edit(~/.profile)', 'Edit(~/.config/autostart/**)',
                                       'Edit(~/.config/systemd/**)', 'Edit(~/.local/bin/**)',
                                       'Edit(~/.local/share/plasma/**)', 'Edit(~/.claude/settings.json)',
                                       'Bash(sudo *)', 'Bash(pkexec *)', 'Bash(systemctl *)',
                                       'Bash(crontab *)', 'Bash(nmcli *)', 'Bash(nordvpn *)',
                                       'Bash(apt *)', 'Bash(git push *)', 'Bash(gh *)']},
               'sandbox': {'enabled': True, 'excludedCommands': ['plasmoidviewer *'],
                           'filesystem': {'allowWrite': [atelier, shared],
                                          'denyRead': ['~/.ssh', '~/.gnupg']}}}
        self.settings.write_text(json.dumps(cfg))

    def test_tilde_paths_are_not_a_false_red(self):
        self.manual_config('~/Arche/atelier', '~/Arche/partage')
        (self.home / 'Arche/atelier/.git').mkdir(parents=True)
        (self.home / 'Arche/atelier/.git/HEAD').write_text('ref: refs/heads/main\n')
        p = self.run_cmd('--atelier', '~/Arche/atelier', '--shared', '~/Arche/partage', 'verify')
        self.assertEqual(p.returncode, 2, p.stdout)  # configuration correcte, confinement non testé
        self.assertNotIn('ÉCHEC', p.stdout)

    def test_merge_does_not_duplicate_tilde_and_absolute(self):
        self.manual_config('~/silus-workshop', '~/silus-shared')
        self.assertEqual(self.run_cmd('install', '--apply').returncode, 0)
        cfg = json.loads(self.settings.read_text())
        self.assertEqual(len(cfg['sandbox']['filesystem']['allowWrite']), 2)
        self.assertEqual(len(cfg['permissions']['additionalDirectories']), 2)

    def test_empty_secret_dirs_and_missing_dirs_are_not_green(self):
        for d in ('.ssh', '.gnupg', 'at', 'sh'):
            (self.home / d).mkdir()
        self.manual_config(str(self.home / 'at'), str(self.home / 'sh'))
        (self.home / '.claude' / 'settings.json').rename(self.home / 'settings.keep')
        (self.home / '.claude').rmdir()   # dossier .claude absent : un « refus » ne prouverait rien
        p = self.run_cmd('--atelier', str(self.home / 'at'), '--shared', str(self.home / 'sh'),
                         'verify', '--inside-claude')
        out = p.stdout
        self.assertIn('PAS masqué', out)             # .ssh vide sans tmpfs : jamais OK
        self.assertNotIn('masqué par le bac à sable', out)
        self.assertIn('NON VÉRIFIÉ (dossier absent', out)
        self.assertNotIn('RECETTE AUTOMATISÉE OK', out)
        self.assertEqual(p.returncode, 1)


    # --- l'escargot : une autre copie de l'atelier ---
    def verify_copy(self, prepare):
        at = self.home / 'Arche/at'
        at.mkdir(parents=True)
        prepare(at)
        self.manual_config(str(at), str(self.home / 'Arche/sh'))
        return self.run_cmd('--atelier', str(at), '--shared', str(self.home / 'Arche/sh'), 'verify')

    def test_no_other_copy_shows_snail(self):
        p = self.verify_copy(lambda at: None)
        self.assertEqual(p.returncode, 1)
        self.assertIn('aucune autre copie', p.stdout)
        self.assertIn('Ayez une autre copie', p.stdout)

    def test_git_parent_counts_but_not_home(self):
        (self.home / '.git').mkdir()          # dépôt de dotfiles dans le HOME : ne compte pas
        p = self.verify_copy(lambda at: None)
        self.assertEqual(p.returncode, 1)
        (self.home / 'Arche/.git').mkdir()    # dépôt englobant l'atelier : compte
        (self.home / 'Arche/.git/HEAD').write_text('ref: refs/heads/main\n')
        p = self.run_cmd('--atelier', str(self.home / 'Arche/at'), '--shared', str(self.home / 'Arche/sh'), 'verify')
        self.assertIn('versionné par git', p.stdout)
        self.assertNotIn('Ayez une autre copie', p.stdout)

    def test_declared_backup_is_labelled_unverified(self):
        p = self.verify_copy(lambda at: (at / 'SAUVEGARDE.txt').write_text('borg, disque du monastère\n'))
        self.assertIn('DÉCLARÉE', p.stdout)
        self.assertNotIn('Ayez une autre copie', p.stdout)
        self.assertEqual(p.returncode, 2)

    def test_empty_declaration_does_not_count(self):
        p = self.verify_copy(lambda at: (at / 'SAUVEGARDE.txt').write_text(''))
        self.assertIn('Ayez une autre copie', p.stdout)

    # --- contre-audit Ael : chemins, symlinks et manifeste ---
    def test_refuse_sensitive_and_outside_workspaces(self):
        for path in ('~/.ssh/atelier', '~/.claude/out', '~/.config/foo', '~/Arche/../.gnupg', '/', '/tmp'):
            with self.subTest(path=path):
                p = self.run_cmd('--atelier', path, 'install')
                self.assertNotEqual(p.returncode, 0, path)

    def test_refuse_symlink_chain_and_nested_workspaces(self):
        (self.home / 'Arche').mkdir()
        (self.home / 'alias').symlink_to(self.home / 'Arche', target_is_directory=True)
        self.assertNotEqual(self.run_cmd('--atelier', '~/alias/atelier', 'install').returncode, 0)
        p = self.run_cmd('--atelier', '~/Arche/at', '--shared', '~/Arche/at/shared', 'install')
        self.assertNotEqual(p.returncode, 0)

    def test_git_placeholder_is_not_a_repository(self):
        at = self.home / 'Arche/at'
        (at / '.git').mkdir(parents=True)
        self.manual_config(str(at), str(self.home / 'Arche/sh'))
        p = self.run_cmd('--atelier', str(at), '--shared', str(self.home / 'Arche/sh'), 'verify')
        self.assertIn('aucune autre copie', p.stdout)

    def test_rollback_refuses_tampered_backup_pointer(self):
        self.assertEqual(self.run_cmd('install', '--apply').returncode, 0)
        state = self.home / '.claude/silus-workshop-state.json'
        value = json.loads(state.read_text())
        value['backup'] = str(self.home / 'unrelated.txt')
        state.write_text(json.dumps(value))
        p = self.run_cmd('rollback', '--apply')
        self.assertNotEqual(p.returncode, 0)
        self.assertTrue(self.settings.is_file())

    def test_refuse_symlink_manifest(self):
        outside = self.home / 'outside.json'
        outside.write_text('{}')
        (self.home / '.claude/silus-workshop-state.json').symlink_to(outside)
        self.assertNotEqual(self.run_cmd('install', '--apply').returncode, 0)
        self.assertEqual(outside.read_text(), '{}')


if __name__ == '__main__':
    unittest.main()
