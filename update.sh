<<<<<<< HEAD
#! /usr/bin/bash

current_dir=$(exec 2>/dev/null;cd -- $(dirname "$0"); unset PWD; /usr/bin/pwd || /bin/pwd || pwd)

export GIT_DIR=${current_dir}/.git
echo $GIT_DIR
git commit -am "Update references"
git push
||||||| 774f737 (Update references)
=======
#! /usr/bin/bash

current_dir=$(exec 2>/dev/null;cd -- $(dirname "$0"); unset PWD; /usr/bin/pwd || /bin/pwd || pwd)

GIT_DIR=$current_dir
git commit -am "Update references"
git push
>>>>>>> parent of 774f737 (Update references)
