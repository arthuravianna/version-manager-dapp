#!/bin/bash


flask --app version_manager_server run > server_log.txt 2>&1 &

# wait for server to start
echo "Waiting for version-manager-server..."
while [ $(grep -c "Running on http://127.0.0.1:5000" server_log.txt) -eq 0 ]
do
    continue
done

cat server_log.txt
rm server_log.txt

rollup-init python3 version_manager.py
