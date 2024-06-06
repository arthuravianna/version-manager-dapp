import logging
import os
import subprocess
import json
import base64
import requests
import signal
import threading
import datetime

from flask import Flask, request, make_response

app = Flask(__name__)

input_data = None
processing_input = False
result = None
rollup_server = os.environ["ROLLUP_HTTP_SERVER_URL"]
dapp_initialzied = False


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


@app.route("/finish", methods=['POST'])
def finish():
    global input_data, processing_input, result, dapp_initialzied

    if not dapp_initialzied: dapp_initialzied = True
    
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
    

    return make_response("no rollup request available", 202)


logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)
forwarded = False

# load version manager conf
version_manager = None
with open("version_manager.conf.json", "r") as f:
    version_manager = json.load(f)
    for i in range(len(version_manager["DEVELOPERS"])):
        version_manager["DEVELOPERS"][i] = version_manager["DEVELOPERS"][i].lower()


child_dapp_process = None

# utility functions
def str2hex(str):
    """Encodes a string as a hex string"""
    return "0x" + str.encode("utf-8").hex()

def hex2str(hex):
    """Decodes a hex string into a regular string"""
    return bytes.fromhex(hex[2:]).decode("utf-8")


def post(endpoint, json):
    response = requests.post(f"{rollup_server}/{endpoint}", json=json)
    logger.info(f"Received {endpoint} status {response.status_code} body {response.content}")


def run_cmd(cmd, shell=False):
    output = subprocess.run(cmd, capture_output=True, shell=shell)
    return output.stdout.decode("utf-8")


def is_developer(msg_sender):
    developers = version_manager.get("DEVELOPERS")
    if developers and not msg_sender.lower() in developers:
        return False
    
    return True


def run_child_dapp():
    global child_dapp_process, dapp_initialzied
    dapp_initialzied = False

    child_dapp_process = subprocess.Popen("cd src && ROLLUP_HTTP_SERVER_URL='http://127.0.0.1:5000' ./entrypoint.sh", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, preexec_fn=os.setsid)

def wait_child_dapp():
    global dapp_initialzied, result
    
    code = None
    while code is None and not dapp_initialzied:
        code = child_dapp_process.poll()

        if code:
            err_msg = child_dapp_process.stderr.read().decode()
            raise Exception(f"Error: Child DApp execution failed!\n{err_msg}")
    
    if code == 0:
        raise Exception("Error: Child DApp terminated!")

def stop_child_dapp():
    global child_dapp_process
    os.killpg(os.getpgid(child_dapp_process.pid), signal.SIGSTOP)

def resume_child_dapp():
    global child_dapp_process
    os.killpg(os.getpgid(child_dapp_process.pid), signal.SIGCONT)

def kill_child_dapp():
    global child_dapp_process
    os.killpg(os.getpgid(child_dapp_process.pid), signal.SIGTERM)

#
# INPUT HANDLERS
#

def update_dapp(metadata, data_json):
    try:
        if not is_developer(metadata["msg_sender"]):
            raise Exception(f"Error: {metadata['msg_sender']} is not registered as a developer.")
        
        tar_filename = "new_commit.tar.gz"

        # data["src"] contains the fs with the new code
        with open(tar_filename, "wb") as f:
            b64 = data_json["src"].encode()
            f.write(base64.b64decode(b64))

        # extract tar.gz with the new code
        os.makedirs("tmp", exist_ok=True)
        run_cmd(["tar", "--strip-components", "1", "-C", "tmp", "-xvf", tar_filename])

        os.remove(tar_filename)

        kill_child_dapp()
        
        # move new code to src directory
        run_cmd("mv tmp/* src/", shell=True)

        run_cmd(["git", "add", "."])

        d = datetime.datetime.fromtimestamp(
            metadata["timestamp"],
            datetime.timezone(datetime.timedelta(hours=0))
        )
        date_str = d.strftime("%a %b %d %H:%M:%S %Y %z")
        commit_msg = data_json.get("COMMIT_MSG")
        if not commit_msg:
            commit_msg = "new version"
        run_cmd([
            "git",
            "-c", f"user.name={metadata['msg_sender']}",
            "commit", f"--date=\"{date_str}\"", "-m", commit_msg
        ])
        
        version = data_json.get("VERSION")
        if not version:
            version = d.strftime("%y.%m.%d")
        run_cmd(["git", "tag", f"v{version}"])
        
        diff = run_cmd(["git", "diff", "HEAD^", "HEAD"])
        post("notice", {"payload": str2hex(diff)})

        run_child_dapp()
        wait_child_dapp()

    except Exception as e:
        post("report", {"payload": str2hex(str(e))})
        return "reject"
    
    return "accept"

def git_tag_list():
    res = run_cmd(["git", "tag", "-l"])
    post("report", {"payload": (str2hex(res))})
    return "accept"

def git_log():
    res = run_cmd(["git", "log"])
    post("report", {"payload": (str2hex(res))})
    return "accept"

def git_ls():
    res = run_cmd(["git", "ls-tree", "--full-tree", "-r", "HEAD"])
    post("report", {"payload": (str2hex(res))})
    return "accept"


def forward_advance(data):
    global forwarded, input_data

    forwarded = True
    input_data = {
        "request_type": "advance_state",
        "data": data
    }


def forward_inspect(data):
    global forwarded, input_data
    
    forwarded = True
    input_data = {
        "request_type": "inspect_state",
        "data": data
    }


def handle_advance(data):
    try:
        payload_str = hex2str(data["payload"])
        try:
            payload_json = json.loads(payload_str)

            version_manager_op = payload_json.get("version-manager")
            if version_manager_op and version_manager_op == "update-dapp":
                return update_dapp(data["metadata"], payload_json)
            else:
                forward_advance(data)    
        except json.decoder.JSONDecodeError:
            forward_advance(data)

    except Exception as e:
        requests.post(rollup_server+"/report", json={"payload": str2hex(str(e))})
        return "reject"

def handle_inspect(data):
    try:
        payload_str = hex2str(data["payload"])

        if len(payload_str) == 7 and payload_str[:7] == "git/tag":
            return git_tag_list()
        elif len(payload_str) == 7 and payload_str[:7] == "git/log":
            return git_log()
        elif len(payload_str) == 6 and payload_str[:6] == "git/ls":
            return git_ls()
        else:
            forward_inspect(data)

    except Exception as e:
        requests.post(rollup_server+"/report", json={"payload": str2hex(str(e))})
        return "reject"


if __name__ == "__main__":
    # start flask server in a non-blocking way
    threading.Thread(target=lambda: app.run()).start()

    # repo ignores everything except src/ directory
    with open(".gitignore", "w") as f:
        print("/*", file=f)
        print("!src/", file=f)

    print(run_cmd(["git", "init", "--initial-branch=main"]))
    run_cmd(["git", "add", "."])

    run_cmd(["git", "config", "--global", "user.name", "version-manager"])
    print(run_cmd(["git", "commit", "-m", "initial version"]))
    run_cmd(["git", "tag", f"v{version_manager['VERSION']}"])

    run_child_dapp()
    wait_child_dapp()

    handlers = {
        "advance_state": handle_advance,
        "inspect_state": handle_inspect,
    }

    finish_json = {"status": "accept"}
    while True:
        if forwarded:
            if not result:
                continue
            else:
                forwarded = False
                finish_json["status"] = result
                result = None

        logger.info(f"Sending finish {finish_json}")
        response = requests.post(rollup_server + "/finish", json=finish_json)
        logger.info(f"Received finish status {response.status_code}")
        if response.status_code == 202:
            logger.info("No pending rollup request, trying again")
        else:
            rollup_request = response.json()
            handler = handlers[rollup_request["request_type"]]
            finish_json["status"] = handler(rollup_request["data"])