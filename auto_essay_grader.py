import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import configparser
import os
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import requests
import threading
import sys
import datetime
import shutil
import webbrowser
import logging
import glob

# 全局 system prompt，作为批改作文的基础指令
SYSTEM_PROMPT = (
    '''
    You are a helpful assistant，帮助用户批改高中英语作文
    1.优先使用中文回答
    2.除非用户要求输出其他内容，否则不要过多分析只输出分数，不要建议
    3.识别不到就打0分
    4.无论何时输出分数都用这个格式：<score>**分</>，方便中介程序调用
    '''
)

# 日志配置，记录调试信息到 debug.log 文件
logging.basicConfig(
    filename="debug.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
    encoding="utf-8"
)

CONFIG_FILE = "aeg_config.ini"

def find_tesseract_on_windows():
    # 全盘搜索 tesseract.exe（只搜 C 盘，速度快些）
    for root_dir in ["C:\\"]:
        for path in glob.glob(os.path.join(root_dir, "**", "tesseract.exe"), recursive=True):
            if os.path.exists(path):
                return path
    return None

class EssayGraderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("英语作文自动批改")
        self.api_type = tk.StringVar()
        self.api_key = tk.StringVar()
        self.deepseek_deepthink = tk.BooleanVar()
        self.save_money_mode = tk.BooleanVar()
        self.prompt_title = tk.StringVar()
        self.prompt_criteria = tk.StringVar()
        self.image_paths = []
        self.log_var = tk.StringVar()
        self.tesseract_path = None
        self.load_config()
        self.setup_tesseract_path()
        self.create_gui()
        # 初始化评分标准到文本框
        self.text_criteria.delete("1.0", "end")
        self.text_criteria.insert("1.0", self.prompt_criteria.get())

    def load_config(self):
        """加载配置文件，初始化各项参数"""
        self.config = configparser.ConfigParser()
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config.read_file(f)
                self.api_type.set(self.config.get("API", "type", fallback="ChatGPT"))
                self.api_key.set(self.config.get("API", "key", fallback=""))
                self.deepseek_deepthink.set(self.config.getboolean("API", "deepthink", fallback=True))
                self.save_money_mode.set(self.config.getboolean("API", "savemoney", fallback=False))
                # 读取评分标准并将\n还原为换行
                raw_criteria = self.config.get("PROMPT", "criteria", fallback="")
                raw_criteria = raw_criteria.replace('\\n', '\n')
                self.prompt_criteria.set(raw_criteria)
                self.tesseract_path = self.config.get("OCR", "tesseract_path", fallback=None)
            else:
                raise Exception("aeg_config.ini不存在")
        except Exception as e:
            # 配置文件损坏或格式错误，重置为默认配置
            print(f"配置文件损坏或格式错误，已重置为默认配置。错误信息: {e}")
            self.api_type.set("Deepseek")
            self.api_key.set("")
            self.deepseek_deepthink.set(True)
            self.save_money_mode.set(False)
            self.prompt_criteria.set("")
            self.save_config()  # 直接覆盖旧config，保证下次启动正常

        # 同步评分标准到文本框
        if hasattr(self, "text_criteria"):
            self.text_criteria.delete("1.0", "end")
            self.text_criteria.insert("1.0", self.prompt_criteria.get())

    def save_config(self):
        """保存当前配置到文件"""
        # 保存前同步变量
        if hasattr(self, "text_criteria"):
            self.prompt_criteria.set(self.text_criteria.get("1.0", "end-1c"))
        if not self.config.has_section("API"):
            self.config.add_section("API")
        if not self.config.has_section("PROMPT"):
            self.config.add_section("PROMPT")
        if not self.config.has_section("OCR"):
            self.config.add_section("OCR")
        # 用\n替换换行，保存为一行
        criteria = self.prompt_criteria.get().replace('\n', '\\n')
        self.config.set("API", "type", self.api_type.get())
        self.config.set("API", "key", self.api_key.get())
        self.config.set("API", "deepthink", str(self.deepseek_deepthink.get()))
        self.config.set("API", "savemoney", str(self.save_money_mode.get()))
        self.config.set("PROMPT", "criteria", criteria)
        if self.tesseract_path:
            self.config.set("OCR", "tesseract_path", self.tesseract_path)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            self.config.write(f)

    def setup_tesseract_path(self):
        if sys.platform.startswith("win"):
            if self.tesseract_path and os.path.exists(self.tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            else:
                # 没有配置或路径失效，自动搜索
                found = find_tesseract_on_windows()
                if found:
                    self.tesseract_path = found
                    pytesseract.pytesseract.tesseract_cmd = found
                    self.save_config()
                else:
                    messagebox.showerror("Tesseract-OCR未找到", "未能自动找到Tesseract-OCR，请手动安装并配置。")
                    sys.exit(1)

    def create_gui(self):
        # 设置窗口默认大小更大一些
        self.root.geometry("700x400")
        self.root.resizable(False, False)  # 禁用全屏和缩放

        # 右上角菜单优化
        menubar = tk.Menu(self.root)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="API设置", command=self.open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="设置", menu=settings_menu)
        self.root.config(menu=menubar)

        # 作文题目
        tk.Label(self.root, text="作文题目:").grid(row=0, column=0, sticky="ne")
        self.text_title = tk.Text(self.root, height=3, width=60, wrap="word")
        self.text_title.grid(row=0, column=1, padx=5, pady=5, sticky="we")
        # 支持鼠标滚轮
        self.text_title.bind("<MouseWheel>", lambda e: self.text_title.yview_scroll(int(-1*(e.delta/120)), "units"))
        # 自动同步变量
        def update_title_var(event):
            self.prompt_title.set(self.text_title.get("1.0", "end-1c"))
        self.text_title.bind("<KeyRelease>", update_title_var)

        # 评分标准
        tk.Label(self.root, text="评分标准:").grid(row=1, column=0, sticky="ne")
        self.text_criteria = tk.Text(self.root, height=7, width=60, wrap="word")
        self.text_criteria.grid(row=1, column=1, padx=5, pady=5, sticky="we")
        self.text_criteria.bind("<MouseWheel>", lambda e: self.text_criteria.yview_scroll(int(-1*(e.delta/120)), "units"))
        def update_criteria_var(event):
            self.prompt_criteria.set(self.text_criteria.get("1.0", "end-1c"))
        self.text_criteria.bind("<KeyRelease>", update_criteria_var)

        # 文件选择
        self.btn_select = tk.Button(self.root, text="选择图片文件", command=self.select_files)
        self.btn_select.grid(row=2, column=0, padx=5, pady=10)
        self.lbl_selected = tk.Label(self.root, text="未选择文件")
        self.lbl_selected.grid(row=2, column=1, sticky="w")

        # 批改按钮
        self.btn_start = tk.Button(self.root, text="开始批改", command=self.start_grading)
        self.btn_start.grid(row=3, column=0, columnspan=2, pady=15)

        # 日志输出区
        self.log_label = tk.Label(self.root, textvariable=self.log_var, anchor="w", fg="blue", wraplength=600, justify="left")
        self.log_label.grid(row=4, column=0, columnspan=2, sticky="we", padx=5, pady=5)
        self.log_var.set("准备就绪。")

    def show_about(self):
        about_text = (
            "英语作文自动批改工具\n"
            "——支持图片OCR识别与AI自动评分\n\n"
            "使用说明：\n"
            "1. 选择作文图片文件（支持多选）\n"
            "2. 填写作文题目和评分标准\n"
            "3. 设置API密钥（首次使用需设置）\n"
            "4. 点击“开始批改”自动生成批改结果\n"
            "5.需要安装OCR模块：Tesseract-OCR\n\n"
            "作者：Eric_Terminal\n"
            "版本信息：\n"
            "v1.0.1 - 2025年5月\n"
            "Build 64"
        )
        messagebox.showinfo("关于", about_text)

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("API设置")
        tk.Label(win, text="API类型:").grid(row=0, column=0, sticky="e")
        api_type_cb = ttk.Combobox(win, textvariable=self.api_type, values=["Deepseek","ChatGPT-3.5(不建议)",], state="readonly")
        api_type_cb.grid(row=0, column=1)
        tk.Label(win, text="API密钥:").grid(row=1, column=0, sticky="e")
        tk.Entry(win, textvariable=self.api_key, width=40).grid(row=1, column=1)
        tk.Checkbutton(win, text="Deepseek深度思考", variable=self.deepseek_deepthink).grid(row=2, column=1, sticky="w")
        # 新增省钱模式及问号说明
        def show_savemoney_info():
            messagebox.showinfo("省钱模式说明", "开启后，批改任务会自动延迟到每日00:30-08:30进行（DeepSeek官网此时段有折扣），以节省API费用（需要修改系统睡眠时间保证电脑不会休眠）。")
        frame = tk.Frame(win)
        frame.grid(row=3, column=1, sticky="w")
        tk.Checkbutton(frame, text="省钱模式", variable=self.save_money_mode).pack(side="left")
        tk.Button(frame, text="?", command=show_savemoney_info, width=2).pack(side="left", padx=2)
        tk.Button(win, text="保存", command=lambda: [self.save_config(), win.destroy()]).grid(row=4, column=0, columnspan=2, pady=10)
        # 新增测试API按钮
        def test_api():
            self.log_var.set("正在测试API...")
            win.update()
            test_prompt = "This is a test essay.使用中文回答，回答“”测试成功”"
            result, _ = self.ask_ai(test_prompt)
            if result == "[AI批改失败]":
                self.log_var.set("API测试失败，请检查API密钥和网络。")
            else:
                self.log_var.set("API测试成功，返回内容：" + result[:100].replace('\n', ' '))
        tk.Button(win, text="测试API", command=test_api).grid(row=5, column=0, columnspan=2, pady=5)

        # 新增Deepseek余额直链按钮
        def open_deepseek_usage():
            webbrowser.open("https://platform.deepseek.com/usage")
        tk.Button(win, text="查看Deepseek余额", command=open_deepseek_usage).grid(row=6, column=0, columnspan=2, pady=5)

    def select_files(self):
        files = filedialog.askopenfilenames(
            title="选择作文图片",
            filetypes=[
                ("PNG 图片", "*.png"),
                ("JPEG 图片", "*.jpg"),
                ("JPEG 图片", "*.jpeg"),
                ("BMP 图片", "*.bmp"),
                #("所有图片", "*.png;*.jpg;*.jpeg;*.bmp"),
            ],
            multiple=True
        )
        if files and len(files) >= 1:
            self.image_paths = list(files)
            self.lbl_selected.config(text=f"已选择{len(self.image_paths)}张图片")
        elif files:
            messagebox.showwarning("提示", "请至少选择1张图片")
        else:
            self.lbl_selected.config(text="未选择文件")

    def start_grading(self):
        # 防止多次点击，立即提示
        self.log_var.set("正在批改，请稍候...")
        self.root.update()  # 立即刷新界面
        if self.save_money_mode.get():
            now = datetime.datetime.now()
            # 判断当前是否在00:30-08:30之外
            start = now.replace(hour=0, minute=30, second=0, microsecond=0)
            end = now.replace(hour=8, minute=30, second=0, microsecond=0)
            if not (start <= now <= end):
                # 计算下一个00:30
                if now < start:
                    wait_until = start
                else:
                    wait_until = (now + datetime.timedelta(days=1)).replace(hour=0, minute=30, second=0, microsecond=0)
                wait_seconds = (wait_until - now).total_seconds()
                messagebox.showinfo("省钱模式", f"省钱模式已开启，将于{wait_until.strftime('%Y-%m-%d %H:%M')}自动开始批改。\n\n你可以关闭本弹窗，届时会自动执行。")
                self.log_var.set(f"省钱模式：等待到{wait_until.strftime('%Y-%m-%d %H:%M')}再开始批改...")
                def delayed_start():
                    import time
                    time.sleep(wait_seconds)
                    self.root.after(0, self._real_start_grading)
                threading.Thread(target=delayed_start, daemon=True).start()
                return
        self._real_start_grading()

    def _real_start_grading(self):
        if not self.image_paths:
            messagebox.showerror("错误", "请先选择图片文件")
            return
        if not self.api_key.get():
            messagebox.showerror("错误", "请先设置API密钥")
            return
        if not self.prompt_title.get():
            messagebox.showerror("错误", "请填写作文题目")
            return
        if not self.prompt_criteria.get():
            messagebox.showerror("错误", "请填写评分标准")
            return
        self.save_config()
        threading.Thread(target=self._grading_worker, daemon=True).start()

    def _grading_worker(self):
        out_dir = os.path.join(os.path.dirname(self.image_paths[0]), "批改结果")
        os.makedirs(out_dir, exist_ok=True)
        for idx, img_path in enumerate(self.image_paths):
            text = self.ocr_image(img_path)
            prompt = f"作文题目：{self.prompt_title.get()}\n评分标准：{self.prompt_criteria.get()}\n学生作文：{text}\n请根据评分标准批改并给出建议。"
            result, usage = self.ask_ai(prompt)
            self.write_result_on_image(img_path, result, out_dir, usage)
            short_result = result[:100].replace('\n', ' ') + ("..." if len(result) > 100 else "")
            self.root.after(0, lambda idx=idx, short_result=short_result: self._update_progress(idx, short_result))
        self.root.after(0, lambda: self._grading_done(out_dir))

    def _update_progress(self, idx, short_result):
        self.lbl_selected.config(text=f"正在批改第{idx+1}/{len(self.image_paths)}张...")
        self.log_var.set(f"第{idx+1}张完成，AI回复：{short_result}")
        self.root.update()

    def _grading_done(self, out_dir):
        # 整合所有txt内容到total.txt，并统计总token
        try:
            import datetime
            txt_files = [f for f in os.listdir(out_dir) if f.lower().endswith(".txt") and f != "total.txt"]
            total_path = os.path.join(out_dir, "total.txt")
            total_prompt_tokens = 0
            total_completion_tokens = 0

            # 先统计所有token
            for txt_file in txt_files:
                file_path = os.path.join(out_dir, txt_file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # 简单正则提取token数
                import re
                prompt_match = re.search(r"上传token数:\s*(\d+)", content)
                completion_match = re.search(r"回复token数:\s*(\d+)", content)
                if prompt_match:
                    total_prompt_tokens += int(prompt_match.group(1))
                if completion_match:
                    total_completion_tokens += int(completion_match.group(1))

            # 写入统计和详细内容
            with open(total_path, "w", encoding="utf-8") as total_f:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                total_f.write(f"【统计时间】{now_str}\n")
                total_f.write(f"【总上传token数】: {total_prompt_tokens}\n")
                total_f.write(f"【总回复token数】: {total_completion_tokens}\n\n")
                for txt_file in txt_files:
                    file_path = os.path.join(out_dir, txt_file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    total_f.write(f"===== {txt_file} =====\n")
                    total_f.write(content)
                    total_f.write("\n\n")
        except Exception as e:
            print(f"整合txt失败: {e}")

        messagebox.showinfo("完成", f"全部批改完成，结果已保存到：{out_dir}")
        self.log_var.set("全部批改完成！")
        self.lbl_selected.config(text="未选择文件")
        self.image_paths = []

    def ocr_image(self, img_path):
        if sys.platform.startswith("win") and self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        try:
            img = Image.open(img_path)
            # 自动尝试中英文混合识别
            text = pytesseract.image_to_string(img, lang="eng+chi_sim")
            text = text.strip()
            # 简单清洗：去除多余空行
            text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
            print(f"OCR识别结果：{repr(text)}")  # 控制台输出便于调试
            if not text or len(text) < 10:
                return "[图片识别失败]"
            return text
        except Exception as e:
            print(f"OCR异常: {e}")
            return "[图片识别失败]"

    def ask_ai(self, prompt):
        if self.api_type.get() == "ChatGPT":
            return self.ask_chatgpt(prompt)
        else:
            return self.ask_deepseek(prompt)

    def ask_chatgpt(self, prompt):
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.api_key.get(),
                base_url="https://api.openai.com/v1"
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            logging.info("[ChatGPT] 发送内容: %r", messages)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=False
            )
            logging.info("[ChatGPT] 返回内容: %r", response.choices[0].message.content)
            usage = getattr(response, "usage", None)
            if usage:
                logging.info("[ChatGPT] usage: %r", usage)
            return response.choices[0].message.content, usage
        except Exception as e:
            logging.error("[ChatGPT] 异常: %s", e)
            return "[AI批改失败]", None

    def ask_deepseek(self, prompt):
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.api_key.get(),
                base_url="https://api.deepseek.com"
            )
            model_name = "deepseek-reasoner" if self.deepseek_deepthink.get() else "deepseek-chat"
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            logging.info("[DeepSeek] 发送内容: %r", messages)
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=False
            )
            content = response.choices[0].message.content
            reasoning_content = getattr(response.choices[0].message, "reasoning_content", None)
            usage = getattr(response, "usage", None)
            if usage:
                logging.info("[DeepSeek] usage: %r", usage)
            if reasoning_content:
                logging.info("[DeepSeek] 思维链: %r", reasoning_content)
                return content + "\n\n【思维链】\n" + reasoning_content, usage
            else:
                return content, usage
        except Exception as e:
            logging.error("[DeepSeek] 异常: %s", e)
            return "[AI批改失败]", None

    def write_result_on_image(self, img_path, result, out_dir, usage=None):
        try:
            import re
            match = re.search(r"<score>(.*?)</>", result)
            if match:
                score_text = match.group(1).strip()
            else:
                score_text = "无分数"

            img = Image.open(img_path).convert("RGB")
            width, height = img.size

            # 字体选择同前
            if sys.platform.startswith("win"):
                font_path_candidates = [
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/simsun.ttc",
                    "C:/Windows/Fonts/NotoSansSC-Regular.otf"
                ]
            elif sys.platform == "darwin":
                font_path_candidates = [
                    "/System/Library/Fonts/PingFang.ttc",
                    "/System/Library/Fonts/STHeiti Medium.ttc",
                    "/Library/Fonts/Songti.ttc",
                    "/Library/Fonts/SimHei.ttf",
                    "/Library/Fonts/NotoSansSC-Regular.otf"
                ]
            else:
                font_path_candidates = [
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                    "/usr/share/fonts/truetype/arphic/ukai.ttc",
                    "/usr/share/fonts/truetype/arphic/uming.ttc"
                ]

            font = None
            for font_path in font_path_candidates:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, 40)
                        break
                    except Exception:
                        continue
            if font is None:
                font = ImageFont.load_default()

            draw = ImageDraw.Draw(img)
            y = 5
            draw.text((20, y), score_text, fill=(255, 0, 0), font=font)

            img = img.convert("RGB")
            base = os.path.basename(img_path)
            img.save(os.path.join(out_dir, base))

            txt_name = os.path.splitext(base)[0] + ".txt"
            ocr_text = ""
            try:
                ocr_text = self.ocr_image(img_path)
            except Exception as e:
                ocr_text = "[获取OCR内容失败]"
            with open(os.path.join(out_dir, txt_name), "w", encoding="utf-8") as f:
                f.write("【OCR识别内容】\n")
                f.write(ocr_text + "\n\n")
                f.write("【AI批改内容】\n")
                f.write(result + "\n\n")
                if usage:
                    # 只写总token数
                    prompt_tokens = getattr(usage, "prompt_tokens", None)
                    completion_tokens = getattr(usage, "completion_tokens", None)
                    f.write("【API用量统计】\n")
                    if prompt_tokens is not None:
                        f.write(f"上传token数: {prompt_tokens}\n")
                    if completion_tokens is not None:
                        f.write(f"回复token数: {completion_tokens}\n")
        except Exception as e:
            print(f"P图失败: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EssayGraderApp(root)
    root.mainloop()