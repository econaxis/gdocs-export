from flask import Flask
from flask_config import CONF


def create_app():
    app = Flask(__name__)
    app.config.from_object(CONF)

    from auth_blueprint import auth_bp
    from server_bp import server

    app.register_blueprint(auth_bp)
    app.register_blueprint(server)
    app.run(debug = True);
    return app


if __name__ == '__main__':
    create_app()

