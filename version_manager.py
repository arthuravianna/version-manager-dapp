import logging
import os
import subprocess
import json
import base64
import requests
import signal
import time

from cartesi import DApp, Rollup, RollupData, JSONRouter, URLRouter

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
dapp = DApp()

url_router = URLRouter()
dapp.add_router(url_router)

json_router = JSONRouter()
dapp.add_router(json_router)

# load version manager conf
VERSION_MANAGER_SERVER_URL = "http://127.0.0.1:5000"
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

def run_cmd(cmd, shell=False):
    output = subprocess.run(cmd, capture_output=True, shell=shell)
    return output.stdout.decode("utf-8")


def is_developer(msg_sender):
    developers = version_manager.get("DEVELOPERS")
    if developers and not msg_sender.lower() in developers:
        return False
    
    return True


def run_child_dapp():
    global child_dapp_process
    child_dapp_process = subprocess.Popen("./src/entrypoint.sh", stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)

def kill_child_dapp():
    global child_dapp_process
    os.killpg(os.getpgid(child_dapp_process.pid), signal.SIGTERM)

#
# INPUT HANDLERS
#

@json_router.advance({"version-manager": "update-dapp"})
def update_dapp(rollup: Rollup, data: RollupData) -> bool:
    try:
        # if not is_developer(data["metadata"]["msg_sender"]):
        #     raise Exception(f"Error: {data['metadata']['msg_sender']} is not registered as a developer.")
        
        data_json = data.json_payload()
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

        run_child_dapp()

        run_cmd(["git", "add", "."])
        run_cmd(["git", "config", "--global", "user.name", data["metadata"]["msg_sender"]])
        run_cmd(["git", "commit", "-m", "new version"])
        diff = run_cmd(["git", "diff", "HEAD^", "HEAD"])
        rollup.notice(str2hex(diff))

    except Exception as e:
        rollup.report(str2hex(str(e)))
        return False
    
    return True




@url_router.inspect('git/tag')
def git_tag_list(rollup: Rollup, data: RollupData) -> bool:
    res = run_cmd(["git", "tag", "-l"])
    rollup.report(str2hex(res))
    return True

@url_router.inspect('git/log')
def git_log(rollup: Rollup, data: RollupData) -> bool:
    res = run_cmd(["git", "log"])
    rollup.report(str2hex(res))
    return True

@url_router.inspect('git/ls')
def git_ls(rollup: Rollup, data: RollupData) -> bool:
    res = run_cmd(["git", "ls-tree", "--full-tree", "-r", "HEAD"])
    rollup.report(str2hex(res))
    return True


@dapp.advance()
def forward_advance(rollup: Rollup, data: RollupData):
    input_data = {
        "request_type": "advance_state",
        "data": {
            "metadata": {
                "msg_sender": data.metadata.msg_sender,
                "epoch_index": data.metadata.epoch_index,
                "input_index": data.metadata.input_index,
                "block_number": data.metadata.block_number,
                "timestamp": data.metadata.timestamp
            },
            "payload": data.payload
        }
    }

    requests.post(f"{VERSION_MANAGER_SERVER_URL}/input", json=input_data)

    return processing_result()

@dapp.inspect()
def forward_inspect(rollup: Rollup, data: RollupData):
    input_data = {
        "request_type": "inspect_state",
        "data": {
            "payload": data.payload
        }
    }

    requests.post(f"{VERSION_MANAGER_SERVER_URL}/input", json=input_data)

    return processing_result()


def processing_result():
    result = None

    wait = 2
    while result is None:
        time.sleep(wait)
        response = requests.get(f"{VERSION_MANAGER_SERVER_URL}/result")
        response_json = response.json()
        
        result = response_json.get("result")
        wait += 1
    
    return result


if __name__ == '__main__':
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

    dapp.run()