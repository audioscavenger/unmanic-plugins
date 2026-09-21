#!/bin/bash
# Script is executed by the Unmanic container on startup to auto-install dependencies

# Ensure errors don't silently cascade
set -e

echo "**** language_whisper_ultra: Starting dependency check... ****"

# 0. FORCE VENV ACTIVATION IF IT EXISTS (Handles manual testing perfectly)
if [ -f "/opt/venv/bin/activate" ]; then
  echo "**** language_whisper_ultra: Activating venv virtual environment... ****"
  source /opt/venv/bin/activate
fi

# 1. DYNAMICALLY DETECT THE CORRECT PYTHON INTERPRETER
# We query 'which python3' first because Unmanic sets up its runtime environment variables (PATH) 
# pointing directly to its active environment (whether system or venv) when executing scripts.
if command -v python3 &> /dev/null; then
  python_command=$(command -v python3)
elif [ -f "/opt/venv/bin/python3" ]; then
  python_command="/opt/venv/bin/python3"
else
  python_command="/usr/bin/python3"
fi
echo "**** language_whisper_ultra: Using Python at ${python_command} ****"

# 2. ACCURATE DEPENDENCY CHECK & INSTALLATION
# Avoid breaking system packages if it falls back to a global system context
PIP_FLAGS=""
if [[ "$python_command" == "/usr/bin/python3" ]]; then
  PIP_FLAGS="--break-system-packages"
fi

if ! ${python_command} -m pip show faster-whisper &> /dev/null; then
  echo "**** language_whisper_ultra: Installing whisper... ****"

  # # Intel: It is impossible to run faster-whisper on an Intel GPU
  # # CTranslate2 (faster-whisper's backend) only has two GPU backends — CUDA (NVIDIA) and ROCm/HIP (AMD)
  # cat /proc/cpuinfo | grep "model name" | uniq | grep -wi Intel && cpu_intel=true || cpu_intel=false
  # lspci -nn | egrep -i "vga|display" | grep -qi Intel && gpu_intel=true || gpu_intel=false
  # if $cpu_intel && $gpu_intel; then
  # else
    # # nvidia:
    ${python_command} -m pip install $PIP_FLAGS -U faster-whisper
  # fi
else
  echo "**** language_whisper_ultra: whisper already installed ****"
fi

# 3. SAFE CLEANUP
echo "**** language_whisper_ultra: Running package cache cleanup... ****"
${python_command} -m pip cache purge

# more cleanup
# python3 -m pip uninstall -y torch torchvision diffusers optimum optimum-intel openvino faster-whisper openai-whisper nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 nvidia-nccl-cu12 nvidia-nvtx-cu12 triton openvino-telemetry mpmath zipp urllib3 typing-extensions tqdm threadpoolctl tabulate sympy shellingham setuptools safetensors regex pyyaml pyparsing pygments psutil Pillow packaging numpy ninja networkx narwhals mdurl MarkupSafe idna hf-xet h11 fsspec filelock cloudpickle click charset_normalizer certifi annotated-doc scipy requests pydot markdown-it-py joblib jinja2 importlib_metadata httpcore anyio torch scikit-learn rich openvino-tokenizers httpx typer nncf huggingface-hub tokenizers diffusers transformers optimum optimum-intel
# rm -rf /usr/local/lib/python3.13/dist-packages/nvidia*
# rm -rf /usr/local/lib/python3.13/dist-packages/triton*
# pip freeze | grep -v "apt-listchanges" | cut -d'=' -f1 | xargs -n 1 pip uninstall -y

# test
# from faster_whisper import WhisperModel
# model = WhisperModel('tiny', device="cuda", compute_type="int8")
# model = WhisperModel('tiny', device="openvino", compute_type="int8")
# model = WhisperModel('tiny', device="cpu", compute_type="int8")
