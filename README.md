# 英语作文自动批改工具

## 简介

本项目是一个基于 Python 的桌面应用，支持图片 OCR 识别和 AI 自动批改高中英语作文。支持 DeepSeek、ChatGPT 等多种大模型 API，支持自定义评分标准，适合教师和学生批量处理英语作文。

## 主要功能

- 图片 OCR 识别（Tesseract-OCR，支持中英文混合）
- 支持 DeepSeek、ChatGPT 等主流大模型 API
- 支持自定义评分标准
- 批量处理多张作文图片
- 评分结果自动写入图片和文本
- 自动统计 API token 用量
- 配置文件自动保存/加载
- Windows 下自动检测/搜索 Tesseract-OCR 路径

## 环境依赖

- Python 3.7 及以上
- 依赖库：
  - tkinter
  - pillow
  - pytesseract
  - requests
  - openai（如需用 ChatGPT/DeepSeek）

安装依赖：

```bash
pip install pillow pytesseract requests openai
```

> **注意：**
> - Windows 用户需安装 [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) 并确保配置好路径。程序会自动检测或全盘搜索 tesseract.exe，并写入配置文件。
> - Mac/Linux 用户可用包管理器安装 tesseract。

## 使用方法

1. 克隆或下载本项目到本地
2. 安装依赖
3. 运行主程序

```bash
python auto_essay_grader.py
```

4. 按界面提示，配置 API Key、评分标准等参数
5. 选择需要批改的作文图片，点击“开始批改”

## 配置说明

- `aeg_config.ini`：保存 API 类型、Key、评分标准、Tesseract 路径等信息
- `debug.log`：程序运行日志
- Windows 下 `OCR` 配置节会自动写入 tesseract 的绝对路径

## 常见问题

- **Tesseract-OCR 未安装/找不到**  
  按提示下载安装，或手动指定路径，或等待程序自动全盘搜索。
- **API Key 无效/额度不足**  
  检查 API Key 是否正确，或更换其他模型接口。

## 许可协议

仅供学习与交流，禁止商业用途。

---

如有建议或问题，欢迎提交 Issue！
