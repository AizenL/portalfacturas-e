#!/bin/bash

# $1 is the file name for the you want to tranfer
# usage: ftpLogOverride.sh

FILE="log.txt"
HOST="192.168.10.6"
USER="dvelez"
PASSWD="D@rcho1982"

ftp -inv $HOST << SCRIPT
user $USER $PASSWD
passive
put $FILE
quit
SCRIPT


# Para instarlo, ejecución todos los días a las 00:02:00
# cron -e
# 0 2 * * * /home/ftpLogOverride.sh