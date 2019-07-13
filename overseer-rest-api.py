#!/usr/bin/python

from flask import Flask
from flask import request

import overseer
import os
import json

app = Flask(__name__)


@app.route('/active')
def active():
    return json.dumps(os.listdir(overseer.path_status))


@app.route('/enable')
def enable():
    act_name = request.args.get("activity")

    response = {"success": False, "error": ""}

    if not overseer.is_daemon_running():
        response["error"] = overseer.exit_codes["daemon_not_running"][1]
        return json.dumps(response)

    if not overseer.activity_exists(act_name):
        response["error"] = "Activity does not exist!"
        return json.dumps(response)

    overseer.link_enable(act_name)
    overseer.remote_bump()
    response["success"] = True
    return json.dumps(response)


@app.route('/disable')
def disable():
    act_name = request.args.get("activity")

    response = {"success": False, "error": ""}

    if not overseer.is_daemon_running():
        response["error"] = overseer.exit_codes["daemon_not_running"][1]
        return json.dumps(response)

    if not overseer.activity_exists(act_name):
        response["error"] = "Activity does not exist!"
        return json.dumps(response)

    overseer.link_disable(act_name)
    overseer.remote_bump()
    response["success"] = True
    return json.dumps(response)


if __name__ == '__main__':
    port = int(os.getenv('OVERSEER_API_PORT', "8989"))
    host = os.getenv('OVERSEER_API_HOST', "0.0.0.0")

    app.run(debug=True, port=port, host=host)