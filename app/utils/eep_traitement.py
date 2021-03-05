from .eepower_utils import simple_report, group_by_scenario, pire_cas
from pandas import ExcelWriter
from os.path import join

FILE_NAME = 'eep-output.xlsx'

def report(data,target):
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
    :param target: the path to the target path
    :type target: str
    :return: a path to the directory and the name of generated file
    :rtype: tuple of path
    """
    reports = []
    output_path = join(target, FILE_NAME)
    writer = ExcelWriter(output_path)
    scenarios = list(range(1,data["NB_SCEN"]+1))
    for scenario in scenarios:
        group = group_by_scenario(data["FILE_PATHS"], data["FILE_NAME"], scenario)
        for path, name in group:
            if '30 Cycle Report' in name:
                file30 = path
            if 'LM' in name:
                file1 = path
            if '.csv' in path:
                _type = 'csv'
            else:
                if not '.xlsx':
                    if '.xls' in path:
                        _type = 'xlsx'

        reports.append(simple_report(file30, file1, typefile=_type, bus_excluded=data["BUS_EXCLUS"]))

    pire_cas_rap = pire_cas(reports, scenarios)

    try:
        pire_cas_rap.to_excel(writer, sheet_name='Pire Cas')
        for i in scenarios:
            reports[(i - 1)].to_excel(writer, sheet_name=('Scénario {0}'.format(i)))
        writer.save()
        #on retourne le repertoire et le fichier séparément
        return target, FILE_NAME

    except PermissionError:
        print("Le fichier choisis est déjà ouvert ou vous n'avez pas la permission de l'écrire")
        return -1
    except ValueError:
        return -1
