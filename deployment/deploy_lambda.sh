#!/bin/bash

set -e

error() {
    echo $@ 2>&1
    exit 1
}

[ "$#" -eq 0 ] || error "Usage: $0"

base_dir=$(dirname "$0")

git config --get remote.origin.url > /dev/null || error "Not in a git repo."
git diff-index --quiet HEAD -- || error "You have uncommitted changes."

short_hash=$(git rev-parse --short HEAD)

echo "Current hash: $short_hash"

zip_file=$(mktemp --suffix .zip)
echo "Building $zip_file..."

"$base_dir/build_lambda_zip.sh" "." "$zip_file"

primary_region=us-east-1
regions=$(aws ec2 describe-regions --query "Regions[].{Name:RegionName}" --output text)

lambda_name=$(basename "$(pwd)")
s3_key="$lambda_name/$short_hash.zip"

echo "Uploading to $primary_region..."
aws s3 cp --acl public-read "$zip_file" "s3://quilt-lambda-$primary_region/$s3_key"
rm "$zip_file"

for region in $regions
do
    if [ "$region" != "$primary_region" ]
    then
        echo "Copying to $region..."
        aws s3 cp --acl public-read "s3://quilt-lambda-$primary_region/$s3_key" "s3://quilt-lambda-$region/$s3_key"
    fi
done

echo "Deployed $s3_key"
