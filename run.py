from flaskr import create_flask_serv


app = create_flask_serv()

if __name__ == '__main__':
    app = create_flask_serv().run(debug = True)
