#!/bin/bash

set -e

error() {
    echo $@ 2>&1
    exit 1
}

git config --get remote.origin.url || error "Not in a git repo."
git diff-index --quiet HEAD -- || error "You have uncommitted changes."

short_hash=$(git rev-parse --short HEAD)

dest=s3://quilt-web-public/navigator/"$short_hash"/


echo "Building..."
npm run build

echo "Sync dry run:"
aws s3 sync --dryrun --delete --acl public-read build/ "$dest"

echo
echo -n "Continue? (y/n) "
read ans

if [[ "$ans" != "y" ]]
then
    exit 1
fi

aws s3 sync --delete --acl public-read build/ "$dest"

echo
echo "Deployment hash: $short_hash"
