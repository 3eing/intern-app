import tempfile
import unittest
from pathlib import Path

from docx import Document

from app.utils.File import render_document
from app.dev_app.tools import _clean_project_text

ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT_DIR / "doc-templates" / "WBG Factsheet.docx"

PROJECTS_DATA = [
    {
        "Bailleur de fond": "MCC",
        "CV 2": ["recw5wwB5KSg5WC5G"],
        "Cat\u00e9gorie": ["R\u00e9seau \u00c9lectrique", "Analyse de donn\u00e9es"],
        "Client": ["WSP"],
        "Compagnie": ["recQDFxAiiBTwWD6j"],
        "Contacts": [
            "Josianne Pusterla\nDirection du service maritime\n+1 418 559-6646 \njosianne.pusterla@wsp.com"
        ],
        "Contexte_en": "Access to electricity has been one of the main obstacles to economic growth in Senegal for several years. The current strategy to expand this access needs support to optimize it.\n\nIn this context, the Millennium Challenge Corporation funded a project named 'Compact' to identify and prepare projects and strategies to optimize Senegal's electrical network in the areas of production, transmission, and distribution. The work of 3E Ing. consisted of completing the distribution part of this project.\n",
        "Contexte_fr": "L'acc\u00e8s \u00e0 \u00e9lectricit\u00e9 constitue un des principaux obstacles \u00e0 la croissance \u00e9conomique au S\u00e9n\u00e9gal depuis plusieurs ann\u00e9es. La strat\u00e9gie actuelle pour \u00e9largir cet acc\u00e8s a besoin d'un soutien afin de l'optimiser. \n\nDans cette optique, Millennium Challenge Corporation a financ\u00e9 un projet nomm\u00e9 \u00ab Compact \u00bb pour identifier et pr\u00e9parer des projets ainsi que des strat\u00e9gies afin d'optimiser le r\u00e9seau \u00e9lectrique du S\u00e9n\u00e9gal dans les domaines de la production, du transport et de la distribution. Le travail de 3E Ing. consistait \u00e0 compl\u00e9ter la partie distribution de ce projet.  ",
        "Cr\u00e9\u00e9 par": {
            "email": "l.letac@3eing.ca",
            "id": "usrpUygzISsfp5aXp",
            "name": "Loup Letac",
        },
        "Description_en": "The technical experts from 3E Ing. carried out the following tasks on the distribution network outside Dakar:\n\u2022 Correction of the network database (DB);\n\u2022 Integration of the DB into the Cymdist simulation software;\n\u2022 Integration and evaluation of the load of already planned projects, excluding 'Compact' projects, for the years 2017 to 2022;\n\u2022 Network simulation and identification of solutions regarding the following aspects:\n  o Correction of overloads and under-voltages;\n  o Improvement of service continuity;\n  o Reduction of technical losses;\n  o Strengthening of network planning activities.\n\u2022 Preparation of three technical reports to present the following elements:\n  o Simulation approach and project identification process;\n  o List of identified projects;\n  o Budget and implementation timelines.\n\u2022 Preparation of a technical report to identify best practices for cost-effective rural electrification;\n\u2022 Preparation of a technical report to identify the resources required to strengthen the distribution network planning activities.\n",
        "Description_fr": "Les experts techniques de 3E Ing. ont r\u00e9alis\u00e9 les t\u00e2ches suivantes, sur le r\u00e9seau de distribution hors Dakar :\n\u2022\tCorrection de la base de donn\u00e9es (BD) de r\u00e9seau;\n\u2022\tInt\u00e9gration de la BD au logiciel de simulation Cymdist;\n\u2022\tInt\u00e9gration et \u00e9valuation de la charge des projets d\u00e9j\u00e0 pr\u00e9vus, hors \u00ab Compact \u00bb pour les ann\u00e9es 2017 \u00e0 2022;\n\u2022\tSimulation du r\u00e9seau et identification des solutions concernant les aspects suivants :\no\tCorrection des surcharges et des sous-tensions;\no\tAm\u00e9lioration de la continuit\u00e9 du service;\no\tR\u00e9duction des pertes techniques;\no\tRenforcement de l'activit\u00e9 planification du r\u00e9seau.\n\u2022\tR\u00e9daction de trois rapports techniques pour pr\u00e9senter les \u00e9l\u00e9ments suivants :\no\tD\u00e9marche de simulation et d'identification des projets;\no\tListe des projets identifi\u00e9s;\no\tBudget et \u00e9ch\u00e9anciers de r\u00e9alisation.\n\u2022\tR\u00e9daction d'un rapport technique pour identifier les meilleures pratiques en mati\u00e8re de r\u00e9seau \u00e0 moindre co\u00fbt pour l'\u00e9lectrification rurale;\n\u2022\tR\u00e9daction d'un rapport technique pour identifier les ressources requises pour le renforcement de l'activit\u00e9 de planification du r\u00e9seau de distribution.",
        "Devise": "USD",
        "Dur\u00e9e (mois)": 3.37925,
        "Dur\u00e9e (mois) - calcul par valeur": 3.37925,
        "D\u00e9but": "2018-06-01",
        "Expert technique": ["Jean-Pierre Laflamme", "Pierre-Luc Laflamme", "Gabriel Boivin"],
        "Fin": "2018-09-01",
        "ID": "rec0Fy1TzU2DVzGxl",
        "Leader": ["Jean-Pierre Laflamme"],
        "Nombre de ressources": 3,
        "Num\u00e9ro": "18-217",
        "Pays": ["S\u00e9n\u00e9gal"],
        "Personnes": ["Jean-Pierre Laflamme", "Pierre-Luc Laflamme", "Gabriel Boivin"],
        "Taux horaire": 100,
        "Titre du projet": "\u00c9tude de renforcement du r\u00e9seau de distribution du S\u00e9n\u00e9gal",
        "Valeur": 47704.92,
        "Valeur totale": 2900000,
        "client_address": "",
        "client_name": ["WSP"],
        "mois-personne": 1.1264166666666666,
        "title_en": "Study of the reinforcement of the distribution network in Senegal",
    },
    {
        "Bailleur de fond": "Banque Mondiale",
        "CV 2": ["recw5wwB5KSg5WC5G"],
        "Cat\u00e9gorie": ["Analyse de donn\u00e9es", "R\u00e9seau \u00c9lectrique", "Efficacit\u00e9 \u00e9nerg\u00e9tique"],
        "Client": ["Tetra Tech"],
        "Compagnie": ["recQDFxAiiBTwWD6j"],
        "Contacts": [
            "Ronnie Murphy\nChef de projet Afrique de l'ouest\n+1 514 219-3925\nronniemurphy1000@hotmail.com, Ronnie.Murphy@tetratech.com"
        ],
        "Contexte_en": "The Soci\u00e9t\u00e9 Tunisienne de l'\u00c9lectricit\u00e9 et du Gaz (STEG) faces a significant financial challenge due to deteriorating technical and commercial performance, increased fraud (electricity consumed but not billed), and low collection rates. Technical and commercial losses reached 18% in 2017, and collection losses were at 21%. As a result, STEG has been experiencing negative net income since 2010.\n\nIn response to this situation, STEG signed a performance contract with the government for the period 2016-2020, committing to improve its technical, commercial, and financial performance and to sustain achievements to ensure its financial viability.\n",
        "Contexte_fr": "La Soci\u00e9t\u00e9 tunisienne de l'\u00e9lectricit\u00e9 et du gaz (STEG) est confront\u00e9e \u00e0 un d\u00e9fi financier important en raison de la d\u00e9gradation des performances techniques et commerciales, de la fraude accrue (\u00e9lectricit\u00e9 consomm\u00e9e mais non factur\u00e9e) et du faible taux de recouvrement. Les pertes techniques et commerciales ont atteint 18% en 2017 et les pertes de recouvrement 21%. En cons\u00e9quence, la STEG souffre d'un b\u00e9n\u00e9fice net n\u00e9gatif depuis 2010.  \n\nEn r\u00e9ponse \u00e0 cette situation, la STEG a sign\u00e9 avec le gouvernement un contrat de performance pour la p\u00e9riode 2016-2020, dans lequel elle s'engageait \u00e0 am\u00e9liorer ses performances technique, commerciale et financi\u00e8re et \u00e0 p\u00e9renniser les r\u00e9alisations pour assurer sa viabilit\u00e9 financi\u00e8re. ",
        "Cr\u00e9\u00e9 par": {
            "email": "l.letac@3eing.ca",
            "id": "usrpUygzISsfp5aXp",
            "name": "Loup Letac",
        },
        "Description_en": "3E Ing. was commissioned to conduct a diagnostic of the electricity distribution network and design a detailed master plan to help STEG achieve the objectives of its performance contract. The mission focused on reducing technical and commercial losses. The technical experts from 3E Ing. carried out the following tasks:\n\u2022 Correction of the network database (DB);\n\u2022 Integration of the DB into the Cymdist simulation software;\n\u2022 Simulation of the distribution network;\n\u2022 Calculation of technical losses in the medium and low voltage networks;\n\u2022 Identification of solutions to correct network issues and reduce losses;\n\u2022 Preparation of a technical report to:\n  o Explain the simulation approach;\n  o Identify the encountered problems;\n  o Define the calculation of medium and low voltage distribution losses.\n",
        "Description_fr": "3E Ing. a \u00e9t\u00e9 mandat\u00e9 afin de r\u00e9aliser un diagnostic du r\u00e9seau de distribution de l'\u00e9lectricit\u00e9 et la conception d'un plan directeur d\u00e9taill\u00e9  pour aider la STEG \u00e0 atteindre les objectifs de son contrat de performance. La mission \u00e9tait ax\u00e9e sur la r\u00e9duction des pertes techniques et commerciales. Les experts techniques de 3E Ing. ont r\u00e9alis\u00e9 les t\u00e2ches suivantes :\n\u2022\tCorrection de la base de donn\u00e9es (BD) du r\u00e9seau;\n\u2022\tInt\u00e9gration de la BD au logiciel de simulation Cymdist;\n\u2022\tSimulation du r\u00e9seau de distribution;\n\u2022\tCalcul des pertes techniques des r\u00e9seaux MT et BT;\n\u2022\tIdentification des solutions pour correction des probl\u00e9matiques de r\u00e9seau et pour r\u00e9duction des pertes;\n\u2022\tR\u00e9daction d'un rapport technique pour :\no\tExpliquer la d\u00e9marche de simulation;\no\tL'identification des probl\u00e8mes encourus;\no\tD\u00e9finir le calcul des pertes de distribution de moyenne et de basse tension.",
        "Devise": "USD",
        "Dur\u00e9e (mois)": 10,
        "Dur\u00e9e (mois) - calcul par valeur": 3.75,
        "D\u00e9but": "2018-11-01",
        "Expert technique": [
            "Jean-Pierre Laflamme",
            "Pierre-Yves Renaud",
            "Pierre-Luc Laflamme",
            "Gabriel Boivin",
        ],
        "Fin": "2019-08-01",
        "ID": "recr4R8aTKg46SNA1",
        "Leader": ["Jean-Pierre Laflamme"],
        "Nombre de ressources": 4,
        "Num\u00e9ro": "18-232",
        "Pays": ["Tunisie"],
        "Personnes": [
            "Jean-Pierre Laflamme",
            "Pierre-Yves Renaud",
            "Pierre-Luc Laflamme",
            "Gabriel Boivin",
        ],
        "Taux horaire": 100,
        "Titre du projet": "\u00c9tude du calcul de perte du r\u00e9seau de distribution de la Tunisie",
        "Valeur": 51926.61,
        "Valeur totale": 164434279.75,
        "client_address": "",
        "client_name": ["Tetra Tech"],
        "mois-personne": 0.9375,
        "title_en": "Study of loss calculation in Tunisia's distribution network",
    },
]


class RenderTemplateTest(unittest.TestCase):
    def test_render_wbg_factsheet_template(self):
        self.assertTrue(TEMPLATE_PATH.exists(), f"Template introuvable: {TEMPLATE_PATH}")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "rendered-wbg-factsheet.docx"

            cleaned_data = list(map(_clean_project_text, PROJECTS_DATA))

            rendered_path = render_document(
                template_path=TEMPLATE_PATH,
                doc_path=output_path,
                projects=cleaned_data,
                persons=[],
            )

            self.assertEqual(Path(rendered_path), output_path)
            self.assertTrue(output_path.exists(), "Le document rendu n'a pas ete cree")
            self.assertGreater(output_path.stat().st_size, 0, "Le document rendu est vide")

            document = Document(output_path)
            self.assertIsNotNone(document)


if __name__ == "__main__":
    unittest.main()
