#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json
from pathlib import Path
from PIL import Image

ICON_DIR = Path("icon")
ICONS = {
    "早": ICON_DIR / "sun.png",
    "中": ICON_DIR / "cloud.png",
    "晚": ICON_DIR / "moon.png",
    "plate": ICON_DIR / "plate.png",
}

def parse_usage(text):
    """
    解析「三餐」「每日」「每餐」「飯前/後」的用法字串
    """

    s = text or ""

    # -----------------------------
    # 判斷是否三餐（包含「每日3餐」「一天三次」「three times a day」）
    # -----------------------------
    if ("三餐" in s) or \
       ("每日3餐" in s) or \
       ("一天三次" in s) or \
       ("Three times a day" in s):
        slots = ["早","中","晚"]
    else:
        # 否則就看是否直接提到 早 / 中 / 晚
        slots = [x for x in ["早","中","晚"] if x in s]

    # -----------------------------
    # 判斷是否 **飯後** → 顯示盤子
    # 「餐後」也算飯後
    # 但如果有「飯前」就不顯示盤子
    # -----------------------------
    after_meal = (("飯後" in s) or ("餐後" in s)) and ("飯前" not in s)

    # 去重 & 排序
    order = {"早":0, "中":1, "晚":2}
    slots = sorted(list(dict.fromkeys(slots)), key=lambda x: order[x])

    return slots, after_meal


def compose(slots, after_meal, out_path, skip_last=False):
    if skip_last and slots:
        slots = slots[:-1]

    icons = []
    for s in slots:
        icons.append(Image.open(ICONS[s]).convert("RGBA"))
    if after_meal:
        icons.append(Image.open(ICONS["plate"]).convert("RGBA"))

    if not icons:
        raise RuntimeError("沒有偵測到可用的圖示，請檢查 JSON 用法內容。")

    h = max(img.height for img in icons)
    w = sum(img.width for img in icons)
    canvas = Image.new("RGBA", (w, h), (255,255,255,0))

    x = 0
    for img in icons:
        canvas.alpha_composite(img, (x, (h-img.height)//2))
        x += img.width

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path)
    print("Saved:", out_path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--out_img", default="out/usage_icons.png")
    ap.add_argument("--skip_last", action="store_true")
    args = ap.parse_args()

    data = json.load(open(args.json_path, "r", encoding="utf-8"))
    usage = data.get("usage_dosage", "")

    slots, after = parse_usage(usage)
    compose(slots, after, args.out_img, skip_last=args.skip_last)

if __name__ == "__main__":
    main()

