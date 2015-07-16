#!/bin/bash

# $1 is the file name for the you want to tranfer
# usage: ftpLogOverride.sh

file=""
IP_address=""
username=""
password=""

ftp -n
 verbose
 open $IP_address
 USER $username $password
 put $file
 bye
EOF

# Para instarlo, ejecución todos los días a las 00:02:00
# cron -e
# 0 2 * * * /home/ftpLogOverride.sh