#!/bin/bash
source $HOME/.virtualenvs/bogoenv/bin/activate
export PYTHONPATH=$(pwd)/app
export FLASK_APP=$(pwd)/app/src/main.py
python3 -m flask run
