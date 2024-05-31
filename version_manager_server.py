# save this as app.py
import os
import requests
from flask import Flask, request

app = Flask(__name__)
rollup_server = os.environ.get('ROLLUP_HTTP_SERVER_URL')

input_data = None


@app.route("/notice", methods=["POST"])
def notice():
    data = request.get_json()
    requests.post(rollup_server + "/notice", json=data)

@app.route("/voucher", methods=["POST"])
def voucher():
    data = request.get_json()
    requests.post(rollup_server + "/voucher", json=data)

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    requests.post(rollup_server + "/report", json=data)


@app.route("/input", methods=["POST"])
def input():
    global input_data
    input_data = request.get_json()
    
    return {}

@app.route("/finish")
def finish():
    global input_data
    if input_data:
        return input_data

    input_data = None
    data = request.get_json()
    requests.post(rollup_server + "/finish", json=data)
