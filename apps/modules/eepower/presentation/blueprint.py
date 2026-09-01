from pathlib import Path
from uuid import uuid4
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from modules.shared.infrastructure.filesystem import (
    create_dir_if_dont_exist,
    get_uploads_files,
    purge_file,
    zip_files,
)
from app.utils.File import add_to_list_file, get_items_from_file, validate_file_epow
from modules.shared.infrastructure.error_handlers import FileError
from app.eep import eepower_utils as eeu, eep_traitement as eep


EEP_SESSION_KEY = "eepower"


eepower_bp = Blueprint(
    "eepower",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/eepower/static",
)


def _paths():
    return current_app.extensions["paths"]


def _workspace_id() -> str:
    state = dict(session.get(EEP_SESSION_KEY, {}))
    workspace_id = state.get("workspace_id")
    if workspace_id is None:
        workspace_id = uuid4().hex
        state["workspace_id"] = workspace_id
        session[EEP_SESSION_KEY] = state
    return workspace_id


def _upload_dir() -> Path:
    return create_dir_if_dont_exist(_paths().eep_uploads / _workspace_id())


def _generated_dir() -> Path:
    return create_dir_if_dont_exist(_paths().generated / "eepower" / _workspace_id())


def _buses_file() -> Path:
    return _paths().eep_uploads / "bus_exclus"


def _report_types() -> list[str]:
    return list(session.get(EEP_SESSION_KEY, {}).get("report_types", []))


def _add_report_type(report_type: str) -> None:
    state = dict(session.get(EEP_SESSION_KEY, {}))
    report_types = list(state.get("report_types", []))
    if report_type not in report_types:
        report_types.append(report_type)
    state["report_types"] = report_types
    session[EEP_SESSION_KEY] = state


def _set_output_filename(output_path: Path) -> None:
    state = dict(session.get(EEP_SESSION_KEY, {}))
    state["output_filename"] = output_path.name
    session[EEP_SESSION_KEY] = state


def _output_filename() -> str | None:
    return session.get(EEP_SESSION_KEY, {}).get("output_filename")


def _build_eep_data() -> dict:
    """Build request-specific data; only small user state lives in the session."""
    files = get_uploads_files(_upload_dir())
    scenarios = eeu.scenario_finder(files)
    return {
        "BUS_EXCLUS": get_items_from_file(_buses_file()),
        "FILE_PATHS": _upload_dir() / "*",
        "FILES": files,
        "SCENARIOS": scenarios,
        "NB_SCEN": len(scenarios),
        "REPORT_TYPE": _report_types(),
    }


@eepower_bp.route('/eepower', methods=['GET', 'POST'])
def eepower():
    uploaded_files = get_uploads_files(_upload_dir())
    if request.method == 'POST':
        # ajout de fichier pour analyse
        if request.form['btn_id'] == 'soumettre_fichier':
            error_messages = []
            submitted_files = request.files.getlist('file')
            for uploaded_file in submitted_files:
                file = Path(secure_filename(uploaded_file.filename))
                if file.name != '':
                    # valide si l'extension des fichiers est bonne
                    if file.suffix not in current_app.config["UPLOAD_EXTENSIONS"]:
                        flash("Les fichiers reçus ne sont des fichiers .csv ou .xlsx", 'error')
                    path_to_file = _upload_dir() / file
                    uploaded_file.save(path_to_file)
                    # valide en ouvrant les fichiers si le contenu est bon
                    try:

                        _add_report_type(validate_file_epow(path_to_file))
                    except FileError as e:
                        Path.unlink(path_to_file)
                        error_messages.append("{0}".format(e))

            flash("\n".join(error_messages), 'warning')
            return redirect(url_for('.eepower'))

        elif request.form['btn_id'] == 'purger':
            return redirect(url_for('.purge'))

        elif request.form['btn_id'] == 'suivant':
            return redirect(url_for('.eepower_traitement'))

    return render_template('eepower/easy_power.html', uploaded_files=uploaded_files)


@eepower_bp.route('/eepower-2', methods=['GET', 'POST'])
def eepower_traitement():
    app_name = 'eepower'
    try:
        eep_data = _build_eep_data()
    except AttributeError:
        flash("Problème avec les regex", 'error')
        return redirect(url_for('.eepower_traitement'))
    file_ready = 0

    if request.method == 'POST':
        if request.form['btn_id'] == 'ajouter_bus':
            if request.form['bus'] != '':
                add_to_list_file(_buses_file(), str.upper(request.form['bus']))
                eep_data["BUS_EXCLUS"] = get_items_from_file(_buses_file())
                render_template('eepower/easy_power_traitement.html', nb_scen=eep_data["NB_SCEN"],
                                bus_exclus=eep_data["BUS_EXCLUS"],
                                file_ready=1)

        elif request.form['btn_id'] == 'suivant':
            try:
                dirpath = _generated_dir()
            except FileNotFoundError:
                flash("Problème lors de la création du répertoire", 'error')
                return render_template('eepower/easy_power_traitement.html', nb_scen=eep_data["NB_SCEN"],
                                       bus_exclus=eep_data["BUS_EXCLUS"],
                                       file_ready=file_ready)
            try:
                file_list = []
                if "CC" in eep_data["REPORT_TYPE"]:
                    file_list += eep.report_cc(eep_data, dirpath)
                if "AF" in eep_data["REPORT_TYPE"]:
                    file_list += eep.report_af(eep_data, dirpath)
                if "ED" in eep_data["REPORT_TYPE"]:
                    file_list += eep.report_ed(eep_data, dirpath)
                if "TCC" in eep_data["REPORT_TYPE"]:
                    file_list += eep.report_tcc(eep_data, dirpath)
                if not file_list:
                    flash("Pas de fichiers fournis", 'error')
                    return render_template('eepower/easy_power_traitement.html', nb_scen=eep_data["NB_SCEN"],
                                           bus_exclus=eep_data["BUS_EXCLUS"],
                                           file_ready=file_ready)
                _set_output_filename(zip_files(file_list, zip_file_name=app_name + '_result'))

            except FileNotFoundError as e:
                flash(e, 'error')
                return render_template('eepower/easy_power_traitement.html', nb_scen=eep_data["NB_SCEN"],
                                       bus_exclus=eep_data["BUS_EXCLUS"],
                                       file_ready=file_ready)

            return render_template('eepower/easy_power_traitement.html', nb_scen=eep_data["NB_SCEN"],
                                   bus_exclus=eep_data["BUS_EXCLUS"],
                                   file_ready=1)

        elif request.form['btn_id'] == 'retour':
            return redirect(url_for('.eepower'))

        elif request.form['btn_id'] == 'telecharger':
            output_filename = _output_filename()
            if output_filename is None:
                flash("Aucun fichier n'est disponible au tÃ©lÃ©chargement", 'error')
                return redirect(url_for('.eepower_traitement'))
            return redirect(url_for('.download'))

        elif request.form['btn_id'] == 'terminer':
            return redirect(url_for('.purge'))

    return render_template('eepower/easy_power_traitement.html', nb_scen=eep_data["NB_SCEN"], bus_exclus=eep_data["BUS_EXCLUS"],
                           file_ready=file_ready)


@eepower_bp.get('/eepower/download')
def download():
    output_filename = _output_filename()
    if output_filename is None:
        flash("Aucun fichier disponible au telechargement", "error")
        return redirect(url_for(".eepower_traitement"))

    return send_from_directory(_generated_dir(), output_filename, as_attachment=True)


@eepower_bp.get('/eepower/purge')
@eepower_bp.post('/eepower/purge')
def purge():
    purge_file(_upload_dir())
    purge_file(_generated_dir())
    session.pop(EEP_SESSION_KEY, None)
    return redirect(url_for(".eepower"))
