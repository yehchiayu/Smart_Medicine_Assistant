#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extract.py — 文字截取（藥袋：姓名/藥名/用法），輸出 JSON 與可選預覽圖
用法示例：
  python extract_min3.py bag.jpg \
    --template tvgh --roi_shift_y -0.03 \
    --lang chi_tra+eng \
    --out_json out_json/extract.json \
    --out_preview out/extract.png \
    --save_rois out_rois
"""

import re, json, argparse
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont

# ---------------- Templates (relative x,y,w,h) ----------------
TEMPLATES = {
    "tvgh": {
        "name":  (0.040, 0.175, 0.30, 0.045),
        "med":   (0.040, 0.210, 0.86, 0.055),
        "usage": (0.040, 0.270, 0.86, 0.080),
    },
}

# ---------------- Utilities ----------------
def ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def load_image(p):
    img = cv2.imread(str(p))
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {p}")
    return img

def preprocess(img, do_morph=True):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 5, 25, 25)
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    if do_morph:
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, k, iterations=1)
    return thr

def crop_rel(img, rect, shift_y=0.0):
    h, w = img.shape[:2]
    x, y, rw, rh = rect
    y = max(0.0, y + shift_y)
    x1, y1 = int(x * w), int(y * h)
    x2, y2 = int((x + rw) * w), int(min(h, (y + rh) * h))
    return img[y1:y2, x1:x2].copy()

def ocr(img, psm=6, lang="chi_tra"):
    cfg = f"--oem 1 --psm {psm} -l {lang}"
    return pytesseract.image_to_string(img, config=cfg)

# ---------------- Parsers（盡量回傳繁中） ----------------
def parse_name(s):
    s_compact = s.replace(" ", "").replace("：", ":")
    m = re.search(r"(姓名|姓\s*名|Name)\s*[:：]\s*([\u4e00-\u9fa5]{2,4})(先生|小姐|女士|君)?", s, re.I)
    if m:
        return (m.group(2) + (m.group(3) or "")).strip()
    m2 = re.search(r"([\u4e00-\u9fa5]{2,4})(先生|小姐|女士|君)", s_compact)
    if m2:
        return m2.group(0)
    m3 = re.search(r"([\u4e00-\u9fa5]{2,4})", s_compact)
    if m3:
        return m3.group(1)
    return s.strip().splitlines()[0] if s.strip() else ""

def parse_medicine(s):
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    zh_hits, en_hits = [], []
    for ln in lines:
        if re.search(r"(藥名|藥品名稱|商品名|學名)", ln):
            tail = re.sub(r".*?[:：]", "", ln).strip()
            if tail: zh_hits.append(tail); continue
        if re.search(r"Drug\s*Name|Generic\s*Name|Brand\s*Name", ln, re.I):
            tail = re.sub(r".*?[:：]", "", ln).strip()
            if tail: en_hits.append(tail); continue
        if re.search(r"(mg|mcg|g|tab|tablet|capsule|錠|膠囊|片|mL)", ln, re.I):
            (zh_hits if re.search(r"[\u4e00-\u9fa5]", ln) else en_hits).append(ln)

    def uniq(seq):
        seen, out = set(), []
        for x in seq:
            if x not in seen:
                seen.add(x); out.append(x)
        return out

    zh_hits = uniq(zh_hits)
    en_hits = uniq(en_hits)

    if zh_hits and en_hits:
        return "；".join((zh_hits[:2] + en_hits[:2]))
    if zh_hits:
        return "；".join(zh_hits[:3])
    if en_hits:
        return "；".join(en_hits[:3])
    return lines[0] if lines else ""

def parse_usage(s):
    s = s.replace("\u3000", " ")
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    text = " ".join(lines)

    m = re.search(r"(用法[及/]?用量|用法|用量)[:：]?\s*([^\n]+)", text)
    if m:
        return m.group(2).strip()

    adm = re.search(r"(Administration|Direction[s]?)[:：]?\s*([^.。]+)", text, re.I)
    dos = re.search(r"(Dosage)[:：]?\s*([^.。]+)", text, re.I)
    parts = []
    if adm: parts.append(adm.group(2).strip())
    if dos: parts.append(dos.group(2).strip())
    if parts:
        return "；".join(parts)

    m2 = re.search(r"([^\n。]*(每|次|餐|飯前|飯後|早|中|晚|睡前)[^。]*)", text)
    return m2.group(1).strip() if m2 else (lines[0] if lines else "")

# ---------------- Visual annotate ----------------
def annotate(img, rects, out_path):
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 34)
    except:
        font = ImageFont.load_default()
    colors = [(220,20,60), (30,144,255), (34,139,34)]
    keys = ["name", "med", "usage"]
    W, H = im.size
    for i, k in enumerate(keys, 1):
        x, y, rw, rh = rects[k]
        x1, y1 = int(x * W), int(y * H)
        x2, y2 = int((x + rw) * W), int((y + rh) * H)
        c = colors[(i - 1) % 3]
        draw.rectangle([x1, y1, x2, y2], outline=c, width=6)
        draw.rectangle([x1, y1 - 38, x1 + 46, y1], fill=c)
        draw.text((x1 + 10, y1 - 36), str(i), fill=(255, 255, 255), font=font)
    ensure_parent(Path(out_path))
    im.save(out_path)

def save_rois(folder, name_img, med_img, usage_img):
    outdir = Path(folder)
    outdir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(outdir / "1_name.png"), name_img)
    cv2.imwrite(str(outdir / "2_medicine.png"), med_img)
    cv2.imwrite(str(outdir / "3_usage.png"), usage_img)

# ---------------- Main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--template", default="tvgh", choices=list(TEMPLATES.keys()))
    ap.add_argument("--out_json", default="out_json/extract.json")
    ap.add_argument("--out_preview", default="")
    ap.add_argument("--save_rois", default="", help="若提供資料夾路徑，將另存三個 ROI 影像")
    ap.add_argument("--psm", type=int, default=6)
    ap.add_argument("--psm_name", type=int, default=None)
    ap.add_argument("--psm_med", type=int, default=None)
    ap.add_argument("--psm_usage", type=int, default=None)
    ap.add_argument("--lang", default="chi_tra+eng", help="建議：chi_tra+eng")
    ap.add_argument("--roi_shift_y", type=float, default=0.0, help="整體垂直位移（負數=上移）")
    args = ap.parse_args()

    img = load_image(args.image)
    rects = TEMPLATES[args.template]

    name_roi  = crop_rel(img, rects["name"],  args.roi_shift_y)
    med_roi   = crop_rel(img, rects["med"],   args.roi_shift_y)
    usage_roi = crop_rel(img, rects["usage"], args.roi_shift_y)

    name_img  = preprocess(name_roi)
    med_img   = preprocess(med_roi)
    usage_img = preprocess(usage_roi)

    psm_name  = args.psm_name  if args.psm_name  is not None else args.psm
    psm_med   = args.psm_med   if args.psm_med   is not None else args.psm
    psm_usage = args.psm_usage if args.psm_usage is not None else args.psm

    name_txt  = ocr(name_img,  psm=psm_name,  lang=args.lang)
    med_txt   = ocr(med_img,   psm=psm_med,   lang=args.lang)
    usage_txt = ocr(usage_img, psm=psm_usage, lang=args.lang)

    result = {
        "patient_name": parse_name(name_txt),
        "medicine_name": parse_medicine(med_txt),
        "usage_dosage": parse_usage(usage_txt),
    }
        # ---- 刪除句號（全形 + 半形）----
    for k in result:
        if isinstance(result[k], str):
            result[k] = result[k].replace("。", "").replace(".", "").strip()


    out_json = Path(args.out_json)
    ensure_parent(out_json)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if args.out_preview:
        annotate(img, rects, args.out_preview)

    if args.save_rois:
        save_rois(args.save_rois, name_roi, med_roi, usage_roi)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Saved JSON:", str(out_json))
    if args.out_preview:
        print("Preview:", args.out_preview)
    if args.save_rois:
        print("ROIs saved to:", args.save_rois)

if __name__ == "__main__":
    main()

