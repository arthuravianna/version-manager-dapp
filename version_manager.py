import logging
import os
import subprocess
import importlib
import json
import base64
import requests

from cartesi import DApp, Rollup, RollupData, JSONRouter, URLRouter, URLParameters

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
    if developers and not msg_sender in developers:
        return False
    
    return True


def run_child_dapp():
    global child_dapp_process
    child_dapp_process = subprocess.Popen("exec ./src/entrypoint.sh", stdout=subprocess.PIPE, shell=True)

def kill_child_dapp():
    global child_dapp_process
    child_dapp_process.kill()

#
# INPUT HANDLERS
#

@json_router.advance({"version-manager": "update-dapp"})
def handle_advance(rollup: Rollup, data: RollupData) -> bool:
    try:
        if not is_developer(data.metadata.msg_sender):
            raise Exception(f"Error: {data.metadata.msg_sender} is not registered as a developer.")
        
        data = data.json_payload()
        tar_filename = "new_commit.tar.gz"

        # data["src"] contains the fs with the new code
        with open(tar_filename, "wb") as f:
            b64 = data["src"].encode()
            f.write(base64.b64decode(b64))
        
        # extract tar.gz with the new code
        os.makedirs("tmp", exist_ok=True)
        run_cmd(["tar", "--strip-components", "1", "-C", "tmp", "-xvf", tar_filename])

        os.remove(tar_filename)
        
        # move new code to src directory
        run_cmd("mv tmp/* src/", shell=True)

        run_child_dapp()

        # module = importlib.import_module("src.main")
        # module_func = getattr(module, "setup")
        # module_func(dapp, json_router, url_router, URLParameters)

        run_cmd(["git", "add", "."])
        run_cmd(["git", "config", "--global", "user.name", data.metadata.msg_sender])
        run_cmd(["git", "commit", "-m", "new version"])
        # git diff HEAD^ HEAD
        diff = run_cmd(["git", "diff", "HEAD^", "HEAD"])
        rollup.notice(str2hex(diff))

    except Exception as e:
        rollup.report(str2hex(e))
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
        "metadata": {
            "msg_sender": data.metadata.msg_sender,
            "epoch_index": data.metadata.epoch_index,
            "input_index": data.metadata.input_index,
            "block_number": data.metadata.block_number,
            "timestamp": data.metadata.timestamp
        },
        "payload": data.payload
    }

    requests.post(f"{VERSION_MANAGER_SERVER_URL}/input", json=input_data)

@dapp.inspect()
def forward_inspect(rollup: Rollup, data: RollupData):
    input_data = {
        "metadata": {},
        "payload": data.payload
    }

    requests.post(f"{VERSION_MANAGER_SERVER_URL}/input", json=input_data)





if __name__ == '__main__':
    # repo ignores everything except src/ directory
    with open(".gitignore", "w") as f:
        print("/*", file=f)
        print("!src/", file=f)
    
    print(run_cmd(["git", "init", "--initial-branch=main"]))
    run_cmd(["git", "add", "."])
    
    # --author="John Doe <>"
    run_cmd(["git", "config", "--global", "user.name", "version-manager"])
    print(run_cmd(["git", "commit", "-m", "initial version"]))
    run_cmd(["git", "tag", f"v{version_manager['VERSION']}"])

    # module = importlib.import_module("src.main")
    # module_func = getattr(module, "setup")
    # module_func(dapp, json_router, url_router, URLParameters)

    # flask --app version_manager_server run
    #subprocess.Popen("flask --app version_manager_server run", shell=True)
    #print("FLASK PROCESS RUNNING")

    run_child_dapp()

    dapp.run()