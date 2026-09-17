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

# if ! command -v whisper &> /dev/null; then
if ! ${python_command} -m pip show faster-whisper &> /dev/null; then
  echo "**** language_whisper_ultra: Installing whisper... ****"

  # # Intel: It is impossible to run faster-whisper on an Intel GPU
  # # CTranslate2 (faster-whisper's backend) only has two GPU backends — CUDA (NVIDIA) and ROCm/HIP (AMD)
  # cat /proc/cpuinfo | grep "model name" | uniq | grep -wi Intel && cpu_intel=true || cpu_intel=false
  # lspci -nn | egrep -i "vga|display" | grep -qi Intel && gpu_intel=true || gpu_intel=false
  # if $cpu_intel && $gpu_intel; then
  # else
    # # nvidia:
    ${python_command} -m pip install -U faster-whisper
  # fi
else
  echo "**** language_whisper_ultra: whisper already installed ****"
fi

# some cleanup
pip cache purge

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
