from apps.web import create_app


intern_app = create_app()


if __name__ == "__main__":
    with intern_app.app_context():
        intern_app.run(port=8080)
