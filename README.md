# 系統需求
Ubuntu  22.04\
Python 3.10+ \
可正常連線到網際網路（edge-tts 需要）

# 安裝環境、套件
sudo apt update\
sudo apt install -y \
python3-venv python3-tk \
tesseract-ocr tesseract-ocr-chi-tra \
fonts-dejavu-core \
ffmpeg


python3 -m venv .venv\
source .venv/bin/activate

python -m pip install -U pip\
python -m pip install \
opencv-python-headless \
numpy \
pillow \
pytesseract \
edge-tts

# 執行
./.venv/bin/python gui.py
