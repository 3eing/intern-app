import os
import secrets

from flask import Flask

from apps.web.paths import AppPaths
from modules.shared.infrastructure.filesystem import create_dir_if_dont_exist


def load_config(app: Flask) -> None:
    env = os.environ.get("FLASK_ENV", "dev").lower()

    if env == "prod":
        app.config.from_object("config.prod")
    elif env == "test":
        app.config.from_object("config.test")
    else:
        app.config.from_object("config.dev")

    if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] == "change-me":
        app.config["SECRET_KEY"] = secrets.token_hex(32)


def build_paths(app: Flask) -> None:
    app.extensions["paths"] = AppPaths(root=app.config["ROOT_DIR"])


def ensure_storage_dirs(app: Flask) -> None:
    paths: AppPaths = app.extensions["paths"]

    for path in [
        paths.uploads,
        paths.generated,
        paths.eep_uploads,
        paths.linepole_uploads,
        paths.dev_uploads,
        paths.dev_template_tmp,
        paths.dev_generated,
        paths.dev_docs_output,
    ]:
        create_dir_if_dont_exist(path)


def register_blueprints(app: Flask) -> None:
    from apps.web.routes import web_bp
    app.register_blueprint(web_bp)


def create_app() -> Flask:
    app = Flask(__name__)

    load_config(app)
    build_paths(app)
    ensure_storage_dirs(app)
    register_blueprints(app)

    return app