# Version Manager DApp

This repository is an experiment on how to create an upgradable Cartesi Rollup DApp. The proposal is that the upgradable DApp is executed as a child process of another DApp, referenced as the Version Manager. The Version Manager accepts special inputs that can provide information about the child DApp version or update it. So, the Version Manager intercepts all inputs to the DApp and verifies if they are for himself. Otherwise, the input is forwarded to the child DApp.

## Tech

### Version Manager DApp

### Version Manager Server

### Child DApp

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