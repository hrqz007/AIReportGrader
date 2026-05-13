[README.md](https://github.com/user-attachments/files/27706207/README.md)
# 实验智评：面向高校课程实验报告的智能评阅系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-2563eb?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Streamlit-Local%20App-ef4444?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/SQLite-Local%20Database-0f766e?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Kimi%20K2.6-API-7c3aed?style=for-the-badge" alt="Kimi K2.6 API">
</p>

<p align="center">
  <strong>面向高校课程实验报告评阅场景的本地化智能评阅系统</strong>
</p>

<p align="center">
  支持课程与教学班管理、学生名单导入、实验任务与评分标准配置、实验报告批量上传、报告解析与脱敏、AI 建议评分、教师复核、成绩导出与班级分析。
</p>

---

## 项目简介

**实验智评** 是一个面向高校课程实验报告评阅场景的本地化智能评阅系统。

系统支持教师创建课程、教学班、实验任务和评分标准，批量上传学生实验报告，调用可配置的大模型 API 对实验报告正文与截图进行辅助分析，生成 **AI 建议分、扣分依据和反馈参考**。教师可在系统中逐份复核并确认最终成绩，最终导出成绩表、分项成绩表和班级分析结果。

> 申报案例名称：**实验智评：面向高校课程实验报告的智能评阅系统开发与应用**

---

## 核心定位

实验智评不是学生端系统，也不是自动替代教师评分的系统。

它的定位是：

> **为高校教师提供一个本地运行的实验报告智能评阅辅助工具，让 AI 负责生成建议分和诊断线索，让教师负责最终复核与成绩确认。**

---

## 功能总览

| 模块 | 已实现能力 |
|---|---|
| AI 模型配置 | 支持配置 Kimi K2.6 API 等通用兼容 API，支持文本模型、视觉模型、默认配置和连接测试 |
| 课程与教学班管理 | 支持课程、教学班独立管理，支持课程与教学班多对多关联 |
| 学生名单导入 | 支持 Excel 模板下载、班级基础名单导入、课程名单副本维护 |
| 实验任务管理 | 支持配置实验目标、实验要求、必须截图、重点检查内容和常见错误 |
| 评分标准管理 | 支持分项评分标准、满分、扣分规则、重点复核和通用模板生成 |
| 批改任务管理 | 支持按课程、教学班、实验任务创建批改任务 |
| 报告上传匹配 | 支持批量上传 `.docx` 报告，按文件名解析学号姓名并自动匹配学生 |
| 报告解析脱敏 | 支持提取 Word 正文、表格、图片，检测并脱敏姓名、学号、班级等敏感信息 |
| AI 初评 | 支持单份和批量 AI 初评，生成分项建议分、扣分原因和复核提示 |
| 教师复核 | 支持 Word 预览、截图查看、分项改分、教师确认总分和复核备注 |
| 成绩导出分析 | 支持成绩 Excel 导出、分项成绩导出、班级统计图表和班级分析 Excel |

---

## 典型使用流程

```text
配置 AI 模型
    ↓
创建课程与教学班
    ↓
导入学生名单
    ↓
创建实验任务
    ↓
配置评分标准
    ↓
创建批改任务
    ↓
批量上传实验报告
    ↓
解析报告与文本脱敏
    ↓
AI 初评生成建议分
    ↓
教师逐份复核确认
    ↓
导出成绩与班级分析
```

---

## 快速开始

### 方式一：Windows 双击启动

适合普通使用者。

1. 安装 **Python 3.11 或更高版本**。
2. 下载本项目并解压。
3. 双击项目根目录中的：

```text
启动实验智评.bat
```

首次运行时，启动器会自动：

- 创建本地虚拟环境 `.venv`
- 安装依赖
- 启动 Streamlit
- 打开或提示访问 `http://localhost:8501`

如果浏览器没有自动打开，请手动访问：

```text
http://localhost:8501
```

### 方式二：命令行启动

适合开发者或熟悉命令行的用户。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

---

## 运行环境

| 环境 | 要求 |
|---|---|
| 操作系统 | Windows 优先；其他系统可通过命令行运行 |
| Python | 3.11 或更高版本 |
| 浏览器 | Chrome、Edge 或其他现代浏览器 |
| 网络 | 首次安装依赖需要联网；AI 初评需要访问所配置的大模型 API |
| 数据库 | SQLite，本地自动创建 |

---

## 依赖技术

| 技术 | 用途 |
|---|---|
| Streamlit | 本地 Web 界面 |
| SQLite | 本地数据存储 |
| pandas / openpyxl | Excel 导入导出 |
| python-docx | Word 实验报告解析 |
| Pillow | 图片压缩与处理 |
| Altair | 班级分析图表 |
| 通用兼容 API SDK | 调用 Kimi K2.6 API 等模型服务 |

---

## 项目结构

```text
AIReportGrader/
├── app.py
├── requirements.txt
├── README.md
├── 启动实验智评.bat
├── run_app.ps1
├── .streamlit/
│   └── config.toml
├── data/
│   └── .gitkeep
├── uploads/
│   └── .gitkeep
├── exports/
│   └── .gitkeep
├── pages/
│   ├── 1_AI模型配置.py
│   ├── 2_课程与班级管理.py
│   ├── 3_学生名单导入.py
│   ├── 4_实验任务与评分标准.py
│   ├── 5_批改任务与报告上传.py
│   ├── 6_AI初评.py
│   ├── 7_教师复核.py
│   └── 8_成绩导出与班级分析.py
├── src/
│   ├── db.py
│   ├── schema.py
│   ├── services/
│   ├── ui/
│   └── utils/
└── docs/
```

---

## 数据安全说明

系统采用本地运行方式，核心数据默认保存在本机项目目录中。

| 数据类型 | 保存位置 |
|---|---|
| SQLite 数据库 | `data/app.db` |
| 上传实验报告 | `uploads/` |
| 提取图片 | `uploads/{task_id}/images/` |
| 导出成绩表 | `exports/` |
| AI 配置 | 本地 SQLite 数据库 |

重要说明：

- API Key 不写死在代码中。
- 学生真实姓名、学号、班级保存在本地。
- 发送给 AI 的报告文本使用脱敏文本。
- 截图内容当前不做自动脱敏，启用图文评分前需教师确认截图中不含敏感信息。
- AI 初评结果仅作为建议分，最终成绩以教师确认分为准。

---

## 当前版本边界

当前 V1.0 申报版已经实现完整的本地评阅闭环，但仍有明确边界：

| 能力 | 当前状态 |
|---|---|
| `.docx` 实验报告解析 | 已支持 |
| PDF 实验报告解析 | 暂不支持 |
| 学生端 | 暂不支持 |
| 多教师账号与权限 | 暂不支持 |
| 公网部署 | 暂不作为 V1.0 核心功能 |
| 文本脱敏 | 已支持 |
| 截图自动脱敏 | 暂不支持 |
| AI 建议评分 | 已支持 |
| 教师最终确认 | 已支持 |

---

## GitHub 使用建议

如果你是直接从 GitHub 下载使用：

1. 点击仓库右上角 `Code`。
2. 选择 `Download ZIP`。
3. 解压到本地文件夹。
4. 安装 Python 3.11+。
5. 双击 `启动实验智评.bat`。

如果首次安装依赖时出现 PyPI、SSL 或网络错误，可以换网络后重试。启动器会自动尝试默认 PyPI、清华镜像和阿里云镜像。

---



## 开发方式说明

本系统围绕真实教学场景进行需求分析、流程设计和评价规则设计，开发过程中借助 Kimi 网页对话框进行方案推演与提示词设计，使用 Trae 编程工具接入 Kimi K2.6 模型辅助完成系统代码开发、调试和页面优化，最终经教师人工测试、修改和复核形成 V1.0 申报版。

---

## 许可与使用

本项目用于教学应用案例展示、课程实验报告评阅辅助和后续研究积累。若用于真实教学环境，请根据所在单位的数据安全要求管理学生名单、实验报告和 API Key。
