from pathlib import Path
from uuid import uuid4
from tempfile import TemporaryDirectory
from flask import Blueprint, current_app, flash, get_flashed_messages, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from modules.shared.infrastructure.filesystem import (
    create_dir_if_dont_exist,
    get_uploads_files,
    purge_file,
    zip_files,
)
from app.utils.File import add_to_list_file, get_items_from_file
from modules.eepower.application.process_reports import generate_reports
from modules.eepower.domain.services import scenario_finder
from modules.eepower.infrastructure.file_validation import REPORT_FORMATS, identify_report_type, validate_file_epow, validate_report_filename
from modules.shared.infrastructure.error_handlers import FileError


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
    scenarios = scenario_finder(files)
    return {
        "BUS_EXCLUS": get_items_from_file(_buses_file()),
        "FILE_PATHS": _upload_dir() / "*",
        "FILES": files,
        "SCENARIOS": scenarios,
        "NB_SCEN": len(scenarios),
        "REPORT_TYPE": _report_types(),
    }


def _flash_upload_error(filename: str, message: str) -> None:
    report_type = identify_report_type(filename)
    if report_type is None:
        flash(message, "error")
    else:
        flash({"report_type": report_type, "filename": filename, "error": message}, "upload_error")


@eepower_bp.route('/eepower', methods=['GET', 'POST'])
def eepower():
    uploaded_files = get_uploads_files(_upload_dir())
    if request.method == 'POST':
        # ajout de fichier pour analyse
        if request.form['btn_id'] == 'soumettre_fichier':
            submitted_files = [f for f in request.files.getlist('file') if f.filename]
            if not submitted_files:
                flash("Sélectionnez au moins un fichier à envoyer.", "warning")
            for uploaded_file in submitted_files:
                filename = secure_filename(uploaded_file.filename)
                if not filename:
                    flash("Nom de fichier invalide.", "error")
                    continue
                try:
                    validate_report_filename(filename)
                    upload_dir = _upload_dir()
                    # Stage outside the directory containing accepted files.
                    with TemporaryDirectory(prefix=".eepower-", dir=upload_dir.parent) as staging:
                        staged_file = Path(staging) / filename
                        uploaded_file.save(staged_file)
                        report_type = validate_file_epow(staged_file)
                        staged_file.replace(upload_dir / filename)
                    _add_report_type(report_type)
                except FileError as error:
                    _flash_upload_error(filename, str(error))
                except OSError:
                    current_app.logger.exception("Échec de stockage du fichier %s", filename)
                    _flash_upload_error(filename, f"Impossible de lire ou d'enregistrer '{filename}'. Réessayez ou contactez l'administrateur.")
                except Exception:
                    current_app.logger.exception("Erreur inattendue pendant l'import de %s", filename)
                    _flash_upload_error(filename, f"Erreur interne pendant l'import de '{filename}'. Contactez l'administrateur.")

            return redirect(url_for('.eepower'))

        elif request.form['btn_id'] == 'purger':
            return redirect(url_for('.purge'))

        elif request.form['btn_id'] == 'suivant':
            return redirect(url_for('.eepower_traitement'))

    report_files = {kind: [] for kind in REPORT_FORMATS}
    for file in uploaded_files:
        report_type = identify_report_type(file)
        if report_type is not None:
            report_files[report_type].append({"filename": file.name, "error": None})
    messages = []
    for category, message in get_flashed_messages(with_categories=True):
        if category == "upload_error":
            report_files[message["report_type"]].append(message)
        else:
            messages.append((category, message))
    return render_template('eepower/easy_power.html', uploaded_files=uploaded_files,
                           report_formats=REPORT_FORMATS, report_files=report_files, messages=messages)


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
                file_list = generate_reports(eep_data, dirpath)
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
