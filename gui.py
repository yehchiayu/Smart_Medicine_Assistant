#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font, Toplevel
from PIL import Image, ImageTk


# ---- 設定與路徑 ----
APP_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

# Default IO paths
OUT_JSON   = APP_DIR / "out_json" / "extract.json"
OUT_PREVIEW= APP_DIR / "out" / "extract.png"
OUT_AUDIO  = APP_DIR / "out_audio" / "extract.mp3"
OUT_USAGE  = APP_DIR / "out" / "usage.png"

# ---- 配色方案 (極簡全白) ----
COLOR_BG = "#FFFFFF"       # 全白背景
COLOR_PANEL = "#FFFFFF"    # 面板也全白 (移除灰色塊)
COLOR_BTN_1 = "#4682B4"    # SteelBlue
COLOR_BTN_2 = "#228B22"    # ForestGreen
COLOR_BTN_3 = "#FF8C00"    # DarkOrange
COLOR_TEXT_MAIN = "#000000"
COLOR_STATUS = "#B22222"

def safe_mkdirs():
    (APP_DIR / "out_json").mkdir(parents=True, exist_ok=True)
    (APP_DIR / "out").mkdir(parents=True, exist_ok=True)
    (APP_DIR / "out_audio").mkdir(parents=True, exist_ok=True)

def play_audio_file(path: Path):
    import shutil
    if not path.exists():
        return
    players = ["ffplay", "mpg123", "aplay", "afplay"]
    for p in players:
        exe = shutil.which(p)
        if exe:
            if p == "ffplay":
                subprocess.Popen([exe, "-nodisp", "-autoexit", str(path)])
            else:
                subprocess.Popen([exe, str(path)])
            return
    if sys.platform.startswith("darwin"):
        subprocess.Popen(["open", str(path)])
    elif os.name == "nt":
        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])

def run_cmd_silent(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"執行錯誤:\n{proc.stderr}")

class ElderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("藥袋語音小幫手")
        
        self.geometry("1024x768")
        if os.name == 'nt':
            self.state('zoomed')
        else:
            self.attributes('-zoomed', True)
        
        self.configure(bg=COLOR_BG)
        safe_mkdirs()
        
        self.base_size = 20
        font_family = "Microsoft JhengHei" if os.name == 'nt' else "Heiti TC"
        self.font_s = font.Font(family=font_family, size=self.base_size)
        self.font_m = font.Font(family=font_family, size=self.base_size+6,weight="bold")
        self.font_l = font.Font(family=font_family, size=self.base_size+14,weight="bold")
        
        
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Step1.TButton", font=self.font_m, background=COLOR_BTN_1, foreground="white", padding=20)
        style.configure("Step2.TButton", font=self.font_m, background=COLOR_BTN_2, foreground="white", padding=20)
        style.configure("Step3.TButton", font=self.font_m, background=COLOR_BTN_3, foreground="white", padding=20)
        style.map("Step1.TButton", background=[('active', '#5F9EA0')])
        style.map("Step2.TButton", background=[('active', '#32CD32')])
        style.map("Step3.TButton", background=[('active', '#FFA500')])

        self.image_path = None
        self.is_processing = False
        
        # [新增] 用來記錄現在是不是正在顯示「分析結果」
        self.showing_result = False
        
        self._build_ui()

    def _build_ui(self):
        # 標題 (移除灰色背景)
        header = tk.Frame(self, bg=COLOR_PANEL, pady=10)
        header.pack(side=tk.TOP, fill=tk.X)
        tk.Label(header, text="👵 智慧藥袋唸給您聽 👴", font=self.font_l, bg=COLOR_PANEL, fg=COLOR_TEXT_MAIN).pack()

        # 內容區
        content_frame = tk.Frame(self, bg=COLOR_BG)
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 左側：照片 (bd=0 去除邊框, relief='flat' 去除浮雕)
        left_frame = tk.LabelFrame(content_frame, text=" 您的藥袋照片 (點擊可放大) ", font=self.font_m, 
                                   bg=COLOR_BG, fg="blue", bd=0, relief="flat")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        self.lbl_img = tk.Label(left_frame, text="\n請按下方藍色按鈕\n\n選取照片", font=self.font_m, bg="#F5F5F5") # 稍微給一點灰底區分圖片區
        self.lbl_img.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.lbl_img.bind("<Button-1>", self.popup_image)
        self.lbl_img.config(cursor="hand2")

        # 右側：結果 (bd=0 去除邊框)
        right_frame = tk.LabelFrame(content_frame, text=" 顯示結果 ", font=self.font_m, 
                                    bg=COLOR_BG, fg="blue", bd=0, relief="flat")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        self.lbl_icon = tk.Label(right_frame, text="等待分析...", font=self.font_m, bg="white", bd=0)
        self.lbl_icon.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 文字框 (bd=0, highlightthickness=0 去除選取框線)
        self.txt_result = tk.Text(right_frame, height=6, font=("Microsoft JhengHei", 28), 
                                  bg="#FFFFFF", wrap=tk.WORD, bd=0, highlightthickness=0, relief="flat")
        self.txt_result.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.txt_result.insert(tk.END, "請依照下方 1、2、3 步驟操作")
        self.txt_result.config(state=tk.DISABLED)

        # 狀態列
        self.lbl_status = tk.Label(self, text="準備中：請先選照片", font=self.font_m, bg="#F0E68C", fg="black", pady=10)
        self.lbl_status.pack(side=tk.TOP, fill=tk.X)

        # 按鈕區
        btn_frame = tk.Frame(self, bg=COLOR_BG, pady=20)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        self.btn_1 = ttk.Button(btn_frame, text="1. 選取照片 📁", style="Step1.TButton", command=self.pick_file)
        self.btn_1.grid(row=0, column=0, padx=20, sticky="ew")

        self.btn_2 = ttk.Button(btn_frame, text="2. 開始分析 ▶", style="Step2.TButton", command=self.start_analysis)
        self.btn_2.grid(row=0, column=1, padx=20, sticky="ew")
        
        self.btn_3 = ttk.Button(btn_frame, text="3. 再聽一次 🔊", style="Step3.TButton", command=lambda: play_audio_file(OUT_AUDIO))
        self.btn_3.grid(row=0, column=2, padx=20, sticky="ew")
        
        self.btn_2.state(["disabled"])
        self.btn_3.state(["disabled"])

    def popup_image(self, event):
        #target_path = OUT_PREVIEW if OUT_PREVIEW.exists() and self.is_processing == False else self.image_path
        
        # [修改] 改用 showing_result 來判斷
        # 如果現在是結果模式 (True) 且檔案存在，就開結果圖；否則開原圖
        if self.showing_result and OUT_PREVIEW.exists():
            target_path = OUT_PREVIEW
        else:
            target_path = self.image_path
            
        if not target_path or not target_path.exists():
            return

        top = Toplevel(self)
        top.title("照片放大檢視")
        top.state('zoomed') if os.name == 'nt' else top.attributes('-fullscreen', True)
        top.configure(bg="black")

        btn_close = tk.Button(top, text="❌ 關閉大圖", font=("Microsoft JhengHei", 24, "bold"), 
                              bg="red", fg="white", command=top.destroy)
        btn_close.pack(side=tk.TOP, fill=tk.X, pady=10)

        lbl_big = tk.Label(top, bg="black")
        lbl_big.pack(fill=tk.BOTH, expand=True)

        top.update_idletasks()
        
        try:
            img = Image.open(target_path)
            w, h = top.winfo_width(), top.winfo_height() - 100 
            ratio = min(w / img.width, h / img.height)
            new_w, new_h = int(img.width * ratio), int(img.height * ratio)
            
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl_big.config(image=photo)
            lbl_big.image = photo
        except Exception as e:
            lbl_big.config(text=f"顯示錯誤: {e}", fg="white")

    def update_status(self, msg, bg_color="yellow", text_color="black"):
        self.lbl_status.config(text=msg, bg=bg_color, fg=text_color)
        self.update_idletasks()

    def pick_file(self):
        f = filedialog.askopenfilename(
            title="請點選藥袋的照片",
            filetypes=[("圖片", "*.jpg *.jpeg *.png *.bmp"), ("所有檔案", "*")]
        )
        if f:
            self.image_path = Path(f)
            # [新增] 重置狀態：選新照片時，切換回「原圖模式」
            self.showing_result = False
            self.show_image(self.image_path, self.lbl_img, max_h=900)
            
            self.update_status("照片選好了！請按中間綠色的「開始分析」", bg_color="#90EE90", text_color="black")
            self.txt_result.config(state=tk.NORMAL)
            self.txt_result.delete(1.0, tk.END)
            self.txt_result.insert(tk.END, "照片已載入。\n如需看大圖，請直接點擊照片。")
            self.txt_result.config(state=tk.DISABLED)
            
            self.lbl_icon.config(image='', text="準備中...")
            self.btn_2.state(["!disabled"])
            self.btn_3.state(["disabled"])

    def show_image(self, path, label_widget, max_h=300):
        if not path or not path.exists():
            return
        try:
            img = Image.open(path)
            target_w = label_widget.winfo_width()
            if target_w < 50: target_w = 500
            
            ratio = min(target_w / img.width, max_h / img.height)
            new_w = int(img.width * ratio)
            new_h = int(img.height * ratio)
            
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            label_widget.config(image=photo, text="")
            label_widget.image = photo 
        except Exception as e:
            label_widget.config(text=f"無法顯示圖片\n{e}")

    def start_analysis(self):
        if not self.image_path:
            return
        if self.is_processing:
            return
        self.is_processing = True
        self.btn_1.state(["disabled"])
        self.btn_2.state(["disabled"])
        threading.Thread(target=self._run_pipeline, daemon=True).start()

    def _run_pipeline(self):
        try:
            self.update_status("正在讀取文字... (請稍候)", bg_color="#FFD700")
            extract_cmd = [
                sys.executable, str(APP_DIR / "extract.py"),
                str(self.image_path),
                "--out_json", str(OUT_JSON),
                "--template", "tvgh", 
                "--lang", "chi_tra+eng",
                "--psm", "6"
            ]
            run_cmd_silent(extract_cmd)

            self.update_status("正在轉換成聲音... (快好了)", bg_color="#FFA500")
           
            speak_cmd = [
                sys.executable, str(APP_DIR / "speak.py"),
                str(OUT_JSON),
                "--out_audio", str(OUT_AUDIO)
            ]
            print("SPEAK CMD =", speak_cmd, flush=True)

            run_cmd_silent(speak_cmd)

            self.update_status("正在畫圖說明...", bg_color="#FF8C00")
            image_cmd = [
                PYTHON, str(APP_DIR / "image.py"),
                str(OUT_JSON),
                "--out_img", str(OUT_USAGE)
            ]
            run_cmd_silent(image_cmd)
            self.after(100, self._on_success)
                
        except Exception:
            import traceback
            err = traceback.format_exc()
            self.after(100, lambda err=err: messagebox.showerror("哎呀", f"讀取失敗了：\n{err}"))
            self.after(100, self._reset_ui_error)

        """
        except Exception as e:
            self.after(100, lambda: messagebox.showerror("哎呀", f"讀取失敗了：{e}"))
            self.after(100, self._reset_ui_error)
"""
    def _on_success(self):
        # [新增] 更新狀態：分析完成，現在是「結果模式」
        self.showing_result = True
        self.show_image(OUT_PREVIEW, self.lbl_img, max_h=900)
        self.show_image(OUT_USAGE, self.lbl_icon, max_h=900)
        
        import json
        if OUT_JSON.exists():
            try:
                data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
                name = data.get("patient_name", "病患")
                med = data.get("medicine_name", "藥品")
                usage = data.get("usage_dosage", "請詳閱說明")
                display_text = f"【姓名】 {name}\n【藥名】 {med}\n【用法】 {usage}"
                
                self.txt_result.config(state=tk.NORMAL)
                self.txt_result.delete(1.0, tk.END)
                self.txt_result.insert(tk.END, display_text)
                self.txt_result.config(state=tk.DISABLED)
            except:
                pass

        self.update_status("完成！正在播放聲音... (可按橘色按鈕重聽)", bg_color="#32CD32", text_color="white")
        self.is_processing = False
        self.btn_1.state(["!disabled"])
        self.btn_2.state(["!disabled"])
        self.btn_3.state(["!disabled"])
        play_audio_file(OUT_AUDIO)

    def _reset_ui_error(self):
        self.is_processing = False
        self.btn_1.state(["!disabled"])
        self.btn_2.state(["!disabled"])
        self.update_status("發生錯誤，請重新選照片試試看", bg_color="red", text_color="white")

def main():
    app = ElderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
