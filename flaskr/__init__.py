from flask import Flask
from flaskr.flask_config import CONF, cache


def create_flask_serv():
    flask_serv = Flask(__name__)
    flask_serv.config.from_object(CONF)

    cache.init_app(flask_serv)
    cache.clear()

    from flaskr.auth_blueprint import auth_bp
    from flaskr.server_bp import server
    from flaskr.dashapp import register_dashapp

    register_dashapp(flask_serv)

    import os

    if "FLASKDBG" not in os.environ or True:
        flask_serv.register_blueprint(auth_bp)
        flask_serv.register_blueprint(server)

    return flask_serv


'''
if __name__ == '__main__':
    create_flask_serv()
'''
