from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import json

def create_dir_if_dont_exist(dir_name):
    Path(dir_name).mkdir(parents=True, exist_ok=True)
    return Path(dir_name)


def get_uploads_files(upload_dir:Path=Path(r'.\uploads'))->list:
    upload_dir = Path(upload_dir)
    if upload_dir.exists() and upload_dir.is_dir():
        return [child for child in upload_dir.iterdir()]
    else:
        print("Directory ", upload_dir.name, " doesn't exist")
        return []


def purge_file(dir_name=Path(r'.\uploads')):
    if get_uploads_files(dir_name):
        for file in get_uploads_files(dir_name):
            file.unlink()


def zip_files(list_of_files, zip_file_name=''):
    """Crée un ZIP à côté du premier fichier et retourne son chemin."""
    files = [Path(file) for file in list_of_files]
    if not files:
        raise ValueError("list_of_files must contain at least one file")

    archive_name = Path(zip_file_name or "archive.zip").name
    if not archive_name.lower().endswith(".zip"):
        archive_name += ".zip"

    archive_path = files[0].parent / archive_name

    with ZipFile(archive_path, "w", ZIP_DEFLATED, allowZip64=True) as archive:
        for file in files:
            archive.write(file, arcname=file.name)

    return archive_path


def add_to_list_file(filename, *items):
    with open(filename, 'a') as file:
        for item in items:
            file.write(item)
            file.write('\n')
    file.close()


def get_items_from_file(filename):
    if Path(filename).exists():
        with open(filename, 'r') as file:
            lines = [line.rstrip('\n') for line in file]
        file.close()

        return lines

    else:
        return []


def get_items_from_json(filename):
    if Path(filename).exists():
        with open('data.json') as json_file:
            data = json.load(json_file)

        return data


def save_items_as_json(data, path, filename="data.json"):
    file = Path(filename)
    json_object = json.dumps(data, indent=4)
    filepath = path/file
    with open(filepath, "w") as outfile:
        outfile.write(json_object)

    return file
