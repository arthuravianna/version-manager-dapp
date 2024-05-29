import logging
import os
import subprocess
import importlib
import json
import base64

from cartesi import DApp, Rollup, RollupData, JSONRouter, URLRouter, URLParameters

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
dapp = DApp()

url_router = URLRouter()
dapp.add_router(url_router)

json_router = JSONRouter()
dapp.add_router(json_router)

# load version manager conf
version_manager = None
with open("version_manager.conf.json", "r") as f:
    version_manager = json.load(f)



# utility functions
def str2hex(str):
    """Encodes a string as a hex string"""
    return "0x" + str.encode("utf-8").hex()

def run_cmd(cmd, shell=False):
    output = subprocess.run(cmd, capture_output=True, shell=shell)
    return output.stdout.decode("utf-8")


@json_router.advance({"version-manager-op": "update-dapp"})
def handle_advance(rollup: Rollup, data: RollupData) -> bool:
    try:
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

        module = importlib.import_module("src.main")
        module_func = getattr(module, "setup")
        module_func(dapp, json_router, url_router, URLParameters)

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
def git_log(rollup: Rollup, data: RollupData) -> bool:
    res = run_cmd(["git", "ls-tree", "--full-tree", "-r", "HEAD"])
    rollup.report(str2hex(res))
    return True



if __name__ == '__main__':
    # repo ignores everything except src/ directory
    # with open(".gitignore", "w") as f:
    #     print("dapp.py", file=f)
    #     print("version_manager.conf.json", file=f)
    
    # print(run_cmd(["git", "init", "--initial-branch=main"]))
    # run_cmd(["git", "add", "."])
    # run_cmd(["git", "config", "--global", "user.name", "version-manager"])
    # print(run_cmd(["git", "commit", "-m", "initial version"]))
    # run_cmd(["git", "tag", f"v{version_manager['VERSION']}"])

    module = importlib.import_module("src.main")
    module_func = getattr(module, "setup")
    module_func(dapp, json_router, url_router, URLParameters)

    dapp.run()