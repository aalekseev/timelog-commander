from tinydb import TinyDB
from flask import Flask, render_template

app = Flask(__name__)
db = TinyDB("db.json")


@app.route("/", methods=["GET"])
def app_homepage():
    return render_template("app.html")
