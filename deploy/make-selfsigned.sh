#!/bin/sh
set -e
host="${1:?usage: make-selfsigned.sh hospital.example.local}"
mkdir -p certs
openssl req -x509 -nodes -newkey rsa:3072 -sha256 -days 365 -keyout certs/privkey.pem -out certs/fullchain.pem -subj "/CN=$host" -addext "subjectAltName=DNS:$host"
chmod 600 certs/privkey.pem
