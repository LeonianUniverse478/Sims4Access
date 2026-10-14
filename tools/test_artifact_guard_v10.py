"""Exercise stale/failed verification rejection without touching shipped files."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_checks_v10 as runner
import verify_v10_artifacts as verifier


class ArtifactGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='a11y-v10-artifacts-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root / 'build'
        self.build.mkdir()
        self.suite = self.root / 'tools/test_example.py'
        self.suite.parent.mkdir()
        self.suite.write_text('# source\n', encoding='utf-8')
        self.log = self.build / 'v10-test_example.log'
        self.log.write_text('Ran 3 tests in 0.001s\n\nOK\n', encoding='utf-8')
        self.inputs = {'tools/test_example.py': runner.sha(self.suite)}
        self.report = {
            'passed': True, 'input_stable': True, 'inputs': self.inputs,
            'results': [{'suite': 'tools/test_example.py', 'passed': True,
                         'returncode': 0, 'checks': 3, 'log': 'build/v10-test_example.log',
                         'log_sha256': runner.sha(self.log)}],
        }

    def verify(self):
        (self.build / 'v10-checks.json').write_text(json.dumps(self.report), encoding='utf-8')
        with patch.object(verifier, 'ROOT', self.root), \
                patch.object(verifier, 'input_hashes', return_value=self.inputs), \
                patch.object(verifier, 'test_paths', return_value=[self.suite]):
            return verifier.verify_checks(self.build)

    def test_counts_python_and_as_fixture_formats_but_not_unreported_exit(self):
        for output, count in [('Ran 3 tests in 0.001s', 3), ('ALL 7 CHECKS PASSED', 7),
                              ('11 Flash navigation fixture checks passed.', 11),
                              ('8 AS source-executing Build checks passed.', 8), ('done', 0)]:
            self.assertEqual(count, runner.check_count(output))

    def test_success_requires_matching_report_and_log(self):
        self.assertEqual([self.build / 'v10-checks.json', self.suite, self.log], self.verify())

    def test_source_change_invalidates_report(self):
        self.report['inputs'] = {'tools/test_example.py': 'stale'}
        with self.assertRaisesRegex(AssertionError, 'predate current source'):
            self.verify()

    def test_missing_suite_or_failed_run_is_rejected(self):
        self.report['results'] = []
        with self.assertRaisesRegex(AssertionError, 'suite set mismatch'):
            self.verify()
        self.report['passed'] = False
        with self.assertRaisesRegex(AssertionError, 'did not pass'):
            self.verify()

    def test_log_change_or_false_count_is_rejected(self):
        self.log.write_text('Ran 0 tests\n\nOK\n', encoding='utf-8')
        with self.assertRaisesRegex(AssertionError, 'log changed'):
            self.verify()
        self.report['results'][0]['log_sha256'] = runner.sha(self.log)
        with self.assertRaisesRegex(AssertionError, 'count mismatch'):
            self.verify()

    def test_source_modified_after_flash_compile_is_rejected(self):
        work = self.root / 'flash/work'
        work.mkdir(parents=True)
        source, output = work / 'source.as', work / 'output.swf'
        source.write_text('source', encoding='utf-8')
        output.write_bytes(b'movie')
        manifest = work / 'replace-batch.tsv'
        manifest.write_text('original.swf\t{}\tExample\t{}\n'.format(output, source), encoding='utf-8')
        os.utime(source, (1000, 1000))
        os.utime(output, (1001, 1001))
        with patch.object(verifier, 'ROOT', self.root):
            result, path = verifier.replacement_sources('work')
            self.assertEqual([source], result[output])
            self.assertEqual(manifest, path)
            os.utime(source, (1002, 1002))
            with self.assertRaisesRegex(AssertionError, 'movie predates source'):
                verifier.replacement_sources('work')


if __name__ == '__main__':
    unittest.main()
