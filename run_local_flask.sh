#!/bin/bash
echo
echo Building js sources
npm run build
echo

echo Running backend tests
echo
source $HOME/.virtualenvs/bogoenv/bin/activate
export FLASK_APP=bogo/bogo/main.py
python3 -m unittest discover -s bogo -v
echo

echo
if [[ $? != 0 ]]; then
  echo Something went wrong
  exit $?
else
  echo Everything seems to be fine
fi
echo
echo

python3 -m flask run
