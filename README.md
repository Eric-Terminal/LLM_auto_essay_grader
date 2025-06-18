# 英语作文自动批改工具

本项目是一个基于 Tkinter 的桌面应用，支持自动识别图片中的英语作文内容，并调用大模型 API 进行自动评分。适用于高中英语作文批改场景，支持自定义评分标准，支持多种大模型接口。

## 功能特性

- 支持图片 OCR 识别，自动提取作文内容
- 支持 ChatGPT、DeepSeek 等多种大模型 API
- 支持自定义评分标准
- 支持批量处理多张图片
- 评分结果自动格式化，便于后续处理
- 日志记录与异常提示
- 配置文件自动保存与加载

## 环境依赖

- Python 3.7 及以上
- 依赖库：
  - tkinter
  - pillow
  - pytesseract
  - requests

安装依赖（推荐使用 pip）：

```bash
pip install pillow pytesseract requests
```

> **注意**：  
> - Windows 用户需安装 [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) 并配置好环境变量或手动指定路径。  
> - Mac/Linux 用户可通过包管理器安装 tesseract。

## 使用方法

1. 克隆本项目或下载源码到本地
2. 安装依赖
3. 运行主程序：

```bash
python auto_essay_grader.py
```

4. 按界面提示，配置 API Key、评分标准等参数
5. 选择需要批改的作文图片，点击“开始批改”即可

## 配置说明

- `aeg_config.ini`：保存 API 类型、Key、评分标准等配置信息
- `debug.log`：程序运行日志，便于排查问题

## 常见问题

- **Tesseract-OCR 未安装/找不到**  
  按提示下载安装并配置好路径，或参考[官方文档](https://github.com/tesseract-ocr/tesseract)。

- **API Key 无效/额度不足**  
  请检查 API Key 是否正确，或更换其他模型接口。

## 许可协议

本项目仅供学习与交流，禁止用于商业用途。

---

如有问题或建议，欢迎提交 Issue 或 PR！
