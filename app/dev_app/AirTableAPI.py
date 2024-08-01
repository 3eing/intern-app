from pyairtable import Api
from flask import Blueprint, abort, send_from_directory
from requests.exceptions import HTTPError
from urllib.request import urlretrieve
from app.utils.File import render_document
from pathlib import Path
import os


api_key = os.environ.get('AIR_KEY')

airtable_api = Blueprint('airtable_api', __name__)

api = Api(api_key)
BASE_ID = api.bases()[0].id

DOC_TABLE = api.table(BASE_ID, "Documents")
PERSON_TABLE = api.table(BASE_ID, "Personnes")
PROJET_TABLE = api.table(BASE_ID, "Projets")


@airtable_api.route("/air/person/GET/<person_id>", methods=['GET', 'POST'])
def get_person(person_id):
    try:
        person = PERSON_TABLE.get(record_id=person_id)['fields']
        return person
    except HTTPError as e:
        raise ValueError("L'entrée personne : {0} n'existe pas".format(person_id))


@airtable_api.route("/air/person/GET/<project_id>", methods=['GET', 'POST'])
def get_project(project_id):
    try:
        project = PROJET_TABLE.get(record_id=project_id)['fields']
        return project
    except HTTPError as e:
        raise ValueError("L'entrée projet : {0} n'existe pas".format(project_id))


@airtable_api.route("/air/doc/GET/<doc_id>", methods=['GET', 'POST'])
def get_doc(doc_id):
    try:
        doc = DOC_TABLE.get(record_id=doc_id)['fields']
        return doc
    except HTTPError as e:
        raise ValueError("L'entrée doc : {0} n'existe pas".format(doc_id))


def change_status(doc_id, status):
    if status not in ("Généré", "Non Généré", "Erreur", "Disponible"):
        raise ValueError("Le status : {0} n'existe pas".format(status))
    try:
        print(f"""
        fonction "change_status"
        Le statuts est {status}
        le doc ID est {doc_id} 
        """)
        DOC_TABLE.update(doc_id, {"Statut document": status})
        return status
    except HTTPError as e:
        raise ValueError("Erreur d'accès : {0}".format(e))


@airtable_api.route('/air/doc/<string:doc_name>', methods=['GET'])
def get_doc_file(doc_name):
    path = Path(f"generated/developpement/doc/{doc_name}")
    # Check if the file exists
    if not path.exists():
        abort(404, description=f"Le fichier {doc_name} n'a pas été trouvé")

    dir = path.absolute().parent
    file = path.name
    return send_from_directory(dir, file, as_attachment=True)


@airtable_api.route("/air/doc/assemble/<doc_id>", methods=['GET', 'POST'])
def assemble_doc(doc_id):
    projects = []
    persons = []
    try:
        doc = get_doc(doc_id)

    except HTTPError as e:
        raise ValueError("L'entrée doc : {0} n'existe pas".format(doc_id))

    for project_id in doc['Projets']:
        projects.append(get_project(project_id))

    for person_id in doc['Personnes']:
        persons.append(get_person(person_id))

    template_file, _ = urlretrieve(doc['Templates'][0]['url'])

    try:
        filename = doc['Nom'] + '.docx'
        rendered_doc = Path('generated/developpement/doc')/filename
        doc_name = Path(render_document(template_file, rendered_doc, projects, persons[0])).name
        print(f"""
        fonction "assemble_doc"
        le doc ID est {doc_id}
        le doc name est {doc_name}
        """)
        status = change_status(doc_id, "Généré")

        return get_doc_file(doc_name)

    except Exception as e:
        change_status(filename, "Erreur")
        raise Exception(e)



