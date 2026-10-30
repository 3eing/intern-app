import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from flask import Flask
from jinja2 import ChoiceLoader, DictLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps'))

from modules.eepower.presentation.blueprint import eepower_bp


class EasyPowerPatternsTest(unittest.TestCase):
    def test_remove_one_pattern_and_ignore_stale_form(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = Flask(__name__)
            app.config.update(TESTING=True, SECRET_KEY='test')
            app.extensions['paths'] = SimpleNamespace(eep_uploads=root, generated=root / 'generated')
            app.register_blueprint(eepower_bp)
            app.jinja_loader = ChoiceLoader([
                DictLoader({'base.html': '{% block content %}{% endblock %}'}),
                app.jinja_loader,
            ])
            client = app.test_client()

            for bus in ('-SEC$', '-SEC$', '-PRIM$'):
                response = client.post('/eepower-2', data={'btn_id': 'ajouter_bus', 'bus': bus}, follow_redirects=True)
                self.assertEqual(response.status_code, 200)

            file = root / 'bus_exclus'
            self.assertEqual(file.read_text().splitlines(), ['-SEC$', '-SEC$', '-PRIM$'])
            response = client.post('/eepower-2', data={
                'btn_id': 'supprimer_bus', 'bus_index': '1', 'bus': '-SEC$',
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(file.read_text().splitlines(), ['-SEC$', '-PRIM$'])
            self.assertEqual(response.data.count(b'aria-label="Supprimer le motif'), 2)

            client.post('/eepower-2', data={
                'btn_id': 'supprimer_bus', 'bus_index': '1', 'bus': '-SEC$',
            })
            self.assertEqual(file.read_text().splitlines(), ['-SEC$', '-PRIM$'])


if __name__ == '__main__':
    unittest.main()
