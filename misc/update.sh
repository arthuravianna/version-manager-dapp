#!/bin/bash

dir=$1
tar -czvf ${dir}.tar.gz ${dir}/*
content=$(cat ${dir}.tar.gz | base64 | tr -d '\n')

cartesi send generic --input="{\"version-manager-op\": \"update-dapp\", \"src\": \"$content\"}"
