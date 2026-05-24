# 实验智评：面向高校课程实验报告的智能评阅系统

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-42b883?logo=vue.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Local_DB-003B57?logo=sqlite&logoColor=white)
![Kimi](https://img.shields.io/badge/Kimi_K2.6-API-0f766e)

“实验智评”是一个面向高校课程实验报告评阅场景的本地化智能评阅系统。系统支持教师建立课程、教学班、实验任务和评分标准，批量上传学生实验报告，完成报告解析、图片提取、脱敏处理、AI 建议评分、教师复核、成绩导出与班级分析。

系统定位是：**让 AI 承担实验报告初评和分项诊断工作，教师保留最终成绩确认权。**

---

## 核心能力

- **课程与教学班管理**：支持按学期维护课程，教学班可与课程关联使用。
- **学生名单管理**：支持 Excel 模板下载、名单导入、基础班级名单和课程名单副本维护。
- **实验任务管理**：为不同课程和学期建立实验任务，可复用历史实验任务与评分标准。
- **评分标准配置**：支持分项评分、满分、扣分规则、重点复核标记和通用模板生成。
- **批改任务创建**：以“课程 + 教学班 + 实验任务 + 评分标准”为单位建立批改任务。
- **报告批量上传与匹配**：支持根据文件名中的学号、姓名自动匹配学生，支持人工处理未匹配和重复提交。
- **报告解析与脱敏**：支持 `.docx`、`.doc`、`.pdf` 实验报告解析，提取正文、表格、图片并生成脱敏文本。
- **AI 初评**：支持接入 Kimi K2.6 API，按评分标准生成 AI 建议分和扣分依据。
- **教师复核**：教师可查看报告预览、分项修改分数、确认最终成绩。
- **成绩导出与班级分析**：支持成绩表、分项成绩和班级分析结果导出。
- **系统数据管理**：支持本地数据备份、恢复、清空和迁移。

---

## 支持的报告格式

| 格式 | 支持情况 | 说明 |
|---|---|---|
| `.docx` | 支持 | 可解析正文、表格和内嵌图片 |
| `.doc` | 支持 | 通过内置 LibreOffice 转换后解析 |
| `.pdf` | 支持 | 可提取文本，并可将页面渲染为图片 |

说明：扫描版 PDF 如果没有可复制文字层，当前版本主要按图片页面处理，尚未内置 OCR。

---

## 技术架构

| 层次 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Element Plus |
| 后端 | FastAPI |
| 数据库 | SQLite，本地保存 |
| 文档处理 | python-docx、PyMuPDF、pypdf、LibreOffice |
| 表格处理 | pandas、openpyxl |
| AI 调用 | Kimi K2.6 API，采用兼容式大模型接口 |
| 运行方式 | 本地单机运行，可打包为便携版 |

---

## 推荐使用方式

普通教师试用时，建议下载项目发布页中的便携版压缩包。解压后双击：

```text
启动实验智评V2.bat
```

系统启动后会自动打开浏览器。如果没有自动打开，可以手动访问：

```text
http://127.0.0.1:8000
```

运行时请不要关闭命令行窗口，关闭后系统会停止运行。

---

## 源码运行方式

如果从源码运行，需要准备：

- Python 3.11+
- Node.js LTS
- npm

安装后端依赖：

```powershell
cd backend
pip install -r requirements.txt
```

安装并构建前端：

```powershell
cd frontend
npm install
npm run build
```

回到项目根目录启动：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

---

## AI 配置说明

系统不内置任何 API Key。首次使用 AI 初评前，需要在“AI 模型配置”页面填写教师自己的模型服务配置。

推荐配置示例：

| 字段 | 示例 |
|---|---|
| 服务商 | Kimi |
| API Base URL | `https://api.moonshot.cn/v1` |
| 文本模型 | `kimi-k2.6` |
| 视觉模型 | `kimi-k2.6` |

API Key 仅保存在本地 SQLite 数据库中。导出或备份数据时，请注意是否包含 API Key。

---

## 教学使用流程

1. 配置 Kimi K2.6 API。
2. 创建课程、教学班和学期信息。
3. 导入或维护学生名单。
4. 创建实验任务并配置评分标准。
5. 创建批改任务。
6. 批量上传学生实验报告。
7. 系统自动匹配学生并解析报告。
8. 执行 AI 初评，得到分项建议分。
9. 教师逐份复核并确认最终成绩。
10. 导出成绩表和班级分析结果。

---

## 数据与隐私

- 系统默认本地运行，不需要公网部署。
- 学生姓名、学号、班级等实名信息保存在本地数据库。
- 发送给 AI 的正文使用脱敏文本。
- AI 结果仅作为建议分，最终成绩以教师确认分为准。
- 当前版本不包含学生端，也不包含多教师权限管理。

---

## 版本说明

- `main`：当前 V2 稳定源码。
- `v2-vue-fastapi-doc-pdf`：V2 独立开发分支。
- `v1-streamlit-archive`：原 Streamlit 版归档分支。
- `v2.0-vue-fastapi-doc-pdf`：当前 V2 发布标签。

---

## 适用场景

本系统适用于计算机、数据科学、工程技术及其他包含实验报告评价环节的高校课程。特别适合需要批量批改实验报告、保留评分依据、进行分项反馈和班级共性问题分析的教学场景。

