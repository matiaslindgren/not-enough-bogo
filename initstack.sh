#!/bin/bash
export LC_ALL="en_US.UTF-8"
sudo dpkg-reconfigure locales

sudo apt-get -y update && sudo apt-get -y upgrade
sudo apt-get -y install python3-pip python3-dev nginx npm nodejs-legacy

sudo pip3 install --upgrade pip
sudo pip3 install virtualenv

