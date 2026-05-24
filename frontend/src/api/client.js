import axios from 'axios'

export const http = axios.create({
  baseURL: '/api',
  timeout: 30000
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message || '请求失败'
    error.userMessage = message
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('app-api-error', { detail: { message } }))
    }
    return Promise.reject(error)
  }
)

export const api = {
  health: () => http.get('/health'),
  listCourses: () => http.get('/courses'),
  createCourse: (payload) => http.post('/courses', payload),
  updateCourse: (id, payload) => http.put(`/courses/${id}`, payload),
  deleteCourse: (id) => http.delete(`/courses/${id}`),
  listClasses: (courseId) => http.get('/classes', { params: courseId ? { course_id: courseId } : {} }),
  createClass: (payload) => http.post('/classes', payload),
  updateClass: (id, payload) => http.put(`/classes/${id}`, payload),
  deleteClass: (id) => http.delete(`/classes/${id}`),
  linkClass: (payload) => http.post('/classes/link', payload),
  unlinkClass: (payload) => http.post('/classes/unlink', payload),
  listClassStudents: (classId) => http.get('/students/class-roster', { params: { class_id: classId } }),
  studentTemplateUrl: () => '/api/students/template',
  importClassStudents: (classId, file, mode = 'append') => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/students/class-roster/import', form, {
      params: { class_id: classId, mode },
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  createClassStudent: (classId, payload) => http.post('/students/class-roster', payload, { params: { class_id: classId } }),
  updateClassStudent: (id, payload) => http.put(`/students/class-roster/${id}`, payload),
  deleteClassStudent: (id) => http.delete(`/students/class-roster/${id}`),
  classStudentsExcelUrl: (classId) => `/api/students/class-roster/export?class_id=${encodeURIComponent(classId)}`,
  listCourseStudents: (courseId, classId) => http.get('/students/course-roster', { params: { course_id: courseId, class_id: classId || undefined } }),
  createCourseStudent: (courseId, classId, payload) => http.post('/students/course-roster', payload, { params: { course_id: courseId, class_id: classId } }),
  updateCourseStudent: (id, payload) => http.put(`/students/course-roster/${id}`, payload),
  deleteCourseStudent: (id) => http.delete(`/students/course-roster/${id}`),
  courseStudentsExcelUrl: (courseId, classId) => `/api/students/course-roster/export?course_id=${encodeURIComponent(courseId)}${classId ? `&class_id=${encodeURIComponent(classId)}` : ''}`,
  syncCourseRoster: (courseId, classId) => http.post('/students/course-roster/sync-from-class', null, { params: { course_id: courseId, class_id: classId } }),
  listArchiveUnits: (filters = {}) => http.get('/archives/course-class-units', { params: filters }),
  archiveCourseClassUnit: (courseId, classId) => http.post('/archives/course-class-units/archive', null, { params: { course_id: courseId, class_id: classId } }),
  restoreCourseClassUnit: (courseId, classId) => http.post('/archives/course-class-units/restore', null, { params: { course_id: courseId, class_id: classId } }),
  listExperiments: (courseId) => http.get('/experiments', { params: courseId ? { course_id: courseId } : {} }),
  createExperiment: (payload) => http.post('/experiments', payload),
  cloneExperiment: (payload) => http.post('/experiments/clone', payload),
  updateExperiment: (id, payload) => http.put(`/experiments/${id}`, payload),
  deleteExperiment: (id) => http.delete(`/experiments/${id}`),
  getExperimentDependencies: (id) => http.get(`/experiments/${id}/dependencies`),
  listRubrics: (experimentId) => http.get('/rubrics', { params: { experiment_id: experimentId } }),
  createRubric: (payload) => http.post('/rubrics', payload),
  updateRubric: (id, payload) => http.put(`/rubrics/${id}`, payload),
  deleteRubric: (id) => http.delete(`/rubrics/${id}`),
  createCommonRubricTemplate: (experimentId) => http.post('/rubrics/template', null, { params: { experiment_id: experimentId } }),
  listGradingTasks: (filters = {}) => http.get('/grading-tasks', { params: filters }),
  createGradingTask: (payload) => http.post('/grading-tasks', payload),
  updateGradingTask: (id, payload) => http.put(`/grading-tasks/${id}`, payload),
  deleteGradingTask: (id) => http.delete(`/grading-tasks/${id}`),
  getGradingTask: (id) => http.get(`/grading-tasks/${id}`),
  getTaskSummary: (id) => http.get(`/grading-tasks/${id}/summary`),
  listSubmissions: (taskId, matchStatus) => http.get('/submissions', { params: { task_id: taskId, match_status: matchStatus || undefined } }),
  getSubmission: (id) => http.get(`/submissions/${id}`),
  getParseSummary: (taskId) => http.get(`/submissions/parse-summary/${taskId}`),
  uploadReports: (taskId, files) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return http.post('/submissions/upload', form, {
      params: { task_id: taskId },
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  updateSubmissionMatch: (id, payload) => http.put(`/submissions/${id}/match`, payload),
  confirmDuplicateSubmission: (id) => http.post(`/submissions/${id}/confirm-duplicate`),
  parseSubmission: (id) => http.post(`/submissions/${id}/parse`, null, { timeout: 120000 }),
  parseTaskSubmissions: (taskId, reparse = false) => http.post('/submissions/parse-task', null, { params: { task_id: taskId, reparse }, timeout: 300000 }),
  deleteSubmission: (id) => http.delete(`/submissions/${id}`),
  batchDeleteSubmissions: (ids) => http.post('/submissions/batch-delete', ids),
  listAIProviders: () => http.get('/ai-providers'),
  getDefaultAIProvider: () => http.get('/ai-providers/default'),
  createAIProvider: (payload) => http.post('/ai-providers', payload),
  updateAIProvider: (id, payload) => http.put(`/ai-providers/${id}`, payload),
  deleteAIProvider: (id) => http.delete(`/ai-providers/${id}`),
  testAIProvider: (id) => http.post(`/ai-providers/${id}/test`, null, { timeout: 60000 }),
  testDefaultAIProvider: () => http.post('/scoring/test-default', null, { timeout: 60000 }),
  getAISummary: (taskId) => http.get(`/scoring/summary/${taskId}`),
  listAIScores: (submissionId) => http.get(`/scoring/scores/${submissionId}`),
  scoreSubmission: (submissionId, rescore = true, useVision = false, imageMode = 'first_3', imageIndices = []) => http.post(`/scoring/submissions/${submissionId}/score`, null, {
    params: {
      rescore,
      use_vision: useVision,
      image_mode: imageMode,
      image_indices: Array.isArray(imageIndices) ? imageIndices.join(',') : ''
    },
    timeout: 180000
  }),
  scoreTask: (taskId, rescoreCompleted = false, useVision = false, imageMode = 'first_3') => http.post(`/scoring/tasks/${taskId}/score`, null, {
    params: {
      rescore_completed: rescoreCompleted,
      use_vision: useVision,
      image_mode: imageMode
    },
    timeout: 600000
  }),
  resetSubmissionAI: (submissionId) => http.post(`/scoring/submissions/${submissionId}/reset`),
  getReviewSummary: (taskId) => http.get(`/reviews/summary/${taskId}`),
  listReviewSubmissions: (taskId, reviewStatus) => http.get('/reviews/submissions', { params: { task_id: taskId, review_status: reviewStatus || undefined } }),
  getReviewDetail: (submissionId) => http.get(`/reviews/submissions/${submissionId}`),
  reviewOriginalDownloadUrl: (submissionId) => `/api/reviews/submissions/${submissionId}/download-original`,
  reviewOriginalPreviewUrl: (submissionId) => `/api/reviews/submissions/${submissionId}/preview-original`,
  reviewImageUrl: (submissionId, imageIndex) => `/api/reviews/submissions/${submissionId}/images/${imageIndex}`,
  initializeReviewFromAI: (submissionId, force = false) => http.post(`/reviews/submissions/${submissionId}/initialize`, null, { params: { force } }),
  saveReviewScores: (submissionId, payload) => http.post(`/reviews/submissions/${submissionId}/save`, payload),
  resetReview: (submissionId) => http.post(`/reviews/submissions/${submissionId}/reset`),
  getExportPreview: (taskId, mode = 'reviewed_only') => http.get(`/exports/preview/${taskId}`, { params: { mode } }),
  getClassAnalysis: (taskId, mode = 'reviewed_only') => http.get(`/exports/analysis/${taskId}`, { params: { mode } }),
  gradesExcelUrl: (taskId, mode = 'reviewed_only') => `/api/exports/grades-excel/${taskId}?mode=${encodeURIComponent(mode)}`,
  analysisExcelUrl: (taskId, mode = 'reviewed_only') => `/api/exports/analysis-excel/${taskId}?mode=${encodeURIComponent(mode)}`,
  getSystemOverview: () => http.get('/system-data/overview'),
  backupDownloadUrl: (includeApiKeys = true, includeExports = false) => `/api/system-data/backup/download?include_api_keys=${includeApiKeys}&include_exports=${includeExports}`,
  validateSystemBackup: (file) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/system-data/backup/validate', form, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 })
  },
  restoreSystemBackup: (file, confirmText) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/system-data/restore', form, { params: { confirm_text: confirmText }, headers: { 'Content-Type': 'multipart/form-data' }, timeout: 300000 })
  },
  clearGradingData: (confirmText) => http.post('/system-data/clear/grading', null, { params: { confirm_text: confirmText }, timeout: 180000 }),
  clearBusinessData: (confirmText, includeAIConfigs = false) => http.post('/system-data/clear/business', null, { params: { confirm_text: confirmText, include_ai_configs: includeAIConfigs }, timeout: 180000 })
}
