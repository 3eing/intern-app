from flask import Flask, Blueprint, abort, send_from_directory, current_app
from pyairtable import Api
from requests.exceptions import HTTPError
from urllib.request import urlretrieve
from app.utils.File import render_document
from pathlib import Path
import os
from datetime import datetime

api_key = os.environ.get('AIR_KEY')

airtable_api = Blueprint('airtable_api', __name__)

api = Api(api_key)
BASE_ID = api.bases()[0].id

DOC_TABLE = api.table(BASE_ID, "Documents")
PERSON_TABLE = api.table(BASE_ID, "Personnes")
PROJET_TABLE = api.table(BASE_ID, "Projets")

ROOT = Path(__file__).parents[2]
GEN_PATH = ROOT/Path('generated/developpement/doc')

current_app.debug = True

@airtable_api.route("/air/person/GET/<person_id>", methods=['GET', 'POST'])
def get_person(person_id):
    try:
        person = PERSON_TABLE.get(record_id=person_id)['fields']
        return person
    except HTTPError as e:
        current_app.logger.error(f"Error fetching person: {e}")
        raise ValueError("L'entrée personne : {0} n'existe pas".format(person_id))


@airtable_api.route("/air/person/GET/<project_id>", methods=['GET', 'POST'])
def get_project(project_id):
    try:
        project = PROJET_TABLE.get(record_id=project_id)['fields']
        return project
    except HTTPError as e:
        current_app.logger.error(f"Error fetching project: {e}")
        raise ValueError("L'entrée projet : {0} n'existe pas".format(project_id))


@airtable_api.route("/air/doc/GET/<doc_id>", methods=['GET', 'POST'])
def get_doc(doc_id):
    try:
        doc = DOC_TABLE.get(record_id=doc_id)['fields']
        return doc
    except HTTPError as e:
        current_app.logger.error(f"Error fetching doc: {e}")
        raise ValueError("L'entrée doc : {0} n'existe pas".format(doc_id))


def change_status(doc_id, status):
    if status not in ("Généré", "Non Généré", "Erreur", "Disponible"):
        raise ValueError("Le status : {0} n'existe pas".format(status))
    try:
        DOC_TABLE.update(doc_id, {"Statut document": status})
        return status
    except HTTPError as e:
        current_app.logger.error(f"Error changing status: {e}")
        raise ValueError("Erreur lors du changement de status : {0}".format(e))


@airtable_api.route('/air/doc/<string:doc_name>', methods=['GET'])
def get_doc_file(doc_name):
    path = GEN_PATH/doc_name
    current_app.logger.debug(f"Looking for file at: {path}")
    if not path.exists():
        current_app.logger.error(f"File not found: {path}")
        raise FileNotFoundError(f"Le fichier {doc_name} n'a pas été trouvé")
    return send_from_directory(GEN_PATH, doc_name, as_attachment=False)


@airtable_api.route('/air/doc/list_files', methods=['GET'])
def get_file_list():
    path = GEN_PATH
    current_app.logger.debug(f"Listing files in {path}")
    file_list = [(file.name, datetime.fromtimestamp(file.stat().st_mtime).isoformat()) for file in path.iterdir() if file.is_file()]
    current_app.logger.debug(f"Files saved: {file_list}")
    return file_list


@airtable_api.route("/air/doc/assemble/<doc_id>", methods=['GET', 'POST'])
def assemble_doc(doc_id):
    projects = []
    persons = []
    try:
        doc = get_doc(doc_id)
        current_app.logger.info(f"Fetched document: {doc['Nom']}")

    except HTTPError as e:
        current_app.logger.error(f"Error fetching document: {e}")
        raise ValueError("L'entrée doc : {0} n'existe pas".format(doc_id))

    for project_id in doc['Projets']:
        projects.append(get_project(project_id))

    for person_id in doc['Personnes']:
        persons.append(get_person(person_id))

    template_file, _ = urlretrieve(doc['Templates'][0]['url'])
    current_app.logger.debug(f"Template file retrieved: {template_file}")

    try:
        filename = doc['Nom'] + '.docx'
        rendered_doc = GEN_PATH/filename
        current_app.logger.debug(f"Rendering document to: {rendered_doc}")
        doc_name = Path(render_document(template_file, rendered_doc, projects, persons[0])).name
        status = change_status(doc_id, "Généré")
        current_app.logger.debug(f"Document generated: {doc_name}, status updated to: {status}")

        return get_doc_file(doc_name)

    except Exception as e:
        current_app.logger.error(f"Error rendering document: {e}")
        change_status(doc_id, "Erreur")
        raise ValueError("Une erreur s'est produite lors du rendu de documents :{0}".format(e))
