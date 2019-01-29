#! /bin/bash
set -e

# latest commit
LATEST_COMMIT=$(git rev-parse HEAD)

# latest commit where deployment/ was changed
DEPLOY_COMMIT=$(git log -1 --format=format:%H --full-diff deployment/)

if [ $DEPLOY_COMMIT = $LATEST_COMMIT ];
    then
        echo "Files in deployment/ have changed."
        ./deploy.sh
else
     echo "No folders of relevance has changed."
     exit 0;
fi
