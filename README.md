# Version Manager DApp

This repository is an experiment on how to create an upgradable Cartesi Rollup DApp. The proposal is that the upgradable DApp is executed as a child process of another DApp, referenced as the Version Manager. The Version Manager accepts special inputs that can provide information about the child DApp version or update it. So, the Version Manager intercepts all inputs to the DApp and verifies if they are for himself. Otherwise, the input is forwarded to the child DApp.

## Architecture
The architecture is composed of the Version Manager DApp, the Version Manager Server, and the Child DApp. The requirements to run the Version Manager DApp and Server are Python, Python's Flask, and Git.

### Version Manager DApp
The Cartesi Machine generated has Git installed, and the Version Manager DApp utilizes it to manage the Child DApp's version. The Version Manager also has a version_manager.conf.json file where developers can define the first version tag and the developer list (the address list that are allowed to update the Child DApp). The Version Manager listens to the special routes listed below.

#### Inspect

1) `git/ls`: Returns the Child DApp file list.
2) `git/tag`: Returns the versions tags for the Child DApp. Every time the DApp is updated it receives a tag with the pattern `v%y.%m.%d`.
3) `git/log`: Returns the Child DApp updates history. Every commit returned by the log has the msg_sender of the commit as the Author and the Block timestamp as the date. *

* Except the initial commit, because when building the machine we don't have access to a proper timestamp.

#### Advance

1) `{"version-manager": "update-dapp", "src": "$content"}`: This route updates the Child DApp code, it is a JSON where the `src` has the content as a `.tar.gz` file encoded as `base64`. Inside the DApp it is decoded, extracted, then executed.

### Version Manager Server
This server is defined in the same Python file as the Version Manage DApp so that it can access the same variables straightforwardly. When the Version Manage DApp intercepts an input that it doesn't know how to process, it stores the input in a variable, sets a forwarded flag to True, and waits for the result. With this, when the Child DApp requests /finish, this input is served processing. After the Child DApp finishes the processing, it requests to /finish with an "accept" or "reject" that is forwarded to the HTTP API. Any notice, report, or voucher is immediately forwarded.

### Child DApp
The Child DApp is a Cartesi Rollup DApp with only the backend code and an `entrypoint.sh` script that executes it.

## Test

First, check the current log for the DApp

```shell
time curl -s http://localhost:8080/inspect/git/log | jq -r '.reports[0].payload' | xxd -r -p
```

You can also check the versions history
```shell
time curl -s http://localhost:8080/inspect/git/tag | jq -r '.reports[0].payload' | xxd -r -p
```

The default Child DApp is an "echo" DApp, send an inspect to it and check the result.
```shell
time curl -s http://localhost:8080/inspect/I_would_like_to_update_my_DApp | jq -r '.reports[0].payload' | xxd -r -p
```

Now, let's send a new code that updates the Child DApp to a "hello" DApp. For this, use the script on `misc` directory. The script requires an directory name as parameter that should contain a new DApp.
```shell
cd misc
./update.sh new_src
```

> [!WARNING]
> Wait for the finished message: `validator-1  | INFO:__main__:Sending finish`.

> [!IMPORTANT]
> When you update the code of the Child DApp a notice containing the `diff` between the codes is generated, you can also check it out.

After making sure the code was updated, send the inspect below

```shell
time curl -s http://localhost:8080/inspect/I_would_like_to_update_my_DApp
```

The input should be `reject`, since the code was updated. So, you should see something like this: `{"status":"Rejected","exception_payload":null,"reports":[],"processed_input_count":1}`


Let's try the new version with an `hello` inspect.

```shell
time curl -s http://localhost:8080/inspect/hello/Arthur | jq -r '.reports[0].payload' | xxd -r -p
```

This inspect return an string with the format `Hello <name>`, so the expected result is `Hello Arthur`. Try to change to your name and run it again :)


To finish, check the DApp log and tags. Notice that on logs the author of the commit will be the address that sent the new version and the date will be the timestamp of the block.

```shell
time curl -s http://localhost:8080/inspect/git/log | jq -r '.reports[0].payload' | xxd -r -p
```

```shell
time curl -s http://localhost:8080/inspect/git/tag | jq -r '.reports[0].payload' | xxd -r -p
```