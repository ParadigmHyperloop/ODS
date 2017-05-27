import os
from flask import Flask, g, jsonify, current_app, request, send_from_directory
from flask import redirect

app = Flask(__name__)
_ods = None
_pod = None

WEB_ROOT = os.environ.get('WEB_ROOT', '../web/src')
DATA_SERVICES = os.path.realpath(os.path.join(__file__, '../../data_services'))


def get_ods():
    """Returns the ODS server"""
    return _ods


def set_ods(ods_server):
    """Tells flask where the ODS Server class is"""
    global _ods
    _ods = ods_server


def get_pod():
    """Returns the ORCS Server class"""
    return _pod


def set_pod(pod):
    """Tells flask where the ORCS Server class is"""
    global _pod
    _pod = pod


def send_path(path):
    if os.path.isdir(path):
        path = os.path.join(path, 'index.html')

    if os.path.exists(path):
        return send_from_directory(os.path.dirname(path),
                                   os.path.basename(path))
    else:
        return jsonify({"msg": "{} does not exist".format(path)})


@app.route("/ui/", defaults={'path': ''})
@app.route("/ui/<path:path>")
def ui(path):
    path = os.path.normpath(os.path.join(os.getcwd(), WEB_ROOT, path))
    return send_path(path)

@app.route("/")
def index():
    return redirect('/ui/')


@app.route("/state")
def state():
    return jsonify(get_ods().get_state())


@app.route("/sensors")
def sensors():
    path = os.path.join(DATA_SERVICES, "sensors.json")
    return send_path(path)


@app.route("/commands/<command>", methods=['POST'])
def command(command):
    argv = [command]

    data = request.get_json()
    if data and 'args' in data:
        argv.extend(data['args'])

    data = None
    try:
        data = get_pod().run(' '.join(argv))
    finally:
        return jsonify({
            "status": "failed" if data is None else "ok",
            "argv": argv,
            "msg": data
        })
