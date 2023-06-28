from .eepower_utils import simple_report, group_by_scenario, pire_cas
from pandas import ExcelWriter
from pathlib import Path
from re import search
import json

XL_FILE_NAME = 'eep-output.xlsx'
TEX_FILE_NAME = "tab_cc.tex"
tex_ref_file = Path(r"app/static/config/tex_ref.json")
with open(tex_ref_file, encoding='utf-8') as file:
    TEX_REF = json.loads(file.read())


def report(data, target_rep):
    """
    Generate a xlsx report for easy power
    :param data: a dictionary that contains all information for the processs
    :type data: dict
    :param data["BUS_EXCLUS"]: list of string patern to exclude form the analysis
    :type data["BUS_EXCLUS"]: list of str
    :param data["FILE_PATHS"]: list of path to the files
    :type data["FILE_PATHS"]: list of str
    :param data["FILE_NAME"]: list of name of the files
    :type data["FILE_NAME"]: list of str
    :param data["NB_SCEN"]: number of scenario
    :type data["NB_SCEN"]: list of str
    :param target_rep: the path to the target path
    :type target_rep: str
    :return: a path to the directory and the name of generated file
    :rtype: tuple of path
    """
    reports = []
    hv = None
    xl_output_path = Path(target_rep).joinpath(XL_FILE_NAME)
    tex_output_path = Path(target_rep).joinpath(TEX_FILE_NAME)


    scenarios = data["SCENARIOS"]

    for scenario in scenarios:
        group = group_by_scenario(data["FILE_PATHS"], data["FILE_NAMES"], scenario)
        file30, file1, _type = None, None, None
        for path, name in group:
            if '30_Cycle_Report' in name or '30 Cycle' in name:
                file30 = path
            elif 'LV' in name or 'LM' in name:
                file1 = path
            elif 'HV' in name:
                hv = path
            if '.csv' in path:
                _type = 'csv'
            elif '.xls' in path:
                _type = 'xlsx'

        if not _type:
            raise FileNotFoundError("Les fichiers doivent être au format csv ou xlsx")
        elif not file1 or not file30:
            raise FileNotFoundError("Il faut au moins un fichier 30s et un fichier instantané")

        tmp_report = simple_report(file30, file1, hv=hv, typefile=_type, bus_excluded=data["BUS_EXCLUS"])
        reports.append(tmp_report)

    pire_cas_rap = pire_cas(reports, scenarios)

    try:
        with ExcelWriter(xl_output_path, engine="openpyxl") as writer:
            pire_cas_rap.to_excel(writer, sheet_name='Pire Cas')
            latex_table_filepath = df_to_tabularay(pire_cas_rap, tex_output_path)

            for scenario in scenarios:
                i = scenarios.index(scenario)
                reports[i].to_excel(writer, sheet_name=('Scénario {0}'.format(scenario)))
            # on retourne le repertoire et le fichier séparément
        return xl_output_path, latex_table_filepath

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
    styled_df = df.style \
        .format_index("\\textbf{{{}}}", escape="latex") \
        .format(precision=1) \
        .format(precision=0, subset=["Bus V"])

    if type == "af":
        styled_df.format("\\\colorcell{{{}}}", escape="latex", subset=df.iloc[-1])
    latex_df = styled_df.to_latex()
    match = search(r"(?<=\\)(\n.+)+(?=\\\\\n\\end)", latex_df)
    isolated_table = match.group()

    header = TEX_REF[type]['header']
    footer = TEX_REF[type]['footer']

    table = header + isolated_table + footer

    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(table)

    return filepath
