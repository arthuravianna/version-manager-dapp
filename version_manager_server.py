# save this as app.py
import os
import requests
from flask import Flask, request, make_response, jsonify

app = Flask(__name__)
rollup_server = os.environ.get('ROLLUP_HTTP_SERVER_URL')

input_data = None
processing_input = False
result = None


@app.route("/notice", methods=["POST"])
def notice():
    data = request.get_json()
    res = requests.post(rollup_server + "/notice", json=data)
    return make_response(res.text, res.status_code)

@app.route("/voucher", methods=["POST"])
def voucher():
    data = request.get_json()
    res = requests.post(rollup_server + "/voucher", json=data)
    return make_response(res.text, res.status_code)

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    res = requests.post(rollup_server + "/report", json=data)
    return make_response(res.text, res.status_code)


@app.route("/input", methods=["POST"])
def input():
    global input_data, result
    input_data = request.get_json()
    result = None
    
    return {}

@app.route("/finish", methods=['POST'])
def finish():
    global input_data, processing_input, result
    
    # not processing and has input
    if not processing_input and input_data:
        processing_input = True
        return input_data

    # processing and has input = processing finished
    elif input_data:
        processing_input = False
        input_data = None

        data = request.get_json()
        result = data["status"]

        #res = requests.post(rollup_server + "/finish", json=data)
        #return make_response(res.text, res.status_code)
    

    return make_response("no rollup request available", 202)

@app.route("/result")
def result():
    if result is None:
        return jsonify(result=None)
    
    status = True if result == "accept" else False
    return jsonify(result=status)