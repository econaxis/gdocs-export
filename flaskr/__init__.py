from flask import Flask
from flaskr.flask_config import CONF


def create_flask_serv():
    flask_serv = Flask(__name__)
    flask_serv.config.from_object(CONF)
    print(1)

    from flaskr.auth_blueprint import auth_bp
    from flaskr.server_bp import server
    from flaskr.dashapp import register_dashapp
    print(2)
    register_dashapp(flask_serv)
    print(3)
    flask_serv.register_blueprint(auth_bp)
    flask_serv.register_blueprint(server)
    print(4)

    print("returning flask_serv")
    return flask_serv

'''
if __name__ == '__main__':
    create_flask_serv()
'''


