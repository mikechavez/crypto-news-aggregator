#!/bin/bash
# scripts/run-evidence.sh
# Wrapper to execute generate-evidence.sh with interactive bash to load aliases

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Execute the evidence generation script in interactive bash mode
# This loads the user's .bashrc and makes ripgrep alias available
bash -ic "$SCRIPT_DIR/generate-evidence.sh"
