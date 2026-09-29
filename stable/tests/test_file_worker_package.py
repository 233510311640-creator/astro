from pathlib import Path
import hashlib
import json
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class FileWorkerPackageTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'Production DPAPI execution is covered by the native installer fixture')
    def test_production_entrypoint_imports_isolated_and_refuses_non_windows_protector(self):
        archive = ROOT / 'windows/Cypher.CorePreview/file_operator.pyz'
        request = json.dumps({'input': 'Files: self-test', 'nonce': 'a' * 32}) + '\n'
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-X', 'utf8', str(archive)],
                                input=request, capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')  # Import/framing tracebacks would expose an entrypoint defect.

    def test_packaged_worker_matches_sources_and_native_pin(self):
        archive = ROOT / 'windows/Cypher.CorePreview/file_operator.pyz'
        host = (ROOT / 'windows/Cypher.CorePreview/FileTaskClient.cs').read_text(encoding='utf-8')
        pin = re.search(r'WorkerSha256 = "([a-f0-9]{64})";', host)[1]
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), pin)
        with zipfile.ZipFile(archive) as bundle:
            self.assertIsNone(bundle.testzip())
            for name in bundle.namelist():
                if name.startswith('local_assistant/'):
                    self.assertEqual(bundle.read(name), (ROOT / 'src' / name).read_bytes())

    def test_isolated_zip_can_import_and_complete_fixture_without_site_packages(self):
        archive = ROOT / 'windows/Cypher.CorePreview/file_operator.pyz'
        code = ('import sys,tempfile; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                'from local_assistant.file_tasks_selftest import run; '
                'from local_assistant.protected_payload import TestKeyProtector; '
                'box=tempfile.TemporaryDirectory(); run(TestKeyProtector(Path(box.name)/"key")); box.cleanup(); print("FILE_FIXTURE_OK")')
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-X', 'utf8', '-c', code, str(archive)],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'FILE_FIXTURE_OK')

    def test_installer_gates_file_worker_before_host_replacement(self):
        script = (ROOT / 'scripts/install_cypher_core_preview_windows.ps1').read_text(encoding='utf-8')
        self.assertIn('FileTaskClient.cs', script)
        self.assertIn('FileTaskHost.cs', script)
        self.assertLess(script.index('$fileSelfTest ='), script.index('\n    Stop-LegacyHost\n'))
        self.assertLess(script.index('$fileWorkerHash -ne $fileExpectedHash'), script.index('& $cscPath $compilerArguments'))
        self.assertLess(script.index('$installedFileWorker ='), script.index('Copy-Item -LiteralPath $builtExe -Destination $installedExe'))


if __name__ == '__main__': unittest.main()
