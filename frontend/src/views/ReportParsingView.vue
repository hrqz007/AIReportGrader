<template>
  <div class="stack">
    <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />
    <TaskFlowNav
      :task-id="selectedTask?.id"
      :task-name="selectedTask?.task_name"
      current="parsing"
    />

    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="选择批改任务" name="select">
        <GradingTaskSelectPanel
          description="先按学期、课程、教学班和实验任务缩小范围，再选择需要解析和脱敏的批改任务。默认只显示进行中的任务。"
          :initial-task-id="route.query.task_id"
          @change="selectTask"
        />
      </el-tab-pane>

      <el-tab-pane label="批量解析" name="batch">
        <el-card v-if="selectedTask" class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>解析概览与批量操作</strong>
            <div class="muted">
              批量解析默认只处理“已匹配”和“姓名不一致”的报告；未匹配、重复提交和重复作废记录会自动跳过。
            </div>
          </div>
        </div>
      </template>

      <div class="selected-task">
        <span>当前批改任务</span>
        <strong>{{ selectedTask.task_name }}</strong>
      </div>

      <div class="summary-grid">
        <div class="parse-metric">
          <span>总提交数</span>
          <strong>{{ parseSummary.total }}</strong>
        </div>
        <div class="parse-metric">
          <span>可解析报告</span>
          <strong>{{ parseSummary.matched }}</strong>
        </div>
        <div class="parse-metric">
          <span>未解析</span>
          <strong>{{ parseSummary.not_parsed }}</strong>
        </div>
        <div class="parse-metric success">
          <span>解析完成</span>
          <strong>{{ parseSummary.parsed }}</strong>
        </div>
        <div class="parse-metric danger">
          <span>解析失败</span>
          <strong>{{ parseSummary.failed }}</strong>
        </div>
        <div class="parse-metric">
          <span>提取图片</span>
          <strong>{{ parseSummary.image_total }}</strong>
        </div>
      </div>

      <div class="button-row">
        <el-button type="primary" :loading="parsing" :disabled="parseSummary.matched === 0" @click="parseTask(false)">
          批量解析可处理报告
        </el-button>
        <el-button :loading="parsing" :disabled="parseSummary.matched === 0" @click="parseTask(true)">
          重新解析已匹配报告
        </el-button>
      </div>

      <el-alert
        class="mt"
        type="warning"
        :closable="false"
        title="图片当前只提取并保存路径，尚未做图片内容自动脱敏；后续发送给 AI 前仍需教师确认截图中是否包含账号、路径、头像等敏感信息。"
      />
        </el-card>
        <el-card v-else class="page-card">
          <el-empty description="请先在“选择批改任务”标签页中选择一个批改任务。" />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="解析结果" name="result">
        <el-card v-if="selectedTask" class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>提交记录解析状态</strong>
            <div class="muted">点击任意行查看原始文本摘要、脱敏文本摘要和图片路径列表。</div>
          </div>
          <el-button :loading="loadingSubmissions" @click="refreshTaskData">刷新列表</el-button>
        </div>
      </template>

      <el-row :gutter="16" class="mb">
        <el-col :span="8">
          <el-select v-model="parseStatusFilter" style="width: 100%">
            <el-option label="全部解析状态" value="全部" />
            <el-option label="未解析" value="未解析" />
            <el-option label="解析完成" value="解析完成" />
            <el-option label="解析失败" value="解析失败" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-select v-model="matchStatusFilter" style="width: 100%">
            <el-option label="全部匹配状态" value="全部" />
            <el-option label="已匹配" value="已匹配" />
            <el-option label="姓名不一致" value="姓名不一致" />
            <el-option label="未匹配" value="未匹配" />
            <el-option label="重复提交" value="重复提交" />
            <el-option label="重复作废" value="重复作废" />
          </el-select>
        </el-col>
      </el-row>

      <el-table
        :data="filteredRows"
        border
        stripe
        highlight-current-row
        empty-text="暂无提交记录"
        @current-change="selectSubmission"
        @row-click="selectSubmission"
      >
        <el-table-column prop="student_no" label="学号" width="125" show-overflow-tooltip />
        <el-table-column prop="student_name" label="姓名" width="100" show-overflow-tooltip />
        <el-table-column prop="original_filename" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column label="匹配状态" width="120">
          <template #default="{ row }">
            <el-tag :type="matchTagType(row.match_status)">{{ row.match_status || '未匹配' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="解析状态" width="120">
          <template #default="{ row }">
            <el-tag :type="parseTagType(row.parse_status)">{{ row.parse_status || '未解析' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="text_length" label="正文长度" width="100" />
        <el-table-column prop="image_count" label="图片数量" width="100" />
        <el-table-column prop="sensitive_summary" label="敏感信息摘要" min-width="220" show-overflow-tooltip />
        <el-table-column prop="parse_error" label="解析错误" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :loading="singleParsingId === row.id"
              :disabled="row.match_status === '重复作废'"
              @click.stop="parseOne(row)"
            >
              {{ row.parse_status === '解析完成' ? '重新解析' : '解析' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
        </el-card>

        <el-card v-if="selectedDetail" class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>单份报告解析结果</strong>
            <div class="muted">{{ selectedDetail.original_filename }}</div>
          </div>
          <el-button :loading="singleParsingId === selectedDetail.id" @click="parseOne(selectedDetail)">
            重新解析该报告
          </el-button>
        </div>
      </template>

      <el-descriptions :column="3" border>
        <el-descriptions-item label="解析状态">
          <el-tag :type="parseTagType(selectedDetail.parse_status)">{{ selectedDetail.parse_status || '未解析' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="正文长度">{{ selectedDetail.text_length || 0 }}</el-descriptions-item>
        <el-descriptions-item label="图片数量">{{ selectedDetail.image_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="敏感信息" :span="3">
          {{ selectedDetail.detected_flags_data?.summary || '暂无检测结果' }}
        </el-descriptions-item>
        <el-descriptions-item v-if="selectedDetail.parse_error" label="解析错误" :span="3">
          <span class="danger-text">{{ selectedDetail.parse_error }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <el-alert
        v-if="selectedDetail.detected_flags_data?.summary"
        class="mt"
        type="info"
        :closable="false"
        :title="selectedDetail.detected_flags_data.summary"
      />

      <el-collapse class="mt">
        <el-collapse-item title="查看原始文本摘要">
          <pre class="text-preview">{{ previewText(selectedDetail.plain_text) }}</pre>
        </el-collapse-item>
        <el-collapse-item title="查看脱敏文本摘要">
          <pre class="text-preview">{{ previewText(selectedDetail.anonymized_text) }}</pre>
        </el-collapse-item>
        <el-collapse-item title="查看提取图片路径">
          <el-empty v-if="imagePaths.length === 0" description="未提取到图片" />
          <ul v-else class="path-list">
            <li v-for="path in imagePaths" :key="path">{{ path }}</li>
          </ul>
        </el-collapse-item>
      </el-collapse>
        </el-card>
        <el-card v-else-if="!selectedTask" class="page-card">
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
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import GradingTaskSelectPanel from '@/components/GradingTaskSelectPanel.vue'
import TaskFlowNav from '@/components/TaskFlowNav.vue'
import { useActionNotice } from '@/composables/useActionNotice'
import { isTaskActive } from '@/utils/taskStatus'

const submissions = ref([])
const selectedTask = ref(null)
const selectedDetail = ref(null)
const parsing = ref(false)
const singleParsingId = ref(null)
const loadingSubmissions = ref(false)
const parseStatusFilter = ref('全部')
const matchStatusFilter = ref('全部')
const route = useRoute()
const activeTab = ref(String(route.query.tab || 'select'))
const { actionNotice, showNotice, clearNotice } = useActionNotice()

watch(() => route.query.tab, (tab) => {
  if (typeof tab === 'string' && tab) {
    activeTab.value = tab
  }
})

const parseSummary = reactive({
  total: 0,
  matched: 0,
  not_parsed: 0,
  parsed: 0,
  failed: 0,
  image_total: 0
})

const rowsWithStats = computed(() =>
  submissions.value.map((row) => {
    let flags = {}
    let imagePaths = []
    try {
      flags = JSON.parse(row.detected_flags || '{}')
    } catch {
      flags = {}
    }
    try {
      imagePaths = JSON.parse(row.image_paths || '[]')
    } catch {
      imagePaths = []
    }
    return {
      ...row,
      parse_status: row.parse_status || '未解析',
      text_length: (row.plain_text || '').length,
      image_count: imagePaths.length,
      sensitive_summary: flags.summary || '暂无检测结果'
    }
  })
)

const filteredRows = computed(() =>
  rowsWithStats.value.filter((row) => {
    const parseOk = parseStatusFilter.value === '全部' || row.parse_status === parseStatusFilter.value
    const matchOk = matchStatusFilter.value === '全部' || row.match_status === matchStatusFilter.value
    return parseOk && matchOk
  })
)

const imagePaths = computed(() => {
  try {
    return JSON.parse(selectedDetail.value?.image_paths || '[]')
  } catch {
    return []
  }
})

async function selectTask(row) {
  if (!row || !isActiveTask(row)) {
    selectedTask.value = null
    selectedDetail.value = null
    submissions.value = []
    resetParseSummary()
    return
  }
  if (selectedTask.value?.id === row.id) return
  selectedTask.value = row
  selectedDetail.value = null
  await refreshTaskData()
}

async function refreshTaskData() {
  await Promise.all([loadSubmissions(), loadParseSummary()])
}

async function loadSubmissions() {
  if (!selectedTask.value) return
  loadingSubmissions.value = true
  try {
    const result = await api.listSubmissions(selectedTask.value.id)
    submissions.value = result.data || []
    if (selectedDetail.value && !submissions.value.some((item) => item.id === selectedDetail.value.id)) {
      selectedDetail.value = null
    }
  } finally {
    loadingSubmissions.value = false
  }
}

async function loadParseSummary() {
  if (!selectedTask.value) return
  const result = await api.getParseSummary(selectedTask.value.id)
  Object.assign(parseSummary, result.data || {})
}

async function parseTask(reparse) {
  if (!selectedTask.value) return
  if (reparse) {
    await ElMessageBox.confirm('确认重新解析所有可处理报告？已有解析结果会被覆盖。', '重新解析确认', {
      type: 'warning'
    })
  }
  parsing.value = true
  try {
    const result = await api.parseTaskSubmissions(selectedTask.value.id, reparse)
    const data = result.data || {}
    showNotice('success', `解析完成：成功 ${data.success || 0} 份，失败 ${data.failed || 0} 份，跳过 ${data.skipped || 0} 份。`)
    await refreshTaskData()
  } finally {
    parsing.value = false
  }
}

async function parseOne(row) {
  if (!row || row.match_status === '重复作废') return
  singleParsingId.value = row.id
  try {
    const result = await api.parseSubmission(row.id)
    if (result.ok) {
      showNotice('success', '解析完成。')
    } else {
      showNotice('warning', result.data?.parse_error || '解析失败。')
    }
    await refreshTaskData()
    await selectSubmission(row)
  } finally {
    singleParsingId.value = null
  }
}

async function selectSubmission(row) {
  if (!row) {
    selectedDetail.value = null
    return
  }
  const result = await api.getSubmission(row.id)
  selectedDetail.value = result.data
}

function previewText(text) {
  if (!text) return '暂无内容。'
  return text.length > 3000 ? `${text.slice(0, 3000)}\n\n……（仅显示前 3000 字）` : text
}

function parseTagType(status) {
  if (status === '解析完成') return 'success'
  if (status === '解析失败') return 'danger'
  return 'info'
}

function matchTagType(status) {
  if (status === '已匹配') return 'success'
  if (status === '姓名不一致') return 'warning'
  if (status === '重复提交') return 'danger'
  if (status === '重复作废') return 'info'
  return ''
}

function resetParseSummary() {
  Object.assign(parseSummary, {
    total: 0,
    matched: 0,
    not_parsed: 0,
    parsed: 0,
    failed: 0,
    image_total: 0
  })
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

.list-tools {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}

.list-tools .el-input {
  max-width: 460px;
}

.selected-task {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  margin-bottom: 14px;
  border-radius: 12px;
  background: #eff8ff;
  border: 1px solid #c9e7fb;
  color: #0f4c81;
}

.selected-task span {
  color: #5f7890;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.parse-metric {
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(180deg, #fff 0%, #f3fbff 100%);
  border: 1px solid #d8e8f3;
}

.parse-metric span {
  display: block;
  color: #64748b;
  font-size: 13px;
}

.parse-metric strong {
  display: block;
  margin-top: 6px;
  font-size: 26px;
  color: #0f4c81;
}

.parse-metric.success strong {
  color: #15803d;
}

.parse-metric.danger strong {
  color: #b91c1c;
}

.button-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.text-preview {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  max-height: 420px;
  overflow: auto;
}

.path-list {
  line-height: 1.8;
  word-break: break-all;
}

.danger-text {
  color: #b91c1c;
}

.function-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
