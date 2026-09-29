from pandas import ExcelWriter
from pathlib import Path
from re import search
import json
from modules.eepower.domain.services import group_by_scenario, pire_cas
from modules.eepower.infrastructure.parsers import (
    simple_af_report,
    simple_cc_report,
    simple_ed_report,
    simple_tcc_reports,
)


CC_XL_FILE_NAME = 'eep-cc-output.xlsx'
CC_TEX_FILE_NAME = "tab_cc.tex"
AF_XL_FILE_NAME = 'eep-af-output.xlsx'
AF_TEX_FILE_NAME = "tab_af.tex"
ED_XL_FILE_NAME = 'eep-ed-output.xlsx'
ED_TEX_FILE_NAME = "tab_ed.tex"
FUSE_XL_FILE_NAME = 'eep-fuse-output.xlsx'
FUSE_TEX_FILE_NAME = "tab_fuse.tex"
SST_XL_FILE_NAME = 'eep-sst-output.xlsx'
SST_TEX_FILE_NAME = "tab_sst.tex"
MT_XL_FILE_NAME = 'eep-mt-output.xlsx'
MT_TEX_FILE_NAME = "tab_mt.tex"

root = Path(__file__).parent
tex_ref_file = root / "config" / "tex_ref.json"

with open(tex_ref_file, encoding='utf-8') as file:
    TEX_REF = json.loads(file.read())


def report_tcc(data, target_rep):
    """
    Generate a xlsx and latex report for Equipment Duty
    :param data: a dictionary that contains all information for the processs
    :type data: dict
    :param data["BUS_EXCLUS"]: list of string patern to exclude form the analysis
    :type data["BUS_EXCLUS"]: list of str
    :param data["FILE_PATHS"]: list of path to the files
    :type data["FILE_PATHS"]: list of str
    :param data["FILE_NAME"]: list of name of the files
    :type data["FILE_NAME"]: list of str
    :param target_rep: the path to the target path
    :type target_rep: str
    :return: a path to the directory and the name of generated file
    :rtype: tuple of path
    """

    xl_output_paths = [Path(target_rep).joinpath(FUSE_XL_FILE_NAME),
                      Path(target_rep).joinpath(SST_XL_FILE_NAME),
                      Path(target_rep).joinpath(MT_XL_FILE_NAME)]
    tex_output_paths = [Path(target_rep).joinpath(FUSE_TEX_FILE_NAME),
                        Path(target_rep).joinpath(SST_TEX_FILE_NAME),
                        Path(target_rep).joinpath(MT_TEX_FILE_NAME)]

    try:
        f = [f for f in data["FILES"] if "tcc_coordination" in f.name.lower()][0]
        reports = simple_tcc_reports(str(f), bus_excluded=data["BUS_EXCLUS"])
    except IndexError:
        raise FileNotFoundError("Aucun fichier de réglages de protections")

    for report_name, report in reports.items():
        try:
            idx = 0
            if report_name == 'fuse':
                idx = 0
            elif report_name == 'magnetothermique':
                idx = 1
            elif report_name == 'electronique':
                    idx = 2
            else:
                raise ValueError("report_name n'a pas la bonne valeurs : {0}".format(report_name))

            with ExcelWriter(xl_output_paths[idx], engine="openpyxl") as writer:
                report.to_excel(writer)
                df_to_tabularay(report, tex_output_paths[idx], type=report_name)

        except PermissionError:
            raise PermissionError("Le fichier choisis est déjà ouvert ou vous n'avez pas la permission de l'écrire")
        except ValueError:
            raise ValueError

    output = [file for file in xl_output_paths] + [file for file in tex_output_paths]
    return output


def report_ed(data, target_rep):
    """
    Generate a xlsx and latex report for Equipment Duty
    :param data: a dictionary that contains all information for the processs
    :type data: dict
    :param data["BUS_EXCLUS"]: list of string patern to exclude form the analysis
    :type data["BUS_EXCLUS"]: list of str
    :param data["FILE_PATHS"]: list of path to the files
    :type data["FILE_PATHS"]: list of str
    :param data["FILE_NAME"]: list of name of the files
    :type data["FILE_NAME"]: list of str
    :param target_rep: the path to the target path
    :type target_rep: str
    :return: a path to the directory and the name of generated file
    :rtype: tuple of path
    """

    xl_output_path = Path(target_rep).joinpath(ED_XL_FILE_NAME)
    tex_output_path = Path(target_rep).joinpath(ED_TEX_FILE_NAME)
    try:
        f = [f for f in data["FILES"] if "equipment_duty" in f.name.lower()][0]
        report = simple_ed_report(str(f), bus_excluded=data["BUS_EXCLUS"])
    except IndexError:
        raise FileNotFoundError("Aucun fichier de capacité d'équipement")

    try:
        with ExcelWriter(xl_output_path, engine="openpyxl") as writer:
            report.to_excel(writer)
            df_to_tabularay(report, tex_output_path, type='ed')
            # on retourne le repertoire et le fichier séparément
        return xl_output_path, tex_output_path

    except PermissionError:
        raise PermissionError("Le fichier choisis est déjà ouvert ou vous n'avez pas la permission de l'écrire")
    except ValueError:
        raise ValueError


def report_af(data, target_rep):
    """
    Generate a xlsx and latex report for arc-flash
    :param data: a dictionary that contains all information for the processs
    :type data: dict
    :param data["BUS_EXCLUS"]: list of string patern to exclude form the analysis
    :type data["BUS_EXCLUS"]: list of str
    :param data["FILE_PATHS"]: list of path to the files
    :type data["FILE_PATHS"]: list of str
    :param data["FILE_NAME"]: list of name of the files
    :type data["FILE_NAME"]: list of str
    :param target_rep: the path to the target path
    :type target_rep: str
    :return: a path to the directory and the name of generated file
    :rtype: tuple of path
    """

    xl_output_path = Path(target_rep).joinpath(AF_XL_FILE_NAME)
    tex_output_path = Path(target_rep).joinpath(AF_TEX_FILE_NAME)
    try:
        f = [f for f in data["FILES"] if "arc_flash_scenario_report" in f.name.lower()][0]
        report = simple_af_report(str(f), bus_excluded=data["BUS_EXCLUS"])
    except IndexError:
        raise FileNotFoundError("Aucun fichier de niveau d'arc-flash")

    try:
        with ExcelWriter(xl_output_path, engine="openpyxl") as writer:
            report.to_excel(writer)
            df_to_tabularay(report, tex_output_path, type='af')
            # on retourne le repertoire et le fichier séparément
        return xl_output_path, tex_output_path

    except PermissionError:
        raise PermissionError("Le fichier choisis est déjà ouvert ou vous n'avez pas la permission de l'écrire")
    except ValueError:
        raise ValueError


def report_cc(data, target_rep):
    """
    Generate a xlsx report for short-circuit
    :param data: a dictionary that contains all information for the processs
    :type data: dict
    :param data["BUS_EXCLUS"]: list of string patern to exclude form the analysis
    :type data["BUS_EXCLUS"]: list of str
    :param data["FILE_PATHS"]: list of path to the files
    :type data["FILE_PATHS"]: list of str
    :param data["FILE"]: list of name of the files
    :type data["FILE"]: list of str
    :param data["NB_SCEN"]: number of scenario
    :type data["NB_SCEN"]: list of str
    :param target_rep: the path to the target path
    :type target_rep: str
    :return: a path to the directory and the name of generated file
    :rtype: tuple of path
    """
    reports = []
    hv = None
    xl_output_path = Path(target_rep)/CC_XL_FILE_NAME
    tex_output_path = Path(target_rep)/CC_TEX_FILE_NAME

    scenarios = data["SCENARIOS"]

    for scenario in scenarios:
        group = group_by_scenario(data["FILES"], scenario)
        file30, file1, _type = None, None, None
        for file in group:
            if '30_Cycle_Report' in file.name or '30 Cycle' in file.name:
                file30 = file
            elif 'LV' in file.name or 'LM' in file.name:
                file1 = file
            elif 'HV' in file.name:
                hv = file
            if '.csv' in file.suffix:
                _type = 'csv'
            elif '.xls' in file.suffix:
                _type = 'xlsx'

        if not _type:
            raise FileNotFoundError("Les fichiers doivent être au format csv ou xlsx")
        elif not file1 or not file30:
            raise FileNotFoundError("Il faut au moins un fichier 30s et un fichier instantané")

        tmp_report = simple_cc_report(str(file30), str(file1), hv=hv, typefile=_type, bus_excluded=data["BUS_EXCLUS"])
        reports.append(tmp_report)

    pire_cas_rap = pire_cas(reports, scenarios)

    try:
        with ExcelWriter(xl_output_path, engine="openpyxl") as writer:
            pire_cas_rap.to_excel(writer, sheet_name='Pire Cas')
            df_to_tabularay(pire_cas_rap, tex_output_path)

            for scenario in scenarios:
                i = scenarios.index(scenario)
                reports[i].to_excel(writer, sheet_name=('Scénario {0}'.format(scenario)))
            # on retourne le repertoire et le fichier séparément
        return xl_output_path, tex_output_path

    except PermissionError:
        raise PermissionError("Le fichier choisis est déjà ouvert ou vous n'avez pas la permission de l'écrire")
    except ValueError:
        raise ValueError


def df_to_tabularay(df, filepath, type='cc'):
    """
    Gives a tabularray table instead of the normal to_latex()
    :param df: DataFrame
    :return:
    """
    # todo: changer ce comportement une fois solution trouvé
    #  (voir SO: https://stackoverflow.com/questions/76781323/dataframe-to-latex-create-a-multilevel-header-in-latex-when-the-index-have-a-nam)
    df.index.name, df.index.names = None, [None]

    if type in ("fuse", "electronique", "magnetothermique"):
        df = df.droplevel(0, axis=1)

    styled_df = df.fillna(' ').style \
        .format_index("\\textbf{{{}}}", escape="latex") \
        .format(precision=1, escape="latex")

    if type not in ("fuse", "electronique", "magnetothermique"):
        styled_df.format(precision=0, subset=["Bus (V)"])

    if type == "af":
        styled_df.format("\\colorcell{{{}}}", subset=["Niveau d'énergie (Cal/cm²)"])
    latex_df = styled_df.to_latex()
    match = search(r"(?<=\\)(\n.+)+(?=\\\\\n\\end)", latex_df)
    isolated_table = match.group()

    header = TEX_REF[type]['header']
    footer = TEX_REF[type]['footer']

    table = header + isolated_table + footer

    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(table)

    return filepath

