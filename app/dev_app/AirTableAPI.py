from flask import Blueprint, send_from_directory, current_app
from pyairtable import Api
from requests.exceptions import HTTPError
from app.dev_app.tools import _actualise_USD, _clean_project_text
from modules.dev_docs.infrastructure.download import download_file_from_Airtable
from app.utils.File import render_document
from pathlib import Path
import os
from datetime import datetime

# Fetch API key from environment variables for Airtable authentication
API_KEY = os.environ.get('AIR_KEY')

# Initialize a Flask Blueprint for organizing API routes related to Airtable
airtable_api = Blueprint('airtable_api', __name__)

# Initialize Airtable API client
api = Api(API_KEY)

# Get the base ID of the first base (assuming only one base is used)
BASE_ID = api.bases()[1].id

# Define Airtable tables in a dictionary
TABLE_NAMES = {
    "DOC": "Documents",
    "PERSON": "Personnes",
    "PROJET": "Projets",
    "PAYS": "Pays",
    "TAG": "tags",
    "COMPAGNIE": "Compagnies",
    "CONTACT": "Contacts",
    "XP": 'Expériences',
    "TEMPLATE": "Templates"
}

# Initialize the tables
TABLES = {name: api.table(BASE_ID, table_name) for name, table_name in TABLE_NAMES.items()}

# Define the root and generation path for document storage
ROOT = Path(__file__).parents[2]
GEN_PATH = ROOT / Path('generated/developpement/doc')
TEMPLATE_TMP_PATH = ROOT / Path('generated/developpement/templates')

# Enable debug mode for detailed logging
current_app.debug = True


@airtable_api.route("/air/GET/<entry_type>/<entry_id>", methods=['GET', 'POST'])
def get_entry(entry_type: str, entry_id: str) -> dict:
    """
    Fetch a record from the Airtable tables.

    :param entry_type: The type of entry to get (DOC, PERSON, etc.)
    :param entry_id: The ID of the entry record to retrieve (str).
    :return: A dictionary containing the entry's fields (dict).
    :raises ValueError: If the person record does not exist or there is a network error.
    """
    try:
        entry = TABLES[entry_type].get(record_id=entry_id)['fields']
        return entry
    except HTTPError as e:
        current_app.logger.error(f"Error fetching {TABLES[entry_type].name}: {e}")
        if e.response.status_code == 403:
            raise ConnectionRefusedError(f"L'accès à {TABLES[entry_type].name} : {entry_id} est "
                                         f"refusé par Airtable ou la table {TABLES[entry_type].nam} n'existe pas")
        else:
            raise ValueError(f"L'entrée {TABLES[entry_type].name} : {entry_id} n'existe pas")


def change_status(doc_id: str, status: str) -> str:
    """
    Update the status of a document in the Airtable "Documents" table.

    :param doc_id: The ID of the document whose status needs to be updated (str).
    :param status: The new status to set for the document (str).
                   Must be one of "Généré", "Non Généré", "Erreur", "Disponible".
    :return: The new status if successfully updated (str).
    :raises ValueError: If the status is invalid or there is a network error.
    """
    if status not in ("Généré", "Non Généré", "Erreur", "Disponible"):
        raise ValueError("Le status : {0} n'existe pas".format(status))
    try:
        TABLES["DOC"].update(doc_id, {"Statut document": status})
        return status
    except HTTPError as e:
        current_app.logger.error(f"Error changing status: {e}")
        raise ValueError("Erreur lors du changement de status : {0}".format(e))


@airtable_api.route('/air/doc/<string:doc_name>', methods=['GET'])
def get_doc_file(doc_name: str):
    """
    Serve a generated document file from the server's file system.

    :param doc_name: The name of the document file to serve (str).
    :return: The requested document file.
    :raises FileNotFoundError: If the requested file does not exist.
    """
    path = GEN_PATH / doc_name
    current_app.logger.debug(f"Looking for file at: {path}")
    if not path.exists():
        current_app.logger.error(f"File not found: {path}")
        raise FileNotFoundError(f"Le fichier {doc_name} n'a pas été trouvé")
    return send_from_directory(GEN_PATH, doc_name, as_attachment=False)


@airtable_api.route('/air/doc/list_files', methods=['GET'])
def get_file_list() -> list:
    """
    List all generated document files stored in the server's file system.

    :return: A list of tuples containing file names and their last modification timestamps (list of tuples).
    """
    path = GEN_PATH
    current_app.logger.debug(f"Listing files in {path}")
    file_list = [(file.name, datetime.fromtimestamp(file.stat().st_mtime).isoformat()) for file in path.iterdir() if
                 file.is_file()]
    current_app.logger.debug(f"Files saved: {file_list}")
    return file_list


def _fetch_attributes_of_entry(entry: dict) -> dict:
    """
    Placeholder function for fetching additional attributes of an Airtable entry.
    This function is currently incomplete.

    :param entry: The Airtable entry for which to fetch attributes (dict).
    :return: None
    """
    for key, item, in entry.items():
        type = None
        if key in {"Personnes", "Expert technique", 'Leader', 'Contacts'}:
            type = "PERSON"
        elif key == "Catégorie":
            type = "TAG"
        elif key == "Pays":
            type = "PAYS"
        elif key == "Client":
            type = "COMPAGNIE"

        if type is not None:
            if isinstance(item, list):
                i = -1
                for record_id in item:
                    i += 1
                    fetched = get_entry(type, record_id)
                    if key == 'Contacts':
                        fetched = '\n'.join([fetched['Nom'], fetched['Rôle'], fetched['Téléphone'], fetched['Email']])
                    elif isinstance(fetched, dict):
                        fetched = fetched["Nom"]

                    entry[key][i] = fetched
            else:
                fetched = get_entry(type, item)
                entry[key] = fetched
        else:
            next

    return entry




@airtable_api.route("/air/doc/assemble/<doc_id>", methods=['GET', 'POST'])
def assemble_doc(doc_id: str):
    """
    Assemble a document from a template by combining data from related projects and persons.

    :param doc_id: The ID of the document to assemble (str).
    :return: The assembled document file.
    :raises ValueError: If there is an error during document fetching, rendering, or status updating.
    """
    projects = []
    persons = []
    compagnies = []
    try:
        # Fetch document metadata
        doc = get_entry("DOC", doc_id)
        current_app.logger.info(f"Fetched document: {doc['Nom']}")

    except HTTPError as e:
        current_app.logger.error(f"Error fetching document: {e}")
        raise ValueError("L'entrée doc : {0} n'existe pas".format(doc_id))

    # Fetch related projects and persons
    try:
        for project_id in doc['Projets']:
            project = _fetch_attributes_of_entry(get_entry("PROJET", project_id))

            try:
                project = _actualise_USD(project, attributes_to_actualise=["Valeur",  "Valeur totale"])
            except ValueError as e:
                current_app.logger.debug(e)

            projet_structured = _clean_project_text(project)


            projects.append(projet_structured)

    except Exception as e:
        current_app.logger.error(f"Error fetching project values: {e}")
        change_status(project_id, "Erreur")
        raise ValueError("Une erreur s'est produite lors du rendu de documents :{0}".format(e))

    if "Personnes" in doc.keys():
        for person_id in doc['Personnes']:
            persons.append(get_entry("PERSON", person_id))

    template_file = None
    try:
        # Define filename and render the document
        filename = doc['Nom'] + '.docx'
        rendered_doc = GEN_PATH / filename

        try:
        # Download template file from the URL provided in the document record
            template = get_entry("TEMPLATE", doc['Templates'][0])
            template_file = download_file_from_Airtable(template['template'][0]['url'], TEMPLATE_TMP_PATH,
                                                        suffix=".docx")
            current_app.logger.debug(f"Template file retrieved: {template_file}")

        except Exception as e:
            current_app.logger.error(f"Error downloading document: {e}")
            change_status(doc_id, "Erreur")
            raise ValueError("Une erreur s'est produite lors du téléchargement de documents :{0}".format(e))


        current_app.logger.debug(f"Rendering document to: {rendered_doc}")
        doc_name = Path(render_document(template_file, rendered_doc, projects, persons)).name

        # Update document status to "Généré" after successful rendering
        status = change_status(doc_id, "Généré")
        current_app.logger.debug(f"Document generated: {doc_name}, status updated to: {status}")

        # Serve the generated document file
        return get_doc_file(doc_name)

    except Exception as e:
        current_app.logger.error(f"Error rendering document: {e}")
        change_status(doc_id, "Erreur")
        raise ValueError("Une erreur s'est produite lors du rendu de documents :{0}".format(e))
    finally:
        if template_file and Path(template_file).exists():
            Path(template_file).unlink(missing_ok=True)
