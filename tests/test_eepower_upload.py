import io
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from flask import Flask
from jinja2 import ChoiceLoader, DictLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps'))

from modules.eepower.domain.services import scenario_number, group_by_scenario
from modules.eepower.infrastructure.file_validation import AF_COLUMNS, validate_file_epow, validate_report_filename
from modules.eepower.infrastructure.parsers import simple_cc_report
from modules.eepower.presentation.blueprint import eepower_bp
from modules.shared.infrastructure.error_handlers import FileError


class EasyPowerUploadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY='test')
        self.app.extensions['paths'] = SimpleNamespace(eep_uploads=self.root, generated=self.root / 'generated')
        self.app.register_blueprint(eepower_bp)
        self.app.jinja_loader = ChoiceLoader([
            DictLoader({'base.html': '{% block content %}{% endblock %}'}),
            self.app.jinja_loader,
        ])
        self.client = self.app.test_client()

    def post(self, files):
        return self.client.post('/eepower', data={'btn_id': 'soumettre_fichier', 'file': files})

    def uploaded(self):
        with self.client.session_transaction() as session:
            return self.root / session['eepower']['workspace_id']

    def test_rejected_formats_and_corrupt_files(self):
        for name, content, message in [
            ('Arc_Flash.csv', b'a,b', 'doit être exporté'),
            ('Equipment_Duty.csv', b'a,b', 'doit être exporté'),
            ('TCC_Coordination.csv', b'a,b', 'doit être exporté'),
            ('Arc_Flash.xls', b'a,b', 'extension'),
            ('Arc_Flash.xlsx', b'a,b', 'XLSX valide'),
            ('Arc_Flash_empty.xlsx', b'', 'vide'),
        ]:
            with self.subTest(name=name):
                file = self.root / name
                file.write_bytes(content)
                with self.assertRaisesRegex(FileError, message):
                    validate_file_epow(file)

    def test_valid_xlsx_and_missing_columns(self):
        file = self.root / 'Arc_Flash.XLSX'
        pd.DataFrame(columns=sorted(AF_COLUMNS)).to_excel(file, index=False)
        self.assertEqual(validate_file_epow(file), 'AF')
        pd.DataFrame(columns=['wrong']).to_excel(file, index=False)
        with self.assertRaisesRegex(FileError, 'Colonnes manquantes'):
            validate_file_epow(file)

    def test_cc_csv_and_xlsx(self):
        csv = self.root / 'LV_Momentary_scen_1.CSV'
        csv.write_text('Report\nBus kV,Sym Amps\n1,2\n', encoding='utf-8')
        self.assertEqual(validate_file_epow(csv), 'CC')
        xlsx = self.root / '30_Cycle_Report_scen_1.XLSX'
        pd.DataFrame({'Bus kV': [1], 'Sym Amps': [2]}).to_excel(xlsx, startrow=7, index=False)
        self.assertEqual(validate_file_epow(xlsx), 'CC')

    def test_cc_scenario_suffix(self):
        for name, expected in [('LV_Momentary_scen_1.csv', '1'), ('LM_Report_SCENARIO_2A.XLSX', '2A'), ('30_Cycle_Report_scen_12.xlsx', '12'), ('30 Cycle Report scenario 3.csv', '3')]:
            with self.subTest(name=name):
                self.assertEqual(validate_report_filename(name), 'CC')
                self.assertEqual(scenario_number(Path(name)), expected)
        for name in ['LV_Momentary.csv', 'LV_Momentary_1.csv', 'LV_Momentary_scen_.csv', 'LV_Momentary_scen_1_backup.csv', 'LV_Momentary_scen_2AB.xlsx']:
            with self.subTest(name=name):
                with self.assertRaisesRegex(FileError, 'numéro de scénario'):
                    validate_report_filename(name)
                self.assertIsNone(scenario_number(Path(name)))
        files = [Path('LV_Momentary_scen_1.csv'), Path('30_Cycle_Report_scen_1.xlsx'), Path('LV_Momentary_scen_2.csv')]
        self.assertEqual(group_by_scenario(files, '1'), files[:2])

    def test_missing_scenario_is_rejected_before_reading(self):
        with patch('modules.eepower.presentation.blueprint.validate_file_epow') as validate:
            response = self.post([(io.BytesIO(b'Report\nBus kV,Sym Amps\n1,2'), 'LV_Momentary.csv')])
        self.assertEqual(response.status_code, 302)
        validate.assert_not_called()
        self.assertEqual(list(self.uploaded().iterdir()), [])
        with self.client.session_transaction() as session:
            self.assertIn('numéro de scénario', session['_flashes'][0][1]['error'])

    def test_batch_preserves_existing_file_and_cleans_staging(self):
        valid = b'Report\nBus kV,Sym Amps\n1,2\n'
        self.post([(io.BytesIO(valid), 'LV_Momentary_scen_1.csv')])
        response = self.post([
            (io.BytesIO(b'broken'), 'LV_Momentary_scen_1.csv'),
            (io.BytesIO(b'wrong'), 'Arc_Flash.csv'),
            (io.BytesIO(valid), '30_Cycle_Report_scen_1.CSV'),
            (io.BytesIO(b'wrong'), 'other.exe'),
        ])
        self.assertEqual(response.status_code, 302)
        upload_dir = self.uploaded()
        self.assertEqual((upload_dir / 'LV_Momentary_scen_1.csv').read_bytes(), valid)
        self.assertEqual({p.name for p in upload_dir.iterdir()}, {'LV_Momentary_scen_1.csv', '30_Cycle_Report_scen_1.CSV'})
        self.assertFalse(list(self.root.glob('.eepower-*')))
        with self.client.session_transaction() as session:
            self.assertEqual(session['eepower']['report_types'], ['CC'])

    def test_unexpected_error_is_logged_and_batch_continues(self):
        with patch('modules.eepower.presentation.blueprint.validate_file_epow', side_effect=[RuntimeError('bug'), 'CC']), patch.object(self.app.logger, 'exception') as logger:
            response = self.post([(io.BytesIO(b'1'), 'LV_Momentary_scen_1.csv'), (io.BytesIO(b'2'), '30_Cycle_Report_scen_1.csv')])
        self.assertEqual(response.status_code, 302)
        logger.assert_called_once()
        self.assertEqual([p.name for p in self.uploaded().iterdir()], ['30_Cycle_Report_scen_1.csv'])
        self.assertFalse(list(self.root.glob('.eepower-*')))

    def test_page_shows_formats(self):
        response = self.client.get('/eepower')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for label in ['Courts-circuits (CC)', 'Arc Flash (AF)', 'Equipment Duty (ED)', 'TCC Coordination (TCC)']:
            self.assertIn(label, html)
        self.assertIn('accept=".csv,.xlsx"', html)
        self.assertIn('LV_Momentary_scen_1.csv', html)
        self.assertIn('30_Cycle_Report_scen_1.xlsx', html)
        self.assertIn('Fichiers ajoutés', html)

    def test_upload_results_are_in_the_matching_report_row(self):
        workbook = io.BytesIO()
        pd.DataFrame(columns=sorted(AF_COLUMNS)).to_excel(workbook, index=False)
        workbook.seek(0)
        self.post([
            (workbook, 'Arc_Flash_Scenario_Report.xlsx'),
            (io.BytesIO(b'csv'), 'Equipment_Duty.csv'),
            (io.BytesIO(b'csv'), 'TCC_Coordination.xls'),
            (io.BytesIO(b'csv'), 'LV_Momentary.csv'),
            (io.BytesIO(b'unknown'), 'unknown.txt'),
        ])
        html = self.client.get('/eepower').get_data(as_text=True)
        cells = dict(re.findall(r'data-report="([A-Z]+)"[^>]*>(.*?)</td>', html, re.S))
        self.assertIn('Ajouté', cells['AF'])
        self.assertIn('Arc_Flash_Scenario_Report.xlsx', cells['AF'])
        self.assertNotIn('Refusé', cells['AF'])
        self.assertIn('Equipment_Duty.csv', cells['ED'])
        self.assertIn('doit être exporté', cells['ED'])
        self.assertIn('TCC_Coordination.xls', cells['TCC'])
        self.assertIn('numéro de scénario', cells['CC'])
        self.assertNotIn('Equipment_Duty.csv', cells['AF'])
        self.assertIn('unknown.txt', html.split('<section id="message"')[1])
        refreshed = self.client.get('/eepower').get_data(as_text=True)
        self.assertIn('Ajouté</strong> — Arc_Flash_Scenario_Report.xlsx', refreshed)

    def test_rejected_replacement_shows_error_and_kept_file(self):
        valid = b'Report\nBus kV,Sym Amps\n1,2\n'
        self.post([(io.BytesIO(valid), 'LV_Momentary_scen_1.csv')])
        self.post([(io.BytesIO(b'Report\nwrong\n1\n'), 'LV_Momentary_scen_1.csv')])
        html = self.client.get('/eepower').get_data(as_text=True)
        cell = re.search(r'data-report="CC"[^>]*>(.*?)</td>', html, re.S).group(1)
        self.assertIn('Ajouté', cell)
        self.assertIn('Refusé', cell)
        self.assertIn('Colonnes manquantes', cell)

    def test_tcc_invalid_structure(self):
        file = self.root / 'TCC_Coordination.xlsx'
        for data in [{'wrong': [1]}, {'TCC Coordination Report': []}, {'TCC Coordination Report': ['heading']}]:
            with self.subTest(data=data):
                pd.DataFrame(data).to_excel(file, index=False)
                with self.assertRaises(FileError):
                    validate_file_epow(file)

    def test_cc_generation_reads_each_format(self):
        frame = pd.DataFrame({'Bus kV': [1], 'Sym Amps': [2], 'X/R Ratio': [3], 'Asym Amps': [4], 'I Peak': [5]}, index=['BUS'])
        csv = self.root / 'LV_Momentary_scen_1.CSV'
        csv.write_text('Report\n' + frame.to_csv(), encoding='utf-8')
        xlsx = self.root / '30_Cycle_Report_scen_1.XLSX'
        frame.to_excel(xlsx, startrow=7)
        result = simple_cc_report(xlsx, csv, bus_excluded=[])
        self.assertEqual(result.loc['BUS', 'I Sym 30'], 2)
        self.assertEqual(result.loc['BUS', 'Bus (V)'], 1000)


if __name__ == '__main__':
    unittest.main()
