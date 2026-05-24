<template>
  <div class="stack">
    <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />
    <TaskFlowNav
      :task-id="selectedTask?.id"
      :task-name="selectedTask?.task_name"
      current="upload"
    />

    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="选择批改任务" name="select">
        <GradingTaskSelectPanel
          description="先按学期、课程、教学班和实验任务缩小范围，再选择需要上传报告的批改任务。默认只显示进行中的任务。"
          :initial-task-id="route.query.task_id"
          @change="selectTask"
        />

      <div v-if="selectedTask" class="task-summary mt">
        <div class="task-line">
          当前批改任务：
          <strong>{{ selectedTask.task_name }}</strong>
        </div>
        <div class="summary-grid">
          <div class="metric-card">
            <span>课程名单人数</span>
            <strong>{{ summary.student_count }}</strong>
          </div>
          <div class="metric-card">
            <span>已上传报告</span>
            <strong>{{ summary.upload_count }}</strong>
          </div>
          <div class="metric-card">
            <span>已匹配</span>
            <strong>{{ summary.matched_count }}</strong>
          </div>
          <div class="metric-card warning">
            <span>需人工处理</span>
            <strong>{{ summary.unmatched_count }}</strong>
          </div>
          <div class="metric-card warning">
            <span>重复提交</span>
            <strong>{{ summary.duplicate_count }}</strong>
          </div>
        </div>
      </div>
      </el-tab-pane>

      <el-tab-pane label="批量上传报告" name="upload">
        <el-card v-if="selectedTask" class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>批量上传实验报告</strong>
            <div class="muted">当前版本支持 .docx、.doc 和 .pdf 文件。文件名建议包含学号和姓名，例如：202201001_张三_实验报告.docx。</div>
          </div>
        </div>
      </template>

      <el-upload v-model:file-list="fileList" drag multiple accept=".docx,.doc,.pdf" :auto-upload="false">
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将实验报告拖到此处，或点击选择文件</div>
        <template #tip>
          <div class="el-upload__tip">支持 .docx、.doc 和 .pdf；单次可以选择多份报告。上传后系统会根据文件名解析学号和姓名。</div>
        </template>
      </el-upload>

      <div class="button-row">
        <el-button type="primary" :loading="uploading" :disabled="fileList.length === 0" @click="uploadReports">上传报告</el-button>
        <el-button :disabled="fileList.length === 0 || uploading" @click="fileList = []">清空待上传列表</el-button>
      </div>

      <el-table v-if="uploadResults.length" class="mt" :data="uploadResults" border stripe>
        <el-table-column prop="original_filename" label="原始文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="parsed_student_no" label="解析学号" width="130" />
        <el-table-column prop="parsed_student_name" label="解析姓名" width="100" />
        <el-table-column prop="student_name" label="匹配学生" width="110" />
        <el-table-column prop="anonymous_id" label="匿名编号" width="100" />
        <el-table-column label="匹配状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.match_status)">{{ row.match_status || '未匹配' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error" label="错误信息" min-width="180" show-overflow-tooltip />
      </el-table>
        </el-card>
        <el-card v-else class="page-card">
          <el-empty description="请先在“选择批改任务”标签页中选择一个批改任务。" />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="提交记录与人工匹配" name="match">
        <el-card v-if="selectedTask" class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>提交记录与人工匹配</strong>
            <div class="muted">勾选多条记录可批量删除；点击任意行可在下方进行人工绑定、重复提交确认或单条删除。</div>
          </div>
          <el-button :loading="loadingSubmissions" @click="loadSubmissions">刷新提交记录</el-button>
        </div>
      </template>

      <el-row :gutter="16" class="mb">
        <el-col :span="10">
          <el-select v-model="matchStatus" style="width: 100%" @change="loadSubmissions">
            <el-option label="全部" value="全部" />
            <el-option label="已匹配" value="已匹配" />
            <el-option label="未匹配" value="未匹配" />
            <el-option label="姓名不一致" value="姓名不一致" />
            <el-option label="重复提交" value="重复提交" />
            <el-option label="重复作废" value="重复作废" />
          </el-select>
        </el-col>
      </el-row>

      <el-alert
        v-if="summary.unmatched_count > 0"
        class="mb"
        type="warning"
        :closable="false"
        :title="`当前有 ${summary.unmatched_count} 条提交记录需要人工处理：未匹配、姓名不一致或重复提交。`"
      />

      <el-table
        ref="submissionTableRef"
        :data="submissions"
        border
        stripe
        row-key="id"
        highlight-current-row
        empty-text="当前批改任务暂无提交记录"
        @selection-change="selectedSubmissionRows = $event"
        @current-change="selectSubmission"
        @row-click="selectSubmission"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="original_filename" label="原始文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="parsed_student_no" label="解析学号" width="120" />
        <el-table-column prop="parsed_student_name" label="解析姓名" width="100" />
        <el-table-column prop="student_name" label="匹配学生" width="110" />
        <el-table-column prop="anonymous_id" label="匿名编号" width="100" />
        <el-table-column label="匹配状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.match_status)">{{ row.match_status || '未匹配' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="parse_status" label="解析状态" width="100" />
        <el-table-column prop="ai_status" label="AI 状态" width="100" />
        <el-table-column prop="review_status" label="复核状态" width="100" />
      </el-table>

      <div class="button-row">
        <el-button type="danger" plain :disabled="selectedSubmissionRows.length === 0" @click="batchDelete">
          批量删除选中记录
        </el-button>
        <span class="muted">已选 {{ selectedSubmissionRows.length }} 条。删除只移除提交记录，不删除 uploads 中的原始文件；已复核报告不能删除。</span>
      </div>

      <el-divider />

      <div v-if="selectedSubmission" class="manual-box">
        <div class="selected-title">
          当前处理记录：
          <strong>{{ selectedSubmission.original_filename }}</strong>
          <el-tag class="ml" :type="statusTagType(selectedSubmission.match_status)">{{ selectedSubmission.match_status }}</el-tag>
        </div>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="解析学号">{{ selectedSubmission.parsed_student_no || '未解析到' }}</el-descriptions-item>
          <el-descriptions-item label="解析姓名">{{ selectedSubmission.parsed_student_name || '未解析到' }}</el-descriptions-item>
          <el-descriptions-item label="当前学生">{{ selectedSubmission.student_name || '未绑定' }}</el-descriptions-item>
          <el-descriptions-item label="匿名编号">{{ selectedSubmission.anonymous_id || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-form class="mt" label-position="top">
          <el-form-item label="手动绑定到课程名单中的学生">
            <SearchTablePicker
              v-model="manualStudentId"
              :items="courseStudentOptions"
              label-key="display_name"
              placeholder="选择当前课程名单中的学生"
              dialog-title="选择绑定学生"
              :columns="studentColumns"
            />
          </el-form-item>

          <div class="button-row">
            <el-button type="primary" :disabled="!manualStudentId" @click="bindStudent">绑定为该学生</el-button>
            <el-button
              v-if="selectedSubmission.match_status === '重复提交' && selectedSubmission.student_id"
              type="warning"
              plain
              @click="confirmDuplicate"
            >
              确认使用此报告
            </el-button>
            <el-button type="danger" plain @click="deleteCurrentSubmission">删除该提交记录</el-button>
          </div>

          <el-alert
            v-if="selectedSubmission.match_status === '重复作废'"
            class="mt"
            type="info"
            :closable="false"
            title="该报告已作废，不参与 AI 初评和成绩导出。"
          />
        </el-form>
      </div>
      <el-empty v-else description="请在上方表格中选择一条提交记录。" />
        </el-card>
        <el-card v-else class="page-card">
          <el-empty description="请先在“选择批改任务”标签页中选择一个批改任务。" />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import GradingTaskSelectPanel from '@/components/GradingTaskSelectPanel.vue'
import SearchTablePicker from '@/components/SearchTablePicker.vue'
import TaskFlowNav from '@/components/TaskFlowNav.vue'
import { useActionNotice } from '@/composables/useActionNotice'
import { isTaskActive } from '@/utils/taskStatus'

const submissions = ref([])
const courseStudents = ref([])
const fileList = ref([])
const uploadResults = ref([])
const selectedTask = ref(null)
const selectedSubmission = ref(null)
const selectedSubmissionRows = ref([])
const manualStudentId = ref(null)
const matchStatus = ref('全部')
const uploading = ref(false)
const loadingSubmissions = ref(false)
const route = useRoute()
const activeTab = ref(String(route.query.tab || 'select'))
const { actionNotice, showNotice, clearNotice } = useActionNotice()

watch(() => route.query.tab, (tab) => {
  if (typeof tab === 'string' && tab) {
    activeTab.value = tab
  }
})

const studentColumns = [
  { prop: 'student_no', label: '学号', width: 160 },
  { prop: 'student_name', label: '姓名', width: 130 },
  { prop: 'class_name', label: '班级', minWidth: 160 },
  { prop: 'anonymous_id', label: '匿名编号', width: 120 }
]
const courseStudentOptions = computed(() => courseStudents.value.map((student) => ({
  ...student,
  student_name: student.student_name || student.name || '',
  display_name: `${student.student_no || ''} / ${student.student_name || student.name || ''} / ${student.anonymous_id || ''}`
})))
const summary = reactive({
  student_count: 0,
  upload_count: 0,
  matched_count: 0,
  unmatched_count: 0,
  duplicate_count: 0,
  ai_done_count: 0,
  reviewed_count: 0
})

async function selectTask(row) {
  if (!row || !isActiveTask(row)) {
    selectedTask.value = null
    selectedSubmission.value = null
    manualStudentId.value = null
    submissions.value = []
    uploadResults.value = []
    resetSummary()
    return
  }
  if (selectedTask.value?.id === row.id) return
  selectedTask.value = row
  selectedSubmission.value = null
  manualStudentId.value = null
  uploadResults.value = []
  await Promise.all([loadSummary(), loadSubmissions(), loadCourseStudents()])
}

async function loadSummary() {
  if (!selectedTask.value) return
  const result = await api.getTaskSummary(selectedTask.value.id)
  Object.assign(summary, result.data || {})
}

async function loadSubmissions() {
  if (!selectedTask.value) return
  loadingSubmissions.value = true
  try {
    const result = await api.listSubmissions(selectedTask.value.id, matchStatus.value)
    submissions.value = result.data || []
    if (selectedSubmission.value && !submissions.value.some((item) => item.id === selectedSubmission.value.id)) {
      selectedSubmission.value = null
      manualStudentId.value = null
    }
    await loadSummary()
  } finally {
    loadingSubmissions.value = false
  }
}

async function loadCourseStudents() {
  if (!selectedTask.value) return
  const result = await api.listCourseStudents(selectedTask.value.course_id, selectedTask.value.class_id)
  courseStudents.value = result.data || []
}

function selectSubmission(row) {
  selectedSubmission.value = row
  manualStudentId.value = row?.student_id || null
}

async function uploadReports() {
  if (!selectedTask.value) return
  const rawFiles = fileList.value.map((item) => item.raw).filter(Boolean)
  if (rawFiles.length === 0) {
    showNotice('warning', '请先选择要上传的 .docx、.doc 或 .pdf 文件。')
    return
  }
  uploading.value = true
  try {
    const result = await api.uploadReports(selectedTask.value.id, rawFiles)
    uploadResults.value = result.data || []
    showNotice('success', result.message || '上传处理完成。')
    fileList.value = []
    await loadSubmissions()
  } finally {
    uploading.value = false
  }
}

async function bindStudent() {
  if (!selectedSubmission.value || !manualStudentId.value) return
  await api.updateSubmissionMatch(selectedSubmission.value.id, {
    student_id: manualStudentId.value,
    match_status: '已匹配'
  })
  showNotice('success', '已绑定学生。')
  await loadSubmissions()
}

async function confirmDuplicate() {
  if (!selectedSubmission.value) return
  const result = await api.confirmDuplicateSubmission(selectedSubmission.value.id)
  showNotice('success', result.message || '已确认使用该报告。')
  await loadSubmissions()
}

async function deleteCurrentSubmission() {
  if (!selectedSubmission.value) return
  await ElMessageBox.confirm('确认删除当前提交记录？原始文件仍会保留在 uploads 目录中。', '删除确认', {
    type: 'warning'
  })
  await api.deleteSubmission(selectedSubmission.value.id)
  showNotice('success', '提交记录已删除。')
  selectedSubmission.value = null
  manualStudentId.value = null
  await loadSubmissions()
}

async function batchDelete() {
  const ids = selectedSubmissionRows.value.map((item) => item.id)
  if (ids.length === 0) return
  await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条提交记录？原始文件仍会保留在 uploads 目录中。已复核报告会被系统拦截，避免误删最终成绩。`, '批量删除确认', {
    type: 'warning'
  })
  const result = await api.batchDeleteSubmissions(ids)
  showNotice('success', result.message || '提交记录已删除。')
  selectedSubmission.value = null
  selectedSubmissionRows.value = []
  await loadSubmissions()
}

function resetSummary() {
  Object.assign(summary, {
    student_count: 0,
    upload_count: 0,
    matched_count: 0,
    unmatched_count: 0,
    duplicate_count: 0,
    ai_done_count: 0,
    reviewed_count: 0
  })
}

function statusTagType(status) {
  if (status === '已匹配') return 'success'
  if (status === '姓名不一致') return 'warning'
  if (status === '重复提交') return 'danger'
  if (status === '重复作废') return 'info'
  return ''
}

</script>

<style scoped>
.stack {
  display: grid;
  gap: 20px;
}

.mb {
  margin-bottom: 16px;
}

.mt {
  margin-top: 16px;
}

.ml {
  margin-left: 8px;
}

.list-tools {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}

.list-tools .el-input {
  max-width: 460px;
}

.button-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.task-summary {
  margin-top: 16px;
  padding: 14px;
  border-radius: 10px;
  background: #eff8ff;
  border: 1px solid #c9e7fb;
}

.task-line {
  color: #0f4c81;
  margin-bottom: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 12px 14px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #d8e8f3;
}

.metric-card span {
  display: block;
  color: #64748b;
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin-top: 6px;
  font-size: 26px;
  color: #0f4c81;
}

.metric-card.warning strong {
  color: #b45309;
}

.manual-box {
  margin-top: 4px;
}

.selected-title {
  margin-bottom: 12px;
  color: #0f172a;
}

.function-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}
</style>
