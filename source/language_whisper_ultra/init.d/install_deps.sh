#!/bin/bash

# Script is executed by the Unmanic container on startup to auto-install dependencies

TARGET_DIR="/opt/venv"
if [ -f "$TARGET_DIR/pyvenv.cfg" -a -f "$TARGET_DIR/bin/python3" ]; then
  # Venv case (Ubuntu 24 style or manual venv)
  python_command="$TARGET_DIR/bin/python3"
else
  # System case (Ubuntu 22 style)
  python_command="/usr/bin/python3"
fi

if ! command -v whisper &> /dev/null; then
  echo "**** language_whisper_ultra: Installing whisper... ****"
  ${python_command} -m pip install -U openai-whisper
  # ${python_command} -m pip install -U pip install faster-whisper[openvino]
else
  echo "**** language_whisper_ultra: whisper already installed ****"
fi

if ${python_command} -m pip list | grep "^torch "; then
  echo "**** language_whisper_ultra: torch already installed ****"
else
  echo "**** language_whisper_ultra: Installing torch... ****"
  ${python_command} -m pip install torch
fi