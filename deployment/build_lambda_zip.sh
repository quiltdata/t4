#!/bin/bash

set -e

error() {
    echo $@ 2>&1
    exit 1
}

[ "$#" -eq 2 ] || error "Usage: $0 lambda_dir output.zip"
lambda_dir=$(readlink -f "$1")
zip_file=$(readlink -f "$2")

docker run --rm \
  -v "$lambda_dir:/lambda" \
  -v "$zip_file:/out.zip" \
  quiltdata/lambda \
  bash -c 'pip3 install /lambda/ -t out && python3 -m compileall out && cd out && zip -r - . > /out.zip'
