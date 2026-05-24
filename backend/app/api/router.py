from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import ai_providers, archives, classes, courses, experiments, exports, grading_tasks, health, reviews, rubrics, scoring, students, submissions, system_data


api_router = APIRouter()
api_router.include_router(health.router, tags=["系统状态"])
api_router.include_router(courses.router, prefix="/courses", tags=["课程"])
api_router.include_router(classes.router, prefix="/classes", tags=["教学班"])
api_router.include_router(students.router, prefix="/students", tags=["学生名单"])
api_router.include_router(archives.router, prefix="/archives", tags=["归档管理"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["实验任务"])
api_router.include_router(rubrics.router, prefix="/rubrics", tags=["评分标准"])
api_router.include_router(grading_tasks.router, prefix="/grading-tasks", tags=["批改任务"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["提交记录"])
api_router.include_router(ai_providers.router, prefix="/ai-providers", tags=["AI 配置"])
api_router.include_router(scoring.router, prefix="/scoring", tags=["AI 初评"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["教师复核"])
api_router.include_router(exports.router, prefix="/exports", tags=["成绩导出与分析"])
api_router.include_router(system_data.router, prefix="/system-data", tags=["系统数据管理"])
