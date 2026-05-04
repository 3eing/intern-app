from flask import Blueprint, render_template

web_bp = Blueprint("web", __name__)


@web_bp.errorhandler(Exception)
def basic_error(e):
    return "an error occured: " + str(e)