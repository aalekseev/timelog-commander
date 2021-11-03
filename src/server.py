from tinydb import TinyDB, Query
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
db = TinyDB("db.json")


@app.route("/", methods=["GET"])
def app_homepage():
    return render_template("app.html")


@app.route("/api/projects", methods=["GET"])
def projects():
    return jsonify([
        {"id": 1, "key": "KP", "name": "Krah-Pipes", "defaultTask": {"key": "KP-1", "summary": "Project Management"}},
        {"id": 2, "key": "MLV", "name": "My Learn View", "defaultTask": {"key": "MLV-1", "summary": "Project Management"}},
        {"id": 3, "key": "TTT", "name": "Thunder's Truck Team", "defaultTask": {"key": "TTT-19", "summary": "Misc Time"}},
    ])


@app.route('/api/tasks/<project_key>', methods=["GET"])
def project_tasks(project_key):
    kp_tasks = [
        {"id": 1, "key": "KP-1", "summary": "Project Management"},
        {"id": 2, "key": "KP-22", "summary": "Implementation Task"},
    ]
    mlv_tasks = [
        {"id": 1, "key": "MLV-54", "summary": "Project Management"},
        {"id": 2, "key": "MLV-12", "summary": "Implementation Task"},
    ]
    mapping = {
        'KP': kp_tasks,
        'MLV': mlv_tasks,
    }
    query = request.args.get('q')
    if query:
        return jsonify(tuple(filter(lambda o: query in o['key'], mapping[project_key])))
    return jsonify(mapping[project_key])


@app.route('/api/record', methods=["POST"])
def record():
    data = request.get_json()
    table = db.table('records')
    table.insert(data)
    return {"status": "ok"}


@app.route('/api/records', methods=["GET"])
def records():
    table = db.table('records')
    return jsonify(table.all())


@app.route('/api/settings/jira', methods=["GET", "POST"])
def jira_settings():
    table = db.table('settings')
    Settings = Query
    rec = table.upsert({'connection': 'jira'}, Settings.connection == 'jira')
    return rec
