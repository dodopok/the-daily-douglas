import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from daily_douglas.model import EditionError, load_config, load_edition, validate_edition
from daily_douglas.printing import PrintError, print_edition
from daily_douglas.render import LayoutError, render_edition

ROOT = Path(__file__).resolve().parents[1]


class NewspaperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        cls.edition = load_edition(ROOT / 'examples' / 'edition.json')
        cls.config = load_config(ROOT / 'config.example.json')
        cls.manifest_path = render_edition(cls.edition, cls.config, cls.directory)
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_reading_order_and_physical_booklet(self):
        reading = PdfReader(self.directory / self.manifest['files']['reading']['path'])
        booklet = PdfReader(self.directory / self.manifest['files']['print']['path'])
        self.assertEqual(len(reading.pages), 4)
        self.assertEqual(len(booklet.pages), 2)
        for i, page in enumerate(reading.pages):
            self.assertIn(self.edition['pages'][i]['headline'].split('\n')[0], page.extract_text())
            self.assertIn('CONTEÚDO DE EXEMPLO', page.extract_text())
            self.assertAlmostEqual(float(page.mediabox.width), 420.94, places=1)
        # Reading order after folding: outside [4|1], inside [2|3].
        for page, pair in zip(booklet.pages, [(3, 0), (1, 2)]):
            text = page.extract_text()
            left, right = [self.edition['pages'][i]['headline'].split('\n')[0] for i in pair]
            self.assertLess(text.index(left), text.index(right))
            self.assertAlmostEqual(float(page.mediabox.width), 841.89, places=1)
        for entry in self.manifest['files'].values():
            self.assertEqual(hashlib.sha256((self.directory / entry['path']).read_bytes()).hexdigest(), entry['sha256'])

    def test_title_markup_is_literal_content(self):
        edition = copy.deepcopy(self.edition)
        edition['pages'][2]['articles'][0]['title'] = '<b>Literal & safe</b>'
        with tempfile.TemporaryDirectory() as output:
            path = render_edition(edition, self.config, output)
            manifest = json.loads(path.read_text(encoding='utf-8'))
            text = PdfReader(Path(output) / manifest['files']['reading']['path']).pages[2].extract_text()
            self.assertIn('<b>Literal & safe</b>', ' '.join(text.split()))

    def test_overflow_does_not_replace_previous_edition(self):
        edition = copy.deepcopy(self.edition)
        edition['pages'][1]['articles'][0]['paragraphs'] = [('Este conteúdo não pode desaparecer. ' * 200)]
        before = {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()}
        with self.assertRaises(LayoutError):
            render_edition(edition, self.config, self.directory)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()})

    def test_contract_rejects_ambiguous_dates_and_unsafe_links(self):
        for bad_date in ['today', '2026-02-30', '20260101']:
            edition = copy.deepcopy(self.edition)
            edition['date'] = bad_date
            with self.assertRaises(EditionError):
                validate_edition(edition)
        edition = copy.deepcopy(self.edition)
        edition['pages'][0]['articles'][0]['source'] = {'label': 'bad', 'url': 'javascript:alert(1)'}
        with self.assertRaises(EditionError):
            validate_edition(edition)

    def test_dry_run_does_not_spawn_or_write_state(self):
        with tempfile.TemporaryDirectory() as directory, patch('daily_douglas.printing.subprocess.run') as run:
            state = Path(directory) / 'state'
            result = print_edition(self.manifest_path, 'Test_Printer', state_dir=state)
            self.assertEqual(result['status'], 'dry_run')
            self.assertIn('sides=one-sided', result['command'])
            self.assertFalse(state.exists())
            run.assert_not_called()

    def test_submission_requires_review_and_blocks_a_second_attempt(self):
        response = subprocess.CompletedProcess([], 0, 'request id is Test_Printer-42 (1 file(s))\n', '')
        with tempfile.TemporaryDirectory() as directory, patch('daily_douglas.printing.shutil.which', return_value='/usr/bin/lp'), patch('daily_douglas.printing.subprocess.run', return_value=response) as run:
            with self.assertRaises(PrintError):
                print_edition(self.manifest_path, 'Test_Printer', submit=True, state_dir=directory)
            result = print_edition(self.manifest_path, 'Test_Printer', 'duplex', submit=True, reviewed=True, state_dir=directory)
            self.assertEqual(result['status'], 'submitted')
            self.assertEqual(result['job_id'], 'Test_Printer-42')
            self.assertIn('sides=two-sided-short-edge', run.call_args.args[0])
            self.assertNotIn('shell', run.call_args.kwargs)
            with self.assertRaises(PrintError):
                print_edition(self.manifest_path, 'Test_Printer', submit=True, reviewed=True, state_dir=directory)
            run.assert_called_once()

    def test_uncertain_submission_blocks_retry(self):
        with tempfile.TemporaryDirectory() as directory, patch('daily_douglas.printing.shutil.which', return_value='/usr/bin/lp'), patch('daily_douglas.printing.subprocess.run', side_effect=subprocess.TimeoutExpired('lp', 30)) as run:
            for _ in range(2):
                with self.assertRaises(PrintError):
                    print_edition(self.manifest_path, 'Test_Printer', submit=True, reviewed=True, state_dir=directory)
            run.assert_called_once()
            record = json.loads(next(Path(directory).glob('*.json')).read_text(encoding='utf-8'))
            self.assertEqual(record['status'], 'uncertain')

    def test_modified_pdf_is_not_printed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = render_edition(self.edition, self.config, directory)
            manifest = json.loads(path.read_text(encoding='utf-8'))
            pdf = Path(directory) / manifest['files']['print']['path']
            pdf.write_bytes(pdf.read_bytes() + b'\nmodified')
            with self.assertRaises(PrintError):
                print_edition(path, 'Test_Printer')

    def test_relative_image_cannot_escape_edition_directory(self):
        edition = copy.deepcopy(self.edition)
        edition['pages'][3]['comic']['image'] = '../outside.png'
        with tempfile.TemporaryDirectory() as output:
            with self.assertRaises(EditionError):
                render_edition(edition, self.config, output, ROOT / 'examples')


if __name__ == '__main__':
    unittest.main()
