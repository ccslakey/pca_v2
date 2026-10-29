#!/bin/sh
# Railway's pre-deploy command (railway.toml): runs once per deploy, in the new image, before it
# takes traffic. A failure stops the deploy and leaves the running version serving.
set -e
python manage.py migrate --noinput
# The methodology docs ship in the image, so a deploy is the only time they can change.
python manage.py index_methodology
