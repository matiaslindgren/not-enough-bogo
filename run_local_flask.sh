#!/bin/bash
source $HOME/.virtualenvs/bogoenv/bin/activate
export PYTHONPATH=$(pwd)/bogo
export FLASK_APP=$(pwd)/bogo/main.py
python3 -m flask run
