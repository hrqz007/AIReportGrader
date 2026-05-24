# 实验智评 V2 自动回归测试

本目录用于放置不会污染真实教学数据的自动化检查脚本。

## 核心链路测试

运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run-smoke-regression.ps1
```

测试脚本会创建临时数据库、临时上传目录和临时导出目录，覆盖以下流程：

- 创建课程、教学班和课程名单副本
- 创建实验任务和评分标准
- 创建批改任务
- 上传并解析 `.docx` 实验报告
- 写入模拟 AI 分项评分结果
- 初始化并保存教师复核结果
- 生成成绩预览和班级分析预览
- 批量删除提交记录

脚本结束后会自动清理临时数据，不会改动 `backend/data/app.db`、`backend/uploads` 或 `backend/exports` 中的真实数据。
