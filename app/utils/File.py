import re
import pandas as pd
import openpyxl
import os
import json
import zipfile
from pathlib import Path
from docxtpl import DocxTemplate

from app.eep.eepower_utils import parse_excel_sheet


class FileError(Exception):
    pass


def get_uploads_files(upload_dir=r'.\uploads'):
    upload_dir = Path(upload_dir)
    if upload_dir.exists() and upload_dir.is_dir():
        return [child for child in upload_dir.iterdir()]
    else:
        print("Directory ", upload_dir.name, " doesn't exist")
        return []


def purge_file(dir_name=Path(r'.\uploads')):
    if get_uploads_files(dir_name) != []:
        for file in get_uploads_files(dir_name):
            file.unlink()


def validate_file_epow(file):
    """

    :param file: Path (pathlib) to the file to validate
    :return: The type of file it is for the study, None is not valitated
    """
    file_names_patern = {
        "cc": "(?i)(.*LM|.*LV.Momentary)|(.*30.Cycle)",
        "af": "(?i)Arc.Flash",
        "ed": "(?i)Equipment.Duty",
        "tcc": "(?i)TCC.coordination"
    }
    col30 = {'Bus kV', 'Sym Amps'}
    col1 = {"Bus kV", "Sym Amps", "X/R Ratio", "Mult Factor", "Asym Amps", "Equip Type", "Duty Amps"}
    af_col = {"Arc Fault Bus Name",
              "Worst Case Scenario",
              "Arc Fault Bus kV",
              "Fault Type",
              "Upstream Trip Device Name",
              "Bus Bolted Fault (kA)",
              "Bus Arc Fault (kA)",
              "Trip Time (sec)",
              "Arc Time (sec)",
              "Limited Approach Boundary (m)",
              "Restricted Approach Boundary (m)",
              "Working Distance (m)",
              "Incident Energy\n(cal/cm2)"}
    ed_col = {
        "Equipment\nName",
        "Worst Case Scenario",
        "Fault\nType",
        "Bus Base\nkV",
        "Manufacturer",
        "Style",
        "Test\nStandard",
        "1/2 Cycle\nRating\n(kA)",
        "1/2 Cycle\nDuty\n(kA)",
        "1/2 Cycle\nDuty\n(%)",
        "Comments"
    }
    tcc_col = {
        "Fuse",
        "SST",
        "Thermal Magnetic Breaker"
    }

    if re.match(file_names_patern['cc'], file.name):
        try:
            df = pd.DataFrame(pd.read_csv(file, skiprows=1))
        except:
            try:
                df = pd.DataFrame(pd.read_excel(file, skiprows=7, engine='openpyxl'))
            except openpyxl.utils.exceptions.InvalidFileException as notXL:
                raise FileError("Le type de fichiers n'est pas .xlsx")

        if col1.issubset(df.columns.to_list()) or col30.issubset(df.columns.to_list()):
            return "CC"
        else:
            missing_col = col30 + col1 - set(df.columns.to_list())
            raise FileError(
                "Les colonnes {0} du fichier '{1}' semblent être manquantes ou mal écrite dans les fichiers "
                "fournis".format(missing_col, file)
            )

    elif re.match(file_names_patern['af'], file.name):
        try:
            df = pd.DataFrame(pd.read_excel(file, engine='openpyxl'))
        except openpyxl.utils.exceptions.InvalidFileException as notXL:
            raise FileError("Le type de fichiers n'est pas .xlsx")
        if af_col.issubset(df.columns.to_list()):
            return "AF"
        else:
            missing_col = af_col - set(df.columns.to_list())
            raise FileError(
                "Les colonnes {0} du fichier '{1}' semblent être manquantes ou mal écrite dans les fichiers "
                "fournis".format(missing_col, file)
            )
        
    elif re.match(file_names_patern['ed'],  file.name):
        try:
            df = pd.DataFrame(pd.read_excel(file, engine='openpyxl'))
        except openpyxl.utils.exceptions.InvalidFileException as notXL:
            raise FileError("Le type de fichiers n'est pas .xlsx")
        if ed_col.issubset(df.columns.to_list()):
            return "ED"
        else:
            missing_col = ed_col - set(df.columns.to_list())
            raise FileError(
                "Les colonnes {0} du fichier '{1}' semblent être manquantes ou mal écrite dans les fichiers "
                "fournis".format(missing_col, file.name)
            )

    elif re.match(file_names_patern['tcc'], file.name):
        try:
            df_tcc = parse_excel_sheet(file, header=[0, 1])
            df = df_tcc[0]
            if set.intersection(tcc_col, df.columns.to_list()[0]) != set():
                return "TCC"
            else:
                missing_col = ("infos manquantes")
                raise FileError(
                    "Les colonnes {0} du fichier '{1}' semblent être manquantes ou mal écrite dans les fichiers "
                    "fournis".format(missing_col, file.name)
                )
        except openpyxl.utils.exceptions.InvalidFileException:
            raise FileError("Le type de fichiers n'est pas .xlsx")
        except BaseException:
            raise FileError("Impossible de déterminer les fins et le débuts des tableaux des protections")

    else:
        raise FileError(
            "Le fichier '{0}' ne semblent pas être un fichier géré par cet outil".format(file.name))


def full_paths(upload_dir):
    return upload_dir / "*"


def create_dir_if_dont_exist(dir_name):
    Path(dir_name).mkdir(parents=True, exist_ok=True)
    return Path(dir_name)


def zip_files(list_of_files, zip_file_name=''):
    """
    Generate a zip file from a list of files in the location of the first file of the list
    :param list_of_files:
    :type list_of_files:
    :param zip_file_name:
    :type zip_file_name:
    :return:
    :rtype:
    """

    if zip_file_name == '':
        file_name = list_of_files[0].parent

    # the current working directory is changed to the directory of the first file in the list
    # return to the previous directory after saving
    previous_dir = Path.cwd()
    wd = list_of_files[0].parent
    os.chdir(wd)
    zip_file_name += '.zip'
    with zipfile.ZipFile(zip_file_name,
                         "w",
                         zipfile.ZIP_DEFLATED,
                         allowZip64=True) as zf:
        for file in list_of_files:
            zf.write(file.name)

    zippath = wd/zip_file_name
    os.chdir(previous_dir)
    return zippath


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


def render_document(template_path, doc_path, projects, person):
    """
    Generate a docx file from a template
    :param template_path: path to the template file
    :type template_path: str
    :param doc_path: filepath where to save the document
    :type doc_path: str
    :param projects: all the projects to include in the document
    :type projects: list[dict]
    :return: filename of the document
    :rtype: str
    """
    create_dir_if_dont_exist(doc_path.parent)
    doc = DocxTemplate(template_path)
    context = {'projects': projects, 'person': person}
    doc.render(context)
    doc.save(doc_path)

    return doc_path


