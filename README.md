# 实验智评 V2 重构版

本目录用于开发“实验智评：面向高校课程实验报告的智能评阅系统”的 V2 工程化重构版本。

## 与 V1 的关系

- V1 原系统目录：`D:\codex\AIReportGrader`
- V2 重构目录：`D:\codex\AIReportGrader_V2`
- V1 保持不变，可继续作为 Streamlit 申报版使用。
- V2 采用前后端分离架构，目标是面向真实教学使用和后续分发给其他教师。

## 技术架构

- 前端：Vue 3 + Vite + Element Plus
- 后端：FastAPI + SQLite
- AI 调用：兼容式大模型 API，当前主要适配 Kimi K2.6 API
- 文件处理：`.docx`、`.doc`、`.pdf` 报告解析，Word/PDF 预览，图片提取，Excel 导入导出
- 本地运行：默认单机运行，不要求公网部署

## 当前已实现的主要功能

- 课程管理
- 教学班管理
- 班级基础名单与课程名单副本管理
- 学生名单 Excel 导入、模板下载、名单维护与导出
- 实验任务管理
- 评分标准管理与通用评分标准模板生成
- 批改任务创建
- 实验报告批量上传、文件名解析和学生匹配
- 提交记录人工匹配、重复提交处理和批量删除
- 报告解析、正文提取、图片提取和脱敏文本生成
- AI 模型配置、默认配置和连接测试
- AI 初评、批量初评、单份初评和结果查看
- 教师复核、逐项改分、最终成绩确认
- 成绩预览、Excel 导出和班级分析
- 系统数据备份、恢复、清空和整体数据管理

## 推荐启动方式

如果只是正常使用系统，双击根目录下的：

```text
启动实验智评V2.bat
```

启动后访问：

```text
http://127.0.0.1:8000
```

当前启动器会优先使用本目录下的内置便携 Python 运行环境：

```text
runtime/python/python.exe
```

因此，如果压缩包中包含 `runtime/`、`backend/`、`frontend/dist/`、`scripts/` 和启动脚本，普通教师使用时不需要单独安装 Python、Node.js 或 npm。

运行时请不要关闭命令行窗口；关闭后系统会停止运行。

> 说明：GitHub 源码仓库通常不提交 `runtime/` 内置运行环境、LibreOffice 和业务数据文件。面向普通教师分发时，请使用 `scripts/package-release.ps1` 生成便携版压缩包，便携版会包含 Python 运行环境和已解压的 LibreOffice 文档转换环境。

## 开发启动方式

开发调试时可以双击：

```text
启动实验智评V2_开发版.bat
```

开发版会分别启动：

- 后端接口服务：`http://127.0.0.1:8000`
- 前端开发服务：`http://127.0.0.1:5173`

开发环境需要：

- Python 3.11+
- Node.js LTS 和 npm

如果修改了前端代码，需要在 `frontend/` 目录执行：

```powershell
npm install
npm run build
```

然后再使用推荐启动方式运行系统。

## 生成便携版压缩包

在 V2 根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\package-release.ps1
```

脚本会生成：

```text
release/实验智评V2_便携版_时间戳/
release/实验智评V2_便携版_时间戳.zip
```

便携版包含：

- 后端代码
- 前端构建产物
- 内置 Python 运行环境
- 内置 LibreOffice 文档转换环境
- 启动脚本
- 使用说明

默认不打包当前业务数据库、上传文件和导出文件。教师第一次启动时会自动创建新的本地数据库。

## 数据位置

V2 运行数据位于：

```text
backend/data/app.db
backend/uploads/
backend/exports/
```

如需换电脑、演示或备份，请优先使用系统内的“系统数据管理”页面进行完整备份和恢复。

## 注意事项

1. AI 初评需要教师自行配置可用的大模型 API。
2. API Key 仅保存在本地数据库中，备份时请注意是否包含 API Key。
3. AI 初评结果只是建议分，最终成绩以教师确认分为准。
4. 当前版本支持 `.docx`、`.doc` 和 `.pdf` 实验报告；其中 `.doc` 预览与解析依赖内置 LibreOffice 转换能力。
5. 本系统面向本地教学使用，不包含学生端和多教师权限系统。
