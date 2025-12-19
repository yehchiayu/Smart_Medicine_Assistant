#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, re, asyncio, subprocess, shutil, platform
from pathlib import Path

# ---- 中文過濾 ----
def keep_chinese(text: str) -> str:
    text = text.replace('\u3000', ' ')
    # 移除 ASCII 英文
    text = re.sub(r"[A-Za-z]", " ", text)
    
    pattern = (
        r"[^\u4e00-\u9fff"
        r"\u3400-\u4dbf"
        r"\U00020000-\U0002a6df"
        r"\U0002a700-\U0002b73f"
        r"\U0002b740-\U0002b81f"
        r"\U0002b820-\U0002ceaf"
        r"\U0002ceb0-\U0002ebef"
        r"\U00030000-\U0003134f"
        r"，。；、：！？（）《》「」『』—·．"
        r"\uFF01-\uFF5E"
        r"\d％\- ]"
        r"]"
    )
    kept = re.sub(pattern, " ", text)
    kept = re.sub(r"\s+", " ", kept).strip()
    return kept

def build_text(d: dict) -> str:
    pn = d.get("patient_name", "") or ""
    md = d.get("medicine_name", "") or ""
    us = d.get("usage_dosage", "") or ""

    # 優化：更親切的口語
    # 如果有名字，就說「XXX您好」
    greeting = f"{pn} 您好。" if pn else "您好。"
    
    # 處理藥名：只取前幾個字避免太長，或直接說「這是您的藥」
    # 這裡保留原邏輯但加強語氣
    med_intro = f"這包藥是：{md}。" if md else "這包藥的資訊如下。"

    # 處理用法：把數字跟單位分開讀得更清楚
    us = re.sub(r"(\d+)\s*次", r"\1 次", us)
    us = re.sub(r"(\d+)\s*(錠|粒|毫克|毫升|克)", r"\1 \2", us)
    
    # 組合
    txt = f"{greeting}{med_intro} 請注意用法：{us}。"

    # 清理英文與符號
    txt = " ".join(t for t in txt.split() if not re.search(r"[A-Za-z]", t))
    txt = re.sub(r"（.*?）|\(.*?\)", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()

    result = keep_chinese(txt)
    
    if not result or len(result) < 5:
        return "不好意思，我看不清楚上面的字，請重新拍一張照片。"
        
    return result

# ---- edge-tts (維持原本設定，語速 -20% 對老人剛好，-30% 也可) ----
"""
async def tts_edge(text: str, out_audio: Path, voice="zh-TW-HsiaoChenNeural", rate="-25%"):
    import edge_tts

    out_audio.parent.mkdir(parents=True, exist_ok=True)

    # 可選：避免空字串
    text = (text or "").strip()
    if not text:
        raise ValueError("TTS text is empty")

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)

    # timeout + 重試
    last_err = None
    for attempt in range(3):
        try:
            await asyncio.wait_for(communicate.save(str(out_audio)), timeout=30)
            return
        except Exception as e:
            last_err = e
            # 短暫等待後重試
            await asyncio.sleep(1.0)

    raise RuntimeError(f"edge-tts failed after 3 attempts: {last_err}")
"""
async def tts_edge(text: str, out_audio: Path):
    import edge_tts
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    # 語速設為 -25% 比較適合長輩聽力
    communicate = edge_tts.Communicate(text, voice="zh-TW-HsiaoChenNeural", rate="-25%")
    await communicate.save(str(out_audio))

def play_audio(path: Path):
    for p in ["ffplay", "afplay", "mpg123", "aplay"]:
        exe = shutil.which(p)
        if exe:
            if p == "ffplay":
                subprocess.run([exe, "-nodisp", "-autoexit", str(path)], check=False)
            else:
                subprocess.run([exe, str(path)], check=False)
            return
    print("⚠ 找不到播放器")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--speak", action="store_true", help="直接播放")
    ap.add_argument("--out_audio", default="out_audio/output.mp3", help="輸出音檔")
    args = ap.parse_args()

    data = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
    text = build_text(data)
    print("朗讀內容：", text)

    out_audio = Path(args.out_audio)
    asyncio.run(tts_edge(text, out_audio))
    print("已存檔：", out_audio)

    if args.speak:
        play_audio(out_audio)

if __name__ == "__main__":
    main()
