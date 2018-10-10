#!/bin/bash
# this file should be executed from the dir it is in
docker exec -it dg01 python manage.py test -t ../src/
