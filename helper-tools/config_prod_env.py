#!/usr/bin/python3

# This file is part of agora-dev-box.
# Copyright (C) 2017  Agora Voting SL <nvotes@nvotes.com>

# agora-dev-box is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-dev-box  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with agora-dev-box.  If not, see <http://www.gnu.org/licenses/>. 

import string
from os import urandom
import sys
import argparse
import re

def store_keyvalue(prod_config, generated_config, keystore, pipe):
  '''
  Updates the keyvalue store
  '''
  keystore.update(pipe['data'])
  return generated_config

def store_keyvalue_match(prod_config, generated_config, keystore, pipe):
  '''
  Match and store
  '''
  rx = re.compile(pipe['pattern'], re.MULTILINE)
  for match in rx.finditer(prod_config):
    keystore[match.group(pipe['store_key_group'])] = match.group(pipe['store_value_group'])
  return generated_config

def replace_keyvalue_match(prod_config, generated_config, keystore, pipe):
  '''
  Match and replace
  '''
  def replacer(match):
    value = keystore[match.group(pipe['lookup_key_group'])]
    templ = pipe['replace_templ'].replace("{lookup_value}", value)
    return match.expand(templ)

  rx = re.compile(pipe['pattern'], re.MULTILINE)
  return re.sub(rx, replacer, generated_config)

def process_pipes(pipes, prod_config, staging_config):
  '''
  Applies the pipe list
  '''
  keystore = dict()
  generated_config = staging_config
  for pipe in pipes:
    if pipe["name"] == "store_keyvalue_match":
      generated_config = store_keyvalue_match(prod_config, generated_config,
        keystore, pipe)
    elif pipe["name"] == "store_keyvalue":
      generated_config = store_keyvalue(prod_config, generated_config,
        keystore, pipe)
    elif pipe["name"] == "replace_keyvalue_match":
      generated_config = replace_keyvalue_match(prod_config, generated_config,
        keystore, pipe)

  return generated_config

# read arguments
parser = argparse.ArgumentParser(description=('Populate config.yml on '
  'agora-dev-box with random passwords. WARNING: This WILL delete your '
  'passwords, please make a copy of config.yml before executing it.'))
parser.add_argument('-p', '--production-config', help=('Path to the '
  'current production config.yml file'), required=True)
parser.add_argument('-s', '--staging-config', help=('Path to the current '
  'staging config.yml file, which will be the base for the new production '
  'config.yml file'), required=True)
parser.add_argument('-o', '--out', help=('Specify the path to the output '
  'config.yml production configuration file'), required=True)

# get file paths
args = parser.parse_args()
prod_config_path = args.production_config
staging_config_path = args.staging_config
output_path = args.out

pipes=[
  # extract some values from the old production configuration file
  dict(
    name="store_keyvalue_match",
    pattern="^\s*(" + "|".join(["backup_password", "global_secret_key",
      "eorchestra_password", "db_password", "shared_secret", "keystore_pass",
      "admin_password", "password", "host", "public_ipaddress",
      "private_ipaddress", "election_start_id", "settings_help_base_url",
      "settings_help_default_url", "admin_signup_link"]) + ")\s*:\s+(.*)\s*$",
    store_key_group=1,
    store_value_group=2
  ),
  # set some default values keyvalues, used for migration
  dict(
    name="store_keyvalue",
    data=dict(
      settings_help_base_url="https://nvotes.com/doc-print/en/embedded-docs/",
      settings_help_default_url="https://nvotes.com/doc-print/en/embedded-docs/not-found/",
      admin_signup_link="https://nvotes.com"
    )
  ),
  # replace values in the new configuration file
  dict(
    name="replace_keyvalue_match",
    pattern="^(\s*(" + "|".join(["backup_password", "global_secret_key",
      "eorchestra_password", "db_password", "shared_secret", "keystore_pass",
      "admin_password", "password", "host", "public_ipaddress",
      "private_ipaddress", "election_start_id", "settings_help_base_url",
      "settings_help_default_url", "admin_signup_link"]) + ")\s*:\s+).*(\s*)$",
    lookup_key_group=2,
    replace_templ="\\1 {lookup_value}\\3\n"
  ),
  # extract hosts from the production configuration file
  dict(
    name="store_keyvalue_match",
    pattern="^\s*(hosts):\s*(\[.*\]|\n(\s+- hostname:.*\n+\s+ip:.*\n+)+)",
    store_key_group=1,
    store_value_group=2
  ),
  # replace hosts from the production configuration file
  dict(
    name="replace_keyvalue_match",
    pattern="^(\s*(hosts):\s*)(\[.*\]|\n(\s+- hostname:.*\n+\s+ip:.*\n+)+)",
    lookup_key_group=2,
    replace_templ="\\1 {lookup_value}\n"
  ),
  # extract slave_agoraelections_ssh_keys or slave_postgres_ssh_keys from the
  # production configuration file
  dict(
    name="store_keyvalue_match",
    match_file="old_pro",
    pattern="^\s*(slave_agoraelections_ssh_keys|slave_postgres_ssh_keys):\s*(\[.*\]|\n(\s+- ssh.*\n+)+)",
    store_key_group=1,
    store_value_group=2
  ),
  # replace hosts from the production configuration file
  dict(
    name="replace_keyvalue_match",
    pattern="^(\s*(slave_agoraelections_ssh_keys|slave_postgres_ssh_keys):\s*)(\[.*\]|\n(\s+- ssh.*\n+)+)",
    lookup_key_group=2,
    replace_templ="\\1 {lookup_value}\n\n"
  ),
  # extract domain from the production configuration file
  dict(
    name="store_keyvalue_match",
    pattern="^\s*agora_gui:\s*\n\s*(domain):\s+(.*)$",
    store_key_group=1,
    store_value_group=2
  ),
  # replace domain from the production configuration file (appears twice)
  dict(
    name="replace_keyvalue_match",
    pattern="^(\s*(agora_gui|expiry):.*\n\s*(domain):\s+)(.*)$",
    lookup_key_group=3,
    replace_templ="\\1 {lookup_value}\n"
  ),
]

# Extract the configuration passwords from the current production configuration
# file
prod_config = open(prod_config_path, 'r', encoding='utf-8').read()
staging_config = open(staging_config_path, 'r', encoding='utf-8').read()

generated_config = process_pipes(pipes, prod_config, staging_config)

# Open the test configuration and modify it to apply the extracted passwords and
# extracted production details
with open(output_path, 'w', encoding='utf-8') as config_file_out:
  config_file_out.seek(0)
  config_file_out.write(generated_config)
