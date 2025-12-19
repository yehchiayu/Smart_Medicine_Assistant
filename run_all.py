#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, subprocess
from pathlib import Path

def run(cmd):
    print("\n"+ "="*60)
    print("執行:", " ".join(cmd))
    print("="*60)
    subprocess.run(cmd, check=True)

def main():
    if len(sys.argv) < 2:
        print("使用方法: python run_all.py bag.jpg")
        sys.exit(1)

    img = sys.argv[1]

    out_json   = "out_json/extract.json"
    out_preview= "out/extract.png"
    out_audio  = "out_audio/extract.mp3"
    out_usage  = "out/usage.png"

    # 1) OCR
    run(["python", "extract.py", img,
         "--out_json", out_json,
         "--out_preview", out_preview])

    # 2) TTS 語音
    run(["python", "speak.py", out_json,
         "--speak",
         "--out_audio", out_audio])

    # 3) 用藥圖示
    run(["python", "image.py", out_json,
         "--out_img", out_usage])

    # 4) 開啟圖片 (Linux 用 feh / Mac 用 open / Windows 用 start)
    if subprocess.call(["which", "feh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        run(["feh", out_usage])
    elif sys.platform == "darwin":
        run(["open", out_usage])
    else:
        run(["start", out_usage], shell=True)

if __name__ == "__main__":
    main()

