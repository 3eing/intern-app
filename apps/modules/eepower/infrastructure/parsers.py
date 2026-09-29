import pandas as pd
from math import sqrt
import re
import numpy as np
from pathlib import Path

SCEN_PATERN = r"(?i)(lv|lm|hv|30_cycle_report).+(scen\D*)(\s*_*-*)(\d+\w{0,1})"


def parse_excel_sheet(file, sheet_name=0, header=0):
    """
    parses multiple tables from an excel sheet into multiple data frame objects. Returns [dfs, df_mds],
    where dfs is a list of data frames and df_mds their potential associated metadata
    from https://stackoverflow.com/questions/43367805/pandas-read-excel-multiple-tables-on-the-same-sheet
    """
    xl = pd.ExcelFile(file)
    try:
        entire_sheet = xl.parse(sheet_name=sheet_name)

        lines = np.logical_not(entire_sheet['TCC Coordination Report'].isnull())
        starts = []
        ends = []
        for line, value in lines.items():
            if line != 0:
                previous_value = lines[line-1]
            if line != len(lines) - 1:
                next_value = lines[line+1]
            if value and not previous_value:
                starts.append(line+1)
            elif value and not next_value:
                ends.append(line)
            elif value and line == len(lines) - 1:
                ends.append(line)

        if len(starts) < len(ends) or len(starts) > len(ends)+1:
            raise BaseException('Could not detect equal number of beginnings and ends')

        # make data frames
        dfs = []
        df_mds = []
        for ind in range(len(starts)):
            start = int(starts[ind])

            if ind < len(ends):
                stop = int(ends[ind] + 1)
            else:
                stop = int(entire_sheet.shape[0])
            df = xl.parse(sheet_name=sheet_name, skiprows=start, nrows=stop-start, header=header)
            dfs.append(df)
        xl.close()
        return dfs
    except BaseException as e:
        xl.close()
        raise e
    except Exception as e:
        xl.close()
        raise e


def simple_tcc_reports(rap_tcc, bus_excluded=None):
    """
    Créer un dataframe pandas avec les données nécessaires issues d'EasyPower:

    :param rap_af: rapport excel ou csv
    :type rap_af: str
    :param bus_excluded: liste des bus à ne pas inclure dans le tableau
    :type bus_excluded: list of str
    :return: un Dataframe Pandas contenant les informations nécessaire dans le tableau
    :rtype: pd.DataFrame
    """
    tables = {
        "fuse": pd.DataFrame(),
        "magnetothermique": pd.DataFrame(),
        "electronique": pd.DataFrame()
    }

    columns = {
        "fuse":{
            "Fuse": "Description",
            "ID": "Équip.",
            "Manufacturer": "Manufacturier",
            "Type": "Type",
            "Style": "Style",
            "Model": "Modèle",
            "kV": "V",
            "Size": "Calibre"
        },
        "electronique": {
            "SST": "Description",
            "LTPU": "Seuil long",
            "STPU": "Seuil court",
            "Inst": "Instantané",
            "ID": "Équip.",
            "Manufacturer": "Manuf.",
            "Type": "Type",
            "Style": "Style",
            "Frame/Sensor": "Format",
            "tap/plug": "entrée",
            "Setting": "Réglage",
            "Trip (A)": "Décl.(A)",
            "Band": "Délais (s)"
        },
        "magnetothermique": {
            "Thermal Magnetic Breaker": "Description",
            "Instantaneous": "Instantané",
            "ID": "Équip.",
            "Manufacturer": "Manuf.",
            "Type": "Type",
            "Style": "Style",
            "Frame": "Format",
            "Trip": "décl.",
            "Trip Adjust": "Ajust.",
            "Setting": "Réglage",
            "Trip (A)": "Décl.(A)",
        }
    }

    rapports = parse_excel_sheet(rap_tcc, header=[0, 1])
    for df in rapports:
        prim_cols = set([prim for prim, sec in df.columns.to_list()])
        sec_cols = set([sec for prim, sec in df.columns.to_list()])
        if "Fuse" in prim_cols or "Fuse" in sec_cols:
            tables["fuse"] = df.set_index(("Fuse", "ID"))
        elif "SST" in prim_cols or "SST" in sec_cols:
            tables["electronique"] = df.set_index(("SST", "ID"))
        elif "Thermal Magnetic Breaker" in prim_cols or "Thermal Magnetic Breaker" in sec_cols:
            tables["magnetothermique"] = df.set_index(("Thermal Magnetic Breaker", "ID"))

    for rapport_name, rapport_df in tables.items():

        # rapport_df = rapport_df.reset_index()
        rapport_df = rapport_df.rename(columns=columns[rapport_name])

        #on élimine les colonnes inutile
        column_to_keep = {v for k, v in columns[rapport_name].items()}
        column_existing = set(rapport_df.columns.get_level_values(1))
        column_to_drop = list(column_existing - column_to_keep)

        rapport_df = rapport_df.drop(column_to_drop, axis=1, level=1)
        if "ZSI" in rapport_df.columns.get_level_values(0):
            rapport_df = rapport_df.drop(["ZSI", "Ground Trip"], axis=1, level=0)

        if "V" in rapport_df.columns.get_level_values(1):
            rapport_df.loc[:,('Description','V')] = rapport_df['Description']['V'] * 1000

        tables[rapport_name] = rapport_df

    return tables


def simple_ed_report(rap_ed, bus_excluded=None):
    """
    Créer un dataframe pandas avec les données nécessaires issues d'EasyPower

    :param rap_af: rapport excel ou csv
    :type rap_af: str
    :param bus_excluded: liste des bus à ne pas inclure dans le tableau
    :type bus_excluded: list of str
    :return: un Dataframe Pandas contenant les informations nécessaire dans le tableau
    :rtype: pd.DataFrame
    """
    columns = {
        "Bus Name": "Bus",
        "Equipment\nName": "Équipement",
        "Fault\nType": "Type de défault",
        "Bus Base\nkV": "Bus (V)",
        "Manufacturer": "Manufacturier",
        "Style": "Style",
        "Test\nStandard": "Standard de test",
        "1/2 Cycle\nRating\n(kA)": "Capacité pour 1/2 cycle (kA)",
        "1/2 Cycle\nDuty\n(kA)": "Utilisation pour 1/2 cycle (kA)",
        "1/2 Cycle\nDuty\n(%)": "Utilisation pour 1/2 cycle (%)",
        "Comments": "Commentaires"
    }

    rapport = pd.DataFrame(pd.read_excel(rap_ed, index_col=1))

    if bus_excluded is not None and bus_excluded != []:
        try:
            rapport = rapport[~rapport.index.str.contains('|'.join(bus_excluded))]
        except Exception as e:
            raise ValueError

    rapport = rapport.rename(columns=columns)
    rapport.index.name = "Équipement"
    rapport['Bus'] = rapport['Bus'].ffill()
    rapport['Commentaires'].fillna(value='OK', inplace=True)
    rapport.sort_values(by=['Bus', 'Équipement'])

    #on élimine les colonnes inutile
    column_to_keep = {v for k, v in columns.items()}
    column_existing = set(rapport.columns.to_list())
    column_to_drop = list(column_existing - column_to_keep)

    rapport = rapport.drop(column_to_drop, axis=1)
    rapport['Bus (V)'] = rapport['Bus (V)'] * 1000

    rapport = rapport.sort_index(ascending=True)

    return rapport


def simple_af_report(rap_af, bus_excluded=None):
    """
    Créer un dataframe pandas avec les données nécessaires issues d'EasyPower:

        Équipement | Scénario | Bus (V) | Type de défault | Disjoncteur en amont | Courant de court circuit (kA) |
     Courant d'arc (kA) | Temps de déclenchement (s) | Temps de l'arc (s) | Périmètre de sécurité (m) |
     Distance d'accès limité (m) | Distance de travail (m) | Niveau d'énergie (Cal/cm²)
    :param rap_af: rapport excel ou csv
    :type rap_af: str
    :param bus_excluded: liste des bus à ne pas inclure dans le tableau
    :type bus_excluded: list of str
    :return: un Dataframe Pandas contenant les informations nécessaire dans le tableau
    :rtype: pd.DataFrame
    """
    columns = {
        "Arc Fault Bus Name": "Équipement",
        "Worst Case Scenario": "Scénario",
        "Arc Fault Bus kV": "Bus (V)",
        "Fault Type": "Type de défault",
        "Upstream Trip Device Name": "Disjoncteur en amont",
        "Bus Bolted Fault (kA)": "Courant de court circuit (kA)",
        "Bus Arc Fault (kA)": "Courant d'arc (kA)",
        "Trip Time (sec)": "Temps de déclenchement (s)",
        "Arc Time (sec)": "Temps de l'arc (s)",
        "Limited Approach Boundary (m)": "Périmètre de sécurité (m)",
        "Restricted Approach Boundary (m)": "Distance d'accès limité (m)",
        "Working Distance (m)": "Distance de travail (m)",
        "Incident Energy\n(cal/cm2)": "Niveau d'énergie (Cal/cm²)"
    }
    file_path = Path(rap_af)
    typefile = file_path.suffix
    if typefile == '.csv':
        rapport = pd.DataFrame(pd.read_csv(rap_af, index_col=0))
    elif typefile == '.xlsx':
        rapport = pd.DataFrame(pd.read_excel(rap_af, index_col=0))

    if bus_excluded is not None and bus_excluded != []:
        rapport = rapport[~rapport.index.str.contains('|'.join(bus_excluded))]

    rapport.dropna()

    rapport = rapport.rename(columns=columns)

    #on élimine les colonnes inutile
    column_to_keep = {v for k, v in columns.items()}
    column_existing = set(rapport.columns.to_list())
    column_to_drop = list(column_existing - column_to_keep)

    rapport = rapport.drop(column_to_drop, axis=1)
    rapport['Bus (V)'] = rapport['Bus (V)'] * 1000

    rapport = rapport.sort_values(by='Bus (V)', ascending=False)

    return rapport.dropna()


def simple_cc_report(rap_30, rap_1, hv=None, typefile='csv', bus_excluded=None):
    """
    Créer une dataframe pandas en groupant les information utile depuis les rapport 30 cycles et 1 cycle
    :param rap_30:
    :type rap_30:
    :param rap_1:
    :type rap_1:
    :param typefile:
    :type typefile:
    :return:
    :rtype:
    """
    bus_excluded = [str.upper(bus) for bus in bus_excluded]
    #ajouté pour être sûr de dropper les lignes voulues (easypower donne des noms en capitale)
    if typefile == 'csv':
        rapport_30cycles = pd.DataFrame(pd.read_csv(rap_30, skiprows=1, index_col=0))
        rapport_1cycle = pd.DataFrame(pd.read_csv(rap_1, skiprows=1, index_col=0))
    elif typefile == 'xlsx':
        rapport_30cycles = pd.DataFrame(pd.read_excel(rap_30, skiprows=7, index_col=0, engine='openpyxl'))
        rapport_1cycle = pd.DataFrame(pd.read_excel(rap_1, skiprows=7, index_col=0, engine='openpyxl'))

    if bus_excluded != None and bus_excluded != []:
        temp1 = rapport_1cycle[~rapport_1cycle.index.str.contains('|'.join(bus_excluded))]
        temp30 = rapport_30cycles[~rapport_30cycles.index.str.contains('|'.join(bus_excluded))]
    else:
        temp1 = rapport_1cycle
        temp30 = rapport_30cycles

    temp1.dropna()
    temp30.dropna()

    temp30 = temp30.rename(columns={'Sym Amps': 'I Sym 30'})
    rap = pd.concat([temp1, temp30['I Sym 30']], axis=1)

    #on élimine les colonnes inutile
    #on conserve 'Bus kV' car il est changé par la suite pour 'Bus (V)'
    column_to_keep = {'Bus kV', 'Sym Amps', 'X/R Ratio', 'Asym Amps', 'I Peak', 'I Sym 30'}
    column_existing = set(rap.columns.to_list())
    column_to_drop = list(column_existing - column_to_keep)

    rap = rap.drop(column_to_drop, axis=1)
    rap = rap.rename(columns={'Bus kV': 'Bus (V)'})
    rap['Bus (V)'] = rap['Bus (V)'] * 1000

    rap = rap.sort_values(by='Bus (V)', ascending=False)

    peak = pd.DataFrame(rap['Sym Amps'] * 2.6).round(1)
    rap.insert(4, '2,6*I Sym', peak)

    if hv:
        hv_report = simple_cc_report(rap_30, hv, hv=None, typefile=typefile, bus_excluded=bus_excluded)
        rap = pd.concat([rap, hv_report])
        rap = rap.sort_values(by='Bus (V)', ascending=False)

    return rap.dropna()


def group_by_scenario(file_list, scenario):
    """
    Make a list of tuple of the path of the file and the file name if it it's the same scenario that number provided
    :param file_list: list of the files to group
    :type file_list: Path
    :param scenario:
    :type scenario: int
    :return: list of pair (path, file name) for the scenario provided
    :rtype: list of tuple
    """
    grouped_files = []
    for file in file_list:
        if scen_num_finder(file) == scenario:
            grouped_files.append(file)

    return grouped_files


def scen_num_finder(file):
    m = re.search(SCEN_PATERN, file.name)
    if m:
        return m.groups()[-1]
    else:
        return None


def scenario_finder(file_names):
    scen_list = []
    for name in file_names:
        num = scen_num_finder(name)
        if num:
            if num not in scen_list:
                scen_list.append(num)

    return scen_list


def pire_cas(reports, scenarios):
    pire_cas = pd.concat(reports, keys=scenarios, names=["Scénario", None])
    pire_cas = pire_cas.loc[pire_cas.groupby(level=1)['Asym Amps'].idxmax()]
    pire_cas = pire_cas.sort_values(by='Bus (V)', ascending=False)
    pire_cas = pire_cas.reset_index("Scénario")
    return pire_cas

