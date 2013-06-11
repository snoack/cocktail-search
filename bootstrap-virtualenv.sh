#!/bin/sh

set -e

requirements_file="`cd \`dirname $0\`; pwd`/requirements.txt"

virtualenv "$1" 
cd "$1"
. bin/activate
pip install -r "$requirements_file"

virtual_env=`pwd`
temp_dir=`mktemp -d`

trap "rm -r $temp_dir" EXIT INT TERM


##########
# Sphinx #
##########

cd "$temp_dir"
wget http://sphinxsearch.com/files/sphinx-2.0.8-release.tar.gz -O - | tar -xz
cd sphinx-2.0.8-release
wget http://snowball.tartarus.org/dist/libstemmer_c.tgz -O - | tar -xz
./configure "--prefix=$virtual_env" --with-libstemmer --with-libexpat --without-mysql
make
make install


##################
# Node.js + less #
##################

cd "$temp_dir"
wget http://nodejs.org/dist/node-latest.tar.gz -O - | tar -xz
cd node-*
./configure "--prefix=$virtual_env"
make
make install

npm install -g less
