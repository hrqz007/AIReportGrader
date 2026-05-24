from __future__ import annotations

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    ok: bool = True
    message: str = ""
    data: object | None = None


class CourseCreate(BaseModel):
    course_name: str = Field(min_length=1)
    course_type: str = "理论+实验课程"
    semester: str | None = None
    description: str | None = None


class CourseUpdate(CourseCreate):
    pass


class TeachingClassCreate(BaseModel):
    class_name: str = Field(min_length=1)
    description: str | None = None
    course_id: int | None = None


class TeachingClassUpdate(BaseModel):
    class_name: str = Field(min_length=1)
    description: str | None = None


class CourseClassLinkCreate(BaseModel):
    course_id: int
    class_id: int


class StudentCreate(BaseModel):
    student_no: str = Field(min_length=1)
    student_name: str = Field(min_length=1)
    class_name: str | None = None


class StudentUpdate(BaseModel):
    student_no: str = Field(min_length=1)
    student_name: str = Field(min_length=1)
    class_name: str | None = None


class ExperimentCreate(BaseModel):
    course_id: int
    experiment_name: str = Field(min_length=1)
    experiment_objectives: str | None = None
    experiment_requirements: str | None = None
    required_screenshots: str | None = None
    key_evaluation_points: str | None = None
    common_errors: str | None = None
    special_notes: str | None = None


class ExperimentUpdate(BaseModel):
    experiment_name: str = Field(min_length=1)
    experiment_objectives: str | None = None
    experiment_requirements: str | None = None
    required_screenshots: str | None = None
    key_evaluation_points: str | None = None
    common_errors: str | None = None
    special_notes: str | None = None


class ExperimentClone(BaseModel):
    source_experiment_id: int
    target_course_id: int
    experiment_name: str | None = None


class RubricItemCreate(BaseModel):
    experiment_id: int
    item_name: str = Field(min_length=1)
    max_score: float
    description: str | None = None
    deduction_rules: str | None = None
    requires_review: bool = False
    sort_order: int = 0


class RubricItemUpdate(BaseModel):
    item_name: str = Field(min_length=1)
    max_score: float
    description: str | None = None
    deduction_rules: str | None = None
    requires_review: bool = False
    sort_order: int = 0


class GradingTaskCreate(BaseModel):
    task_name: str = Field(min_length=1)
    course_id: int
    class_id: int
    experiment_id: int
    description: str | None = None


class GradingTaskUpdate(BaseModel):
    task_name: str = Field(min_length=1)
    description: str | None = None
    status: str = "进行中"


class SubmissionMatchUpdate(BaseModel):
    student_id: int
    match_status: str = "已匹配"


class AIProviderCreate(BaseModel):
    provider_name: str = Field(min_length=1)
    provider_type: str = "openai_compatible"
    base_url: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    text_model: str = Field(min_length=1)
    vision_model: str | None = None
    analysis_model: str | None = None
    supports_vision: bool = False
    supports_json: bool = True
    is_default: bool = False
    enabled: bool = True


class AIProviderUpdate(BaseModel):
    provider_name: str = Field(min_length=1)
    provider_type: str = "openai_compatible"
    base_url: str = Field(min_length=1)
    api_key: str | None = None
    text_model: str = Field(min_length=1)
    vision_model: str | None = None
    analysis_model: str | None = None
    supports_vision: bool = False
    supports_json: bool = True
    is_default: bool = False
    enabled: bool = True


class ReviewScoreItem(BaseModel):
    rubric_item_id: int | None = None
    item_name: str = ""
    max_score: float = 0
    ai_score: float = 0
    teacher_score: float = 0
    teacher_comment: str | None = None
    deduction_reason: str | None = None
    confidence: str | None = None
    need_teacher_review: bool = False


class ReviewSave(BaseModel):
    score_rows: list[ReviewScoreItem]
    overall_comment: str | None = None
    reviewer_name: str | None = None
    mark_completed: bool = True
