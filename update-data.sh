#!/bin/sh
# The script use relative path:
# Use with ./update-data.sh

./data-generation.py
max_date="$(head -n1 generated/confirmed.csv | rev | cut -d, -f1 | rev)"
sed -i "2s/.*/const maxDate = \"$max_date\"/" ./visualization.js
