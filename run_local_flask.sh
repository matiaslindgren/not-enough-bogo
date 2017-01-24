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

if [[ $? != 0 ]]; then
  echo
  echo Something went wrong
  echo
  exit $?
else
  echo
  echo Everything seems to be fine
  echo ===========================
fi
echo

python3 -m flask run
