#! /usr/bin/bash

current_dir=$(exec 2>/dev/null;cd -- $(dirname "$0"); unset PWD; /usr/bin/pwd || /bin/pwd || pwd)

GIT_DIR=$current_dir
git commit -am "Update references"
git push
