#!/bin/bash

# change cwd to script dir
cd "$(dirname "$0")"
cd spec

# setup spec environment
source ./shrc

# run the command
"$@"
