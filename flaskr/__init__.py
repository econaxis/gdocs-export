from flask import Flask
from flaskr.flask_config import CONF


def create_flask_serv():
    flask_serv = Flask(__name__)
    flask_serv.config.from_object(CONF)

    from flaskr.auth_blueprint import auth_bp
    from flaskr.server_bp import server
    from flaskr.dashapp import register_dashapp

    register_dashapp(flask_serv)

    flask_serv.register_blueprint(auth_bp)
    flask_serv.register_blueprint(server)
    flask_serv.run(debug = True);
    return flask_serv


if __name__ == '__main__':
    create_flask_serv()
