# 智能问答系统

这是一个基于向量检索的智能问答系统，能够从预设知识库中检索相关信息并回答用户问题。

## 功能特点

- 基于向量检索的高效知识匹配
- 支持多种文档格式的知识库导入
- 提供Web界面进行交互
- 支持特殊关键词的精确搜索
- 包含文本去重、网页爬取等辅助功能

## 目录结构

```
├── app.py              # 主应用程序入口
├── web_scraper.py      # 网页爬取工具
├── text_deduplication.py # 文本去重工具
├── knowledge/          # 知识库文件夹
├── db/                 # 数据库文件夹
├── templates/          # Web模板文件夹
└── 1-6.py              # 各个功能模块的拆分文件
```

## 安装环境

1. 确保已安装Python 3.8+
2. 创建虚拟环境（可选但推荐）
   ```bash
   python -m venv .venv
   ```
3. 激活虚拟环境
   ```bash
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```
4. 安装依赖包
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. 在`knowledge`文件夹中添加您的知识库文档
2. 运行主应用程序
   ```bash
   python app.py
   ```
3. 打开浏览器访问 `http://localhost:5000`

## 开发说明

- `app.py`: Flask应用，提供Web界面和API接口
- `web_scraper.py`: 用于从网页爬取内容并保存到知识库
- `text_deduplication.py`: 用于去除知识库中的重复内容
- 向量数据库使用ChromaDB，存储在`db/chroma_demo`目录

## 知识库格式

知识库支持文本文件(.txt)格式，每个文件将作为一个知识源被导入系统。

## 许可证

[MIT License](LICENSE)

## 贡献指南

欢迎提交Issue和Pull Request！

## 联系方式

如有问题，请通过Issues与我们联系。