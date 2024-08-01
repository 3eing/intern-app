# -*- coding: utf-8 -*-
import os
import pathlib
import secrets

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename

from .linepole import settings as kml_settings
from .linepole.KMLHandler import KMLHandler
from .eep import eepower_utils as eeu, eep_traitement as eep

from .utils.File import validate_file_epow as validate, get_uploads_files, purge_file, full_paths, \
    create_dir_if_dont_exist as create_dir, zip_files, add_to_list_file, get_items_from_file, \
    FileError


def create_app():
    app = Flask(__name__)

    app.secret_key = secrets.token_bytes()

    app.config['ROOT_DIR'] = pathlib.Path(__file__).parent.parent

    app.config['MAX_CONTENT_LENGTH'] = 3072 * 3072
    app.config['UPLOAD_EXTENSIONS'] = ['.csv', '.xlsx', '.xls']

    app.config['UPLOAD_PATH'] = create_dir(app.config['ROOT_DIR']/'uploads')

    app.config['UPLOAD_PATH_EPOW'] = create_dir(app.config['UPLOAD_PATH']/'eepower')

    app.config['UPLOAD_PATH_LP'] = create_dir(app.config['UPLOAD_PATH']/'linepole_generator')
    app.config['GENERATED_PATH'] = create_dir(app.config['ROOT_DIR']/'generated')
    app.config['CURRENT_OUTPUT_FILE'] = ''

    app.config['MAX_XP'] = 3
    app.config['MAX_SLAN'] = 2
    app.config['MAX_DEGREES'] = 2

    app.config['UPLOAD_PATH_DEV'] = create_dir(app.config['UPLOAD_PATH']/'developpement')
    app.config['DEV_TEMPLATE_DOC'] = app.config['UPLOAD_PATH_DEV'] / 'templates'
    app.config['GENERATED_DEV_DOC_PATH'] = app.config['GENERATED_PATH'] / 'developpement'

    BUSES_FILE = os.path.join(app.config['UPLOAD_PATH_EPOW'], r'bus_exclus')
    EEP_DATA = {"BUS_EXCLUS": get_items_from_file(BUSES_FILE),
                "FILE_PATHS": [],
                "FILES": [],
                "SCENARIOS": [],
                "NB_SCEN": 0,
                "REPORT_TYPE": []}

    with app.app_context():
        from app.dev_app.AirTableAPI import airtable_api
        app.register_blueprint(airtable_api)

    @app.route('/')
    def index():
        return render_template('accueil.html')


    @app.route('/eepower', methods=['GET', 'POST'])
    def eepower():
        uploaded_files = get_uploads_files(app.config['UPLOAD_PATH_EPOW'])
        if request.method == 'POST':
            # ajout de fichier pour analyse
            if request.form['btn_id'] == 'soumettre_fichier':
                error_messages = []
                submittted_files = request.files.getlist('file')
                for uploaded_file in submittted_files:
                    file = pathlib.Path(secure_filename(uploaded_file.filename))
                    if file.name != '':
                        # valide si l'extension des fichiers est bonne
                        if file.suffix not in app.config['UPLOAD_EXTENSIONS']:
                            flash("Les fichiers reçus ne sont des fichiers .csv ou .xlsx", 'error')
                        path_to_file = pathlib.Path(app.config['UPLOAD_PATH_EPOW']) / file
                        uploaded_file.save(path_to_file)
                        # valide en ouvrant les fichiers si le contenu est bon
                        try:

                            EEP_DATA["REPORT_TYPE"].append(validate(path_to_file))
                        except FileError as e:
                            os.remove(path_to_file)
                            error_messages.append("{0}".format(e))

                flash("\n".join(error_messages), 'warning')
                return redirect(url_for('eepower'))

            elif request.form['btn_id'] == 'purger':
                return redirect(url_for('purge', app_name='eepower'))

            elif request.form['btn_id'] == 'suivant':
                return redirect(url_for('eepower_traitement'))

        return render_template('easy_power.html', uploaded_files=uploaded_files)


    @app.route('/eepower-2', methods=['GET', 'POST'])
    def eepower_traitement():
        app_name = 'eepower'
        try:
            EEP_DATA["FILES"] = get_uploads_files(app.config['UPLOAD_PATH_EPOW'])
            EEP_DATA["FILE_PATHS"] = full_paths(app.config['UPLOAD_PATH_EPOW'])
            EEP_DATA["SCENARIOS"] = eeu.scenario_finder(EEP_DATA["FILES"])
            EEP_DATA["NB_SCEN"] = len(EEP_DATA["SCENARIOS"])
        except(AttributeError):
            flash("Problème avec les regex", 'error')
            EEP_DATA["FILES"] = []
            return redirect(url_for('eepower_traitement'))
        file_ready = 0


        if request.method == 'POST':
            if request.form['btn_id'] == 'ajouter_bus':
                if request.form['bus'] != '':
                    add_to_list_file(BUSES_FILE, str.upper(request.form['bus']))
                    EEP_DATA["BUS_EXCLUS"] = get_items_from_file(BUSES_FILE)
                    render_template('easy_power_traitement.html', nb_scen=EEP_DATA["NB_SCEN"],
                                    bus_exclus=EEP_DATA["BUS_EXCLUS"],
                                    file_ready=1)

            elif request.form['btn_id'] == 'suivant':
                try:
                    dirpath = create_dir(app.config['GENERATED_PATH']/'eepower')
                except FileNotFoundError:
                    flash("Problème lors de la création du répertoire", 'error')
                    return render_template('easy_power_traitement.html', nb_scen=EEP_DATA["NB_SCEN"],
                                           bus_exclus=EEP_DATA["BUS_EXCLUS"],
                                           file_ready=file_ready)
                try:
                    file_list = []
                    if "CC" in EEP_DATA["REPORT_TYPE"]:
                        file_list += eep.report_cc(EEP_DATA, dirpath)
                    if "AF" in EEP_DATA["REPORT_TYPE"]:
                        file_list += eep.report_af(EEP_DATA, dirpath)
                    if "ED" in EEP_DATA["REPORT_TYPE"]:
                        file_list += eep.report_ed(EEP_DATA, dirpath)
                    if "TCC" in EEP_DATA["REPORT_TYPE"]:
                        file_list += eep.report_tcc(EEP_DATA, dirpath)
                    if file_list == []:
                        flash("Pas de fichiers fournis", 'error')
                        return render_template('easy_power_traitement.html', nb_scen=EEP_DATA["NB_SCEN"],
                                               bus_exclus=EEP_DATA["BUS_EXCLUS"],
                                               file_ready=file_ready)
                    app.config['CURRENT_OUTPUT_FILE'] = pathlib.Path(zip_files(file_list, zip_file_name=app_name + '_result'))

                except FileNotFoundError as e:
                    flash(e, 'error')
                    return render_template('easy_power_traitement.html', nb_scen=EEP_DATA["NB_SCEN"],
                                           bus_exclus=EEP_DATA["BUS_EXCLUS"],
                                           file_ready=file_ready)


                return render_template('easy_power_traitement.html', nb_scen=EEP_DATA["NB_SCEN"],
                                       bus_exclus=EEP_DATA["BUS_EXCLUS"],
                                       file_ready=1)

            elif request.form['btn_id'] == 'retour':
                return redirect(url_for('eepower'))

            elif request.form['btn_id'] == 'telecharger':
                return redirect(url_for('download', app_name=app_name, filename=app.config['CURRENT_OUTPUT_FILE'].name))

            elif request.form['btn_id'] == 'terminer':
                return redirect(url_for('purge', app_name=app_name))

        return render_template('easy_power_traitement.html', nb_scen=EEP_DATA["NB_SCEN"], bus_exclus=EEP_DATA["BUS_EXCLUS"],
                               file_ready=file_ready)


    @app.route('/linepole_generator', methods=['GET', 'POST'])
    def linepole_generator():
        app_name = 'linepole_generator'
        uploaded_files = get_uploads_files(app.config['UPLOAD_PATH_LP'])
        output_path = create_dir(os.path.join(app.config['GENERATED_PATH'], app_name))

        if request.method == 'POST':
            # ajout de fichier pour analyse
            if request.form['btn_id'] == 'soumettre_fichier':
                file = request.files['file']
                filename = secure_filename(file.filename)

                if filename != '':
                    file_ext = os.path.splitext(filename)[1]
                    # valide si l'extension des fichier est bonne
                    if file_ext != '.kml':
                        flash("Le fichier reçu n'est pas un fichier .kml", 'error')

                    file.save(os.path.join(app.config['UPLOAD_PATH_LP'], filename))
                    return redirect(url_for('linepole_generator', uploaded_files=uploaded_files, file_ready=0))

                return redirect(url_for('linepole_generator', uploaded_files=uploaded_files, file_ready=0, file_submit=1))

            elif request.form['btn_id'] == 'analyze':
                global handle
                kml_settings.init()
                handle = KMLHandler(os.path.join(app.config["UPLOAD_PATH_LP"], uploaded_files[0]))
                return render_template('linepole.html', uploaded_files=uploaded_files, file_ready=0, file_submit=1,
                                       loader=0, pole=0, parallele=0)

            elif request.form['btn_id'] == 'pole':
                kml_settings.space_by_type['custom'] = request.form.get('dist_pole', type=int)
                handle.generatePoles()
                handle.generateOutput()

                # create the kml with poles
                kml_file_name = os.path.join(output_path, "augmented_kml.kml")
                kml_file = open(kml_file_name, "w+")
                kml_file.write(repr(handle))
                kml_file.close()

                # create a csv in the camelia format
                camelia = handle.camelia
                cam_file_name = os.path.join(output_path, "camelia_output.csv")
                camelia.to_csv(cam_file_name)

                # generate a csv containing all generated data
                csv_name = os.path.join(output_path, "all_data.csv")
                handle.outputdf.to_csv(csv_name)

                outputs = [kml_file_name, cam_file_name, csv_name]

                app.config['CURRENT_OUTPUT_FILE'] = pathlib.Path(zip_files(outputs, zip_file_name=app_name + '_result'))
                return render_template('linepole.html', uploaded_files=uploaded_files, file_ready=1, file_submit=1,
                                       pole=1, parallele=0)

            elif request.form['btn_id'] == 'parallele':
                offset = request.form.get('dist_line', type=int)
                max_dist = request.form.get('dist_max_line', type=int)

                handle.generateOffset(offset, max_dist)
                handle.generateOutput()

                # create the kml with poles
                kml_file_name = os.path.join(output_path, "augmented_kml.kml")
                kml_file = open(kml_file_name, "w+")
                kml_file.write(repr(handle))
                kml_file.close()

                # generate a csv containing all generated data
                csv_name = os.path.join(output_path, "all_data.csv")
                handle.outputdf.to_csv(csv_name)

                outputs = [kml_file_name, csv_name]

                app.config['CURRENT_OUTPUT_FILE'] = pathlib.Path(zip_files(outputs, zip_file_name=app_name + '_result'))
                return render_template('linepole.html', uploaded_files=uploaded_files, file_ready=1, file_submit=1,
                                       pole=0, parallele=1)

            elif request.form['btn_id'] == 'purger':
                return redirect(url_for('purge', app_name=app_name, file_submit=0))

            elif request.form['btn_id'] == 'telecharger':
                return redirect(url_for('download', app_name=app_name, filename=app.config['CURRENT_OUTPUT_FILE'].name))

            elif request.form['btn_id'] == 'terminer':
                return redirect(url_for('purge', app_name=app_name))

        return render_template('linepole.html', uploaded_files=uploaded_files, file_ready=0, file_submit=0, loader=0)

    @app.route('/download/<app_name>/<filename>/', methods=['GET', 'POST'])
    def download(app_name, filename):
        directory = pathlib.Path(app.config['GENERATED_PATH']/app_name).absolute()
        # filename = pathlib.Path(file).name
        return send_from_directory(directory=directory, path=filename,
                                   as_attachment=True)


    @app.route('/purge/<app_name>', methods=['GET', 'POST'])
    def purge(app_name):
        purge_file(os.path.join(app.config['UPLOAD_PATH'], app_name))
        purge_file(os.path.join(app.config['GENERATED_PATH'], app_name))
        EEP_DATA = {"BUS_EXCLUS": [],
                    "FILE_PATHS": [],
                    "FILE": [],
                    "SCENARIOS": [],
                    "NB_SCEN": 0}
        return redirect(url_for(app_name))


    @app.errorhandler(Exception)
    def basic_error(e):
        return "an error occured: " + str(e)


    return app

