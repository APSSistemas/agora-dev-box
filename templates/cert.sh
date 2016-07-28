#!/bin/bash

# This file is part of agora-dev-box.
# Copyright (C) 2014-2016  Agora Voting SL <agora@agoravoting.com>

# agora-dev-box is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-dev-box  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with agora-dev-box.  If not, see <http://www.gnu.org/licenses/>.

C="{{ config.cert.C }}"
ST="{{ config.cert.ST }}"
L="{{ config.cert.L }}"
O="{{ config.cert.O }}"
OU="{{ config.cert.OU }}"
HOST=$(hostname)
CN=$(hostname)
EMAIL={{ config.cert.EMAIL }}
DNS1={{ config.agora_elections.domain }}

CERT_DIR="/srv/certs/selfsigned"
CERT_PREFIX="cert"
CERT_PATH="$CERT_DIR/${CERT_PREFIX}.pem"
CERT_KEY_PATH="$CERT_DIR/key-nopass.pem"
CERT_CALIST_PATH="$CERT_DIR/calist"

CREATE_CERT=false
CALIST_COPY=""

if [ ! -f $CERT_PATH ]; then
  CREATE_CERT=true
else
  # Check if the existing certificate has a valid name and alternative DNS
  NOW_CN=$(openssl x509 -in "$CERT_PATH" -text | grep "Subject: " | sed s/.*,\ CN\=// | sed s/\\/emailAddress.*//)
  NOW_DNS_LIST=$(openssl x509 -in "$CERT_PATH" -text  | awk '/X509v3\ Subject\ Alternative\ Name:/ { getline; print $0}')
  NOW_DNS1=$(echo "$NOW_DNS_LIST" | awk '{print $1}' | sed s/DNS:// | sed s/,//)
  NOW_DNS2=$(echo "$NOW_DNS_LIST" | awk '{print $2}' | sed s/DNS:// | sed s/,//)
  CREATE_CERT=true
  if [ "$NOW_CN" == "$CN" ] || [ "$NOW_CN" == "$DNS1" ]; then
    if [ "$NOW_DNS1" == "$CN" ] && [ "$NOW_DNS2" == "$DNS1" ]; then
      CREATE_CERT=false
    fi
    if [ "$NOW_DNS1" == "$DNS1" ] && [ "$NOW_DNS2" == "$CN" ]; then
      CREATE_CERT=false
    fi
  fi
fi

if [ "--gencert" == "$1" ]; then
  CREATE_CERT=true
  if [ "false" == "$2" ]; then
    CREATE_CERT=false
  fi
fi

if [ "$CREATE_CERT" == true ]; then
  # If there are CAs installed for the authorities, preserve them
  if [ "$CREATE_CERT" == true ]; then
    # Remove own CA, preserve authorities CAs
    CALIST_COPY=$(python "/root/cert.py" "$CERT_PATH" "$CERT_CALIST_PATH")
  fi
  openssl req -nodes -x509 -newkey rsa:4096 -extensions v3_ca -keyout "$CERT_KEY_PATH" -out "$CERT_PATH" -days 3650  -subj "/C=${C}/ST=${ST}/L=${L}/O=${O}/OU=${OU}/CN=${CN}/emailAddress=${EMAIL}" -config <(cat <<-EOF
[req]
default_bits           = 4096
default_md             = sha256
distinguished_name     = req_distinguished_name
x509_extensions        = v3_ca

[ req_distinguished_name ]
countryName            = ${C}                     # C=
stateOrProvinceName    = ${ST}                    # ST=
localityName           = ${L}                     # L=
organizationName       = ${O}                     # O=
organizationalUnitName = ${OU}                    # OU=
commonName             = ${CN}                    # CN=
emailAddress           = ${EMAIL}                 # CN/emailAddress=

[ v3_ca ]
# The extentions to add to a self-signed cert
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always,issuer:always
basicConstraints       = CA:TRUE
keyUsage               = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment, keyAgreement, keyCertSign
subjectAltName         = DNS:${DNS1},DNS:${CN}
issuerAltName          = issuer:copy

EOF
)
  cp "$CERT_PATH" "$CERT_CALIST_PATH"
  echo "$CALIST_COPY" >> "$CERT_CALIST_PATH"
fi