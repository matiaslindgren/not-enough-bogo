import flask
app = flask.Flask(__name__)

@app.route("/")
def hi(name=None):
    return flask.render_template('main.html', name=name)


