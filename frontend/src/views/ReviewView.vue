<template>
  <div class="stack">
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      title="AI 建议分不作为最终成绩。教师确认分才用于成绩导出，教师应结合原报告、截图和评分标准进行复核。"
    />
    <TaskFlowNav
      :task-id="selectedTask?.id"
      :task-name="selectedTask?.task_name"
      current="review"
    />

    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="选择批改任务" name="select">
        <GradingTaskSelectPanel
          description="先按学期、课程、教学班和实验任务筛选，再选择需要教师复核的批改任务。默认只显示进行中的任务。"
          :initial-task-id="route.query.task_id"
          @change="selectTask"
        />
      </el-tab-pane>

      <el-tab-pane label="复核进度" name="progress">
    <el-empty v-if="!selectedTask" description="请先选择批改任务后查看复核进度。" />
    <el-card v-else class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>复核进度</strong>
            <div class="muted">确认最终成绩后，系统会自动刷新列表并进入下一份未复核报告。</div>
          </div>
        </div>
      </template>

      <div class="summary-grid">
        <div class="review-metric">
          <span>可复核报告</span>
          <strong>{{ reviewSummary.total }}</strong>
        </div>
        <div class="review-metric success">
          <span>AI 初评完成</span>
          <strong>{{ reviewSummary.ai_done }}</strong>
        </div>
        <div class="review-metric warning">
          <span>待复核</span>
          <strong>{{ reviewSummary.pending }}</strong>
        </div>
        <div class="review-metric success">
          <span>已复核</span>
          <strong>{{ reviewSummary.reviewed }}</strong>
        </div>
        <div class="review-metric">
          <span>教师平均分</span>
          <strong>{{ reviewSummary.average ?? '-' }}</strong>
        </div>
      </div>
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="提交列表" name="submissions">
    <el-empty v-if="!selectedTask" description="请先选择批改任务后查看提交列表。" />
    <el-card v-else class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>提交列表</strong>
            <div class="muted">默认显示未复核报告。点击任意行即可切换当前复核对象。</div>
          </div>
          <div class="filter-row">
            <el-select v-model="reviewStatusFilter" style="width: 160px" @change="loadAndSelectFirst">
              <el-option label="未复核" value="未复核" />
              <el-option label="已复核" value="已复核" />
              <el-option label="全部" value="全部" />
            </el-select>
            <el-button :loading="loadingReviewRows" @click="loadAndSelectFirst">刷新列表</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="reviewRows"
        border
        stripe
        highlight-current-row
        empty-text="当前筛选条件下暂无报告"
        @current-change="selectSubmission"
        @row-click="selectSubmission"
      >
        <el-table-column prop="student_no" label="学号" width="125" show-overflow-tooltip />
        <el-table-column prop="student_name" label="姓名" width="100" show-overflow-tooltip />
        <el-table-column prop="anonymous_id" label="匿名编号" width="105" />
        <el-table-column prop="original_filename" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column label="AI 状态" width="120">
          <template #default="{ row }">
            <el-tag :type="aiTagType(row.ai_status)">{{ row.ai_status || '未初评' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AI 建议总分" width="120">
          <template #default="{ row }">{{ formatScore(row.ai_total_score) }}</template>
        </el-table-column>
        <el-table-column label="教师确认总分" width="130">
          <template #default="{ row }">{{ formatScore(row.final_teacher_total_score) }}</template>
        </el-table-column>
        <el-table-column label="复核状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.review_status === '已复核' ? 'success' : 'warning'">{{ row.review_status || '未复核' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="评分复核" name="review">
    <el-empty v-if="!detail" description="请先在提交列表中选择一份报告。" />
    <el-card v-else class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>当前报告：{{ detail.submission.student_no || '-' }} | {{ detail.submission.student_name || '-' }}</strong>
            <div class="muted">{{ detail.submission.original_filename }}</div>
          </div>
        </div>
      </template>

      <div class="material-panel">
        <div class="section-head">
          <div>
            <div class="panel-title">原始报告预览</div>
            <div class="muted">先核对学生提交材料，再在下方逐项确认教师分。</div>
          </div>
          <el-button class="review-outline-button" @click="downloadOriginalReport">下载原始 Word 报告</el-button>
        </div>
        <el-alert
          class="mb"
          type="warning"
          :closable="false"
          show-icon
          title="系统优先使用本机 Office/LibreOffice 转 PDF 进行高保真预览；若未检测到转换能力，会自动降级为 HTML 预览，降级预览可能与 Word 原版式不完全一致。"
        />
        <el-tabs class="material-tabs">
          <el-tab-pane label="Word 预览">
            <iframe class="word-preview-frame" :src="api.reviewOriginalPreviewUrl(detail.submission.id)" />
          </el-tab-pane>
          <el-tab-pane label="原始解析文本">
            <pre class="text-preview">{{ previewText(detail.submission.plain_text) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="报告截图">
            <el-empty v-if="detail.image_paths.length === 0" description="未提取到图片" />
            <div v-else class="review-image-grid">
              <div v-for="(path, index) in detail.image_paths" :key="path" class="review-image-card">
                <el-image :src="reviewImageUrls[index]" fit="contain" :preview-src-list="reviewImageUrls" />
                <div class="image-caption">截图 {{ index + 1 }}</div>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="脱敏文本">
            <pre class="text-preview">{{ previewText(detail.submission.anonymized_text) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="敏感检测">
            <pre class="text-preview">{{ JSON.stringify(detail.detected_flags || {}, null, 2) }}</pre>
          </el-tab-pane>
        </el-tabs>
      </div>

      <div class="score-panel">
        <div class="section-head">
          <div>
            <div class="panel-title">分项评分复核</div>
            <div class="muted">教师确认分可在总览表快速修改，也可在评分项详情中逐项核对。备注为可选项。</div>
          </div>
          <div class="button-row no-margin">
            <el-button class="review-outline-button" :loading="initializing" @click="initFromAI(false)">用 AI 建议分初始化</el-button>
            <el-button class="review-outline-button" :loading="initializing" @click="initFromAI(true)">重置为 AI 建议分</el-button>
          </div>
        </div>

        <el-alert
          v-if="invalidScoreRows.length"
          class="mb"
          type="error"
          :closable="false"
          show-icon
          :title="`教师确认分不能超过该项满分：${invalidScoreRows.join('；')}`"
        />

        <div class="quick-review-block">
          <div class="quick-review-title">
            <span>评分总览与快速改分</span>
            <strong>当前报告：{{ detail.submission.student_no || '未匹配学号' }} | {{ detail.submission.student_name || '未匹配姓名' }}</strong>
          </div>
          <el-table :data="scoreRows" border stripe empty-text="暂无 AI 分项建议分，请先完成 AI 初评。">
            <el-table-column type="index" label="序号" width="70" />
            <el-table-column prop="item_name" label="评分项" min-width="210" show-overflow-tooltip />
            <el-table-column label="满分" width="90">
              <template #default="{ row }">{{ formatPlainScore(row.max_score) }}</template>
            </el-table-column>
            <el-table-column label="AI 建议分" width="115">
              <template #default="{ row }">{{ formatPlainScore(row.ai_score) }}</template>
            </el-table-column>
            <el-table-column label="教师确认分" width="170">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.teacher_score"
                  :min="0"
                  :step="0.5"
                  controls-position="right"
                  style="width: 138px"
                />
              </template>
            </el-table-column>
            <el-table-column label="教师备注（可选）" min-width="220">
              <template #default="{ row }">
                <el-input v-model="row.teacher_comment" placeholder="可选：说明改分原因" />
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="90" />
            <el-table-column label="重点复核" width="100">
              <template #default="{ row }">{{ row.need_teacher_review || row.confidence === '低' ? '是' : '否' }}</template>
            </el-table-column>
          </el-table>
          <div class="score-total-row">
            <span>总分</span>
            <span>满分：{{ totalMaxScore.toFixed(2) }}</span>
            <span>AI 建议总分：{{ aiTotal.toFixed(2) }}</span>
            <strong>教师确认总分：{{ teacherTotal.toFixed(2) }}</strong>
            <span>人与 AI 评分差值：{{ (teacherTotal - aiTotal).toFixed(2) }}</span>
          </div>
        </div>

        <div v-if="activeScoreRow" class="score-detail-block">
          <div class="detail-title-row">
            <div>
              <div class="panel-title">评分项详情</div>
              <div class="muted">逐项查看 AI 扣分依据，结合报告原文、截图和评分标准确认。</div>
            </div>
            <div class="current-report-chip">当前报告：{{ detail.submission.student_no || '未匹配学号' }} | {{ detail.submission.student_name || '未匹配姓名' }}</div>
          </div>

          <el-tabs v-model="activeScoreTab" class="score-item-tabs">
            <el-tab-pane
              v-for="(row, index) in scoreRows"
              :key="row.rubric_item_id || index"
              :name="String(index)"
              :label="`${index + 1}. ${shortLabel(row.item_name)}${row.need_teacher_review || row.confidence === '低' ? '*' : ''}`"
            />
          </el-tabs>

          <div class="score-detail-card">
            <div class="score-detail-header">
              <div>
                <strong>{{ Number(activeScoreTab) + 1 }}. {{ activeScoreRow.item_name }}</strong>
                <div class="muted">满分 {{ formatPlainScore(activeScoreRow.max_score) }} 分；AI 建议 {{ formatPlainScore(activeScoreRow.ai_score) }} 分</div>
              </div>
              <div class="tag-row">
                <el-tag :type="activeScoreRow.need_teacher_review || activeScoreRow.confidence === '低' ? 'warning' : 'info'">
                  {{ activeScoreRow.need_teacher_review || activeScoreRow.confidence === '低' ? '需重点复核' : '常规复核' }}
                </el-tag>
                <el-tag type="primary">置信度：{{ activeScoreRow.confidence || '未提供' }}</el-tag>
              </div>
            </div>

            <el-row :gutter="18" class="score-detail-main">
              <el-col :span="8">
                <div class="ai-reason-card">
                  <div class="small-title">AI 建议与扣分原因</div>
                  <p>{{ activeScoreRow.deduction_reason || 'AI 未提供扣分原因。' }}</p>
                </div>
                <div class="total-card in-detail">
                  <span>教师确认总分</span>
                  <strong>{{ teacherTotal.toFixed(2) }} 分</strong>
                  <small>AI 建议总分 {{ aiTotal.toFixed(2) }} 分；人与 AI 评分差值 {{ (teacherTotal - aiTotal).toFixed(2) }} 分。</small>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="max-score-line">本项满分：{{ formatPlainScore(activeScoreRow.max_score) }} 分</div>
                <el-form label-position="top">
                  <el-form-item label="教师确认分">
                    <el-input-number
                      v-model="activeScoreRow.teacher_score"
                      :min="0"
                      :step="0.5"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </el-form-item>
                  <el-form-item label="教师备注 / 修改原因（可选）">
                    <el-input v-model="activeScoreRow.teacher_comment" type="textarea" :rows="4" placeholder="可选：说明改分原因" />
                  </el-form-item>
                  <el-button class="review-primary-button" type="primary" style="width: 100%" @click="confirmCurrentItem">确认本项</el-button>
                </el-form>
              </el-col>
              <el-col :span="8">
                <el-alert
                  :type="activeScoreRow.need_teacher_review || activeScoreRow.confidence === '低' ? 'warning' : 'info'"
                  :closable="false"
                  :title="activeScoreRow.need_teacher_review || activeScoreRow.confidence === '低'
                    ? '该项建议重点复核。请结合上方原始报告预览、报告截图和评分标准确认。'
                    : '如 AI 建议分合理，可直接保留教师确认分。'"
                />
                <el-alert
                  v-if="Number(activeScoreRow.teacher_score || 0) !== Number(activeScoreRow.ai_score || 0)"
                  class="mt"
                  type="info"
                  :closable="false"
                  title="当前教师确认分与 AI 建议分不同，建议填写修改原因。"
                />
                <el-button class="next-item-btn review-outline-button" :disabled="Number(activeScoreTab) >= scoreRows.length - 1" @click="nextScoreItem">下一项</el-button>
              </el-col>
            </el-row>
          </div>
        </div>

        <el-input
          v-model="overallComment"
          class="mt"
          type="textarea"
          :rows="4"
          placeholder="教师总评 / 复核备注（可选）"
        />

        <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

        <div class="button-row">
          <el-button type="primary" :loading="savingFinal" :disabled="scoreRows.length === 0 || invalidScoreRows.length > 0" @click="confirmFinal">
            确认最终成绩并进入下一份
          </el-button>
          <el-button class="review-outline-button" :loading="savingDraft" :disabled="scoreRows.length === 0 || invalidScoreRows.length > 0" @click="saveDraft">暂存复核分</el-button>
          <el-button class="review-outline-button" :loading="resetting" @click="resetCurrentReview">重置复核状态</el-button>
        </div>
      </div>
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

const reviewRows = ref([])
const selectedTask = ref(null)
const detail = ref(null)
const scoreRows = ref([])
const overallComment = ref('')
const reviewStatusFilter = ref('未复核')
const loadingReviewRows = ref(false)
const initializing = ref(false)
const savingDraft = ref(false)
const savingFinal = ref(false)
const resetting = ref(false)
const activeScoreTab = ref('0')
const route = useRoute()
const activeTab = ref(String(route.query.tab || 'select'))
const { actionNotice, showNotice, clearNotice } = useActionNotice()

watch(() => route.query.tab, (tab) => {
  if (typeof tab === 'string' && tab) {
    activeTab.value = tab
  }
})

const reviewSummary = reactive({
  total: 0,
  ai_done: 0,
  ai_failed: 0,
  pending: 0,
  reviewed: 0,
  average: null
})

const teacherTotal = computed(() => scoreRows.value.reduce((sum, row) => sum + Number(row.teacher_score || 0), 0))
const aiTotal = computed(() => scoreRows.value.reduce((sum, row) => sum + Number(row.ai_score || 0), 0))
const totalMaxScore = computed(() => scoreRows.value.reduce((sum, row) => sum + Number(row.max_score || 0), 0))
const activeScoreRow = computed(() => {
  const index = Number(activeScoreTab.value || 0)
  return scoreRows.value[index] || null
})
const invalidScoreRows = computed(() => scoreRows.value
  .filter((row) => Number(row.teacher_score || 0) < 0 || Number(row.teacher_score || 0) > Number(row.max_score || 0))
  .map((row) => `${row.item_name}：填写 ${formatPlainScore(row.teacher_score)}，满分 ${formatPlainScore(row.max_score)}`))
const reviewImageUrls = computed(() => (detail.value?.image_paths || []).map((_, index) => api.reviewImageUrl(detail.value.submission.id, index + 1)))
async function selectTask(row) {
  if (!row || !isActiveTask(row)) {
    selectedTask.value = null
    detail.value = null
    scoreRows.value = []
    reviewRows.value = []
    resetSummary()
    return
  }
  if (selectedTask.value?.id === row.id) return
  selectedTask.value = row
  detail.value = null
  scoreRows.value = []
  await Promise.all([loadReviewSummary(), loadReviewSubmissions()])
  await autoSelectFirstRow()
}

async function loadAndSelectFirst() {
  await Promise.all([loadReviewSummary(), loadReviewSubmissions()])
  await autoSelectFirstRow()
}

async function loadReviewSubmissions() {
  if (!selectedTask.value) return
  loadingReviewRows.value = true
  try {
    const result = await api.listReviewSubmissions(selectedTask.value.id, reviewStatusFilter.value)
    reviewRows.value = result.data || []
  } finally {
    loadingReviewRows.value = false
  }
}

async function loadReviewSummary() {
  if (!selectedTask.value) return
  const result = await api.getReviewSummary(selectedTask.value.id)
  Object.assign(reviewSummary, result.data || {})
}

async function selectSubmission(row) {
  if (!row) return
  const result = await api.getReviewDetail(row.id)
  detail.value = result.data
  buildScoreRows()
  clearNotice()
}

function buildScoreRows() {
  const teacherItems = detail.value.teacher_items || []
  const byRubric = new Map(teacherItems.map((item) => [Number(item.rubric_item_id), item]))
  scoreRows.value = (detail.value.ai_scores || []).map((ai) => {
    const saved = byRubric.get(Number(ai.rubric_item_id))
    const aiScore = Number(ai.ai_score || 0)
    return {
      rubric_item_id: ai.rubric_item_id,
      item_name: ai.item_name,
      max_score: Number(ai.max_score || 0),
      ai_score: aiScore,
      teacher_score: saved ? Number(saved.teacher_score || 0) : aiScore,
      teacher_comment: saved?.teacher_comment || '',
      deduction_reason: ai.deduction_reason || '',
      confidence: ai.confidence || '',
      need_teacher_review: Boolean(ai.need_teacher_review)
    }
  })
  activeScoreTab.value = scoreRows.value.length ? '0' : '0'
  overallComment.value = detail.value.teacher_score?.feedback || detail.value.submission.teacher_overall_comment || ''
}

function shortLabel(text) {
  const value = String(text || '评分项')
  return value.length > 10 ? `${value.slice(0, 10)}…` : value
}

function formatPlainScore(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0'
  return Number.isInteger(num) ? String(num) : num.toFixed(2)
}

function nextScoreItem() {
  const index = Number(activeScoreTab.value || 0)
  if (index < scoreRows.value.length - 1) {
    activeScoreTab.value = String(index + 1)
  }
}

function confirmCurrentItem() {
  if (!activeScoreRow.value) return
  const currentScore = Number(activeScoreRow.value.teacher_score || 0)
  const maxScore = Number(activeScoreRow.value.max_score || 0)
  if (currentScore > maxScore) {
    showNotice('error', `本项教师确认分不能超过满分 ${formatPlainScore(maxScore)} 分。`)
    return
  }
  if (Number(activeScoreTab.value || 0) < scoreRows.value.length - 1) {
    nextScoreItem()
  }
  showNotice('success', '本项已确认，可继续复核下一项。')
}

async function initFromAI(force) {
  if (!detail.value) return
  if (force) {
    await ElMessageBox.confirm('确认将当前教师复核分重置为 AI 建议分？', '重置确认', { type: 'warning' })
  }
  initializing.value = true
  try {
    const result = await api.initializeReviewFromAI(detail.value.submission.id, force)
    await selectSubmission(detail.value.submission)
    showNotice(result.ok ? 'success' : 'warning', result.message || (result.ok ? '已初始化教师确认分。' : '初始化失败。'))
  } finally {
    initializing.value = false
  }
}

async function saveDraft() {
  savingDraft.value = true
  try {
    await saveReview(false)
  } finally {
    savingDraft.value = false
  }
}

async function confirmFinal() {
  savingFinal.value = true
  try {
    const result = await saveReview(true)
    if (result?.ok) {
      reviewStatusFilter.value = '未复核'
      await Promise.all([loadReviewSummary(), loadReviewSubmissions()])
      if (reviewRows.value.length > 0) {
        await autoSelectFirstRow()
        activeTab.value = 'review'
      } else {
        detail.value = null
        scoreRows.value = []
        overallComment.value = ''
        activeTab.value = 'submissions'
        showNotice('success', '当前批改任务下未复核报告已处理完。')
      }
    }
  } finally {
    savingFinal.value = false
  }
}

async function saveReview(markCompleted) {
  if (!detail.value) return null
  const result = await api.saveReviewScores(detail.value.submission.id, {
    score_rows: scoreRows.value,
    overall_comment: overallComment.value,
    reviewer_name: '',
    mark_completed: markCompleted
  })
  if (result.ok) {
    showNotice(
      'success',
      markCompleted ? `最终成绩已确认：${formatScore(result.total_score)} 分。` : `复核分已暂存：${formatScore(result.total_score)} 分。`
    )
  } else {
    showNotice('error', result.message || '保存失败。')
  }
  return result
}

async function resetCurrentReview() {
  if (!detail.value) return
  await ElMessageBox.confirm('确认重置该报告的教师复核状态？已保存的教师确认分会被清除。', '重置确认', { type: 'warning' })
  resetting.value = true
  try {
    const current = detail.value.submission
    const result = await api.resetReview(current.id)
    await Promise.all([loadReviewSummary(), loadReviewSubmissions()])
    await selectSubmission(current)
    showNotice(result.ok ? 'success' : 'warning', result.message || '复核状态已重置。')
  } finally {
    resetting.value = false
  }
}

async function autoSelectFirstRow() {
  if (!reviewRows.value.length) {
    detail.value = null
    scoreRows.value = []
    overallComment.value = ''
    return
  }
  await selectSubmission(reviewRows.value[0])
}

function previewText(text) {
  if (!text) return '暂无内容。'
  return text.length > 2500 ? `${text.slice(0, 2500)}\n\n……（仅显示前 2500 字）` : text
}

function downloadOriginalReport() {
  if (!detail.value?.submission?.id) return
  window.open(api.reviewOriginalDownloadUrl(detail.value.submission.id), '_blank')
}

function formatScore(value) {
  if (value === null || value === undefined || value === '') return '暂无'
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : '暂无'
}

function aiTagType(status) {
  if (status === '初评完成') return 'success'
  if (status === '初评失败') return 'danger'
  if (status === '初评中') return 'warning'
  return 'info'
}

function resetSummary() {
  Object.assign(reviewSummary, {
    total: 0,
    ai_done: 0,
    ai_failed: 0,
    pending: 0,
    reviewed: 0,
    average: null
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

.function-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}

.filter-row,
.button-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.button-row {
  margin-top: 16px;
}

.button-row.no-margin {
  margin-top: 0;
}

.review-primary-button {
  background: #0369a1 !important;
  border-color: #0369a1 !important;
  color: #ffffff !important;
  font-weight: 850;
}

.review-primary-button:hover,
.review-primary-button:focus {
  background: #075985 !important;
  border-color: #075985 !important;
  color: #ffffff !important;
}

.review-outline-button {
  background: #ffffff !important;
  border-color: #7fc5df !important;
  color: #075985 !important;
  font-weight: 800;
}

.review-outline-button:hover,
.review-outline-button:focus {
  background: #e0f2fe !important;
  border-color: #0284c7 !important;
  color: #0c4a6e !important;
}

.review-outline-button.is-disabled,
.review-outline-button.is-disabled:hover,
.review-outline-button.is-disabled:focus {
  background: #f1f5f9 !important;
  border-color: #cbd5e1 !important;
  color: #64748b !important;
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.review-metric {
  padding: 14px 16px;
  border: 1px solid #d8e8f3;
  border-radius: 12px;
  background: linear-gradient(180deg, #fff 0%, #f3fbff 100%);
}

.review-metric span {
  display: block;
  color: #64748b;
  font-size: 13px;
}

.review-metric strong {
  display: block;
  margin-top: 8px;
  color: #0f4c81;
  font-size: 28px;
  line-height: 1.1;
}

.review-metric.success strong {
  color: #15803d;
}

.review-metric.warning strong {
  color: #b45309;
}

.material-panel,
.score-panel {
  border: 1px solid #d8e8f3;
  border-radius: 14px;
  background: #fbfdff;
  padding: 16px;
}

.material-panel + .score-panel {
  margin-top: 18px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.panel-title {
  color: #08344f;
  font-size: 18px;
  font-weight: 850;
  margin-bottom: 10px;
}

.material-actions {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 12px;
}

.material-tabs :deep(.el-tabs__content) {
  padding-top: 8px;
}

.review-image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.review-image-card {
  border: 1px solid #d8e8f3;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.review-image-card .el-image {
  width: 100%;
  height: 150px;
  border-radius: 8px;
  background: #f8fafc;
}

.word-preview-frame {
  width: 100%;
  height: 820px;
  border: 1px solid #d8e8f3;
  border-radius: 12px;
  background: #e5e7eb;
}

.image-caption {
  margin-top: 8px;
  color: #0f4c81;
  font-weight: 800;
  text-align: center;
}

.score-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.quick-review-block {
  margin-top: 14px;
}

.quick-review-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  padding-top: 12px;
  margin-bottom: 12px;
  border-top: 1px solid #d8e8f3;
}

.quick-review-title span,
.detail-title-row .panel-title {
  color: #08344f;
  font-size: 20px;
  font-weight: 900;
}

.quick-review-title strong,
.current-report-chip {
  color: #00796b;
  font-size: 18px;
  font-weight: 900;
}

.score-total-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1.2fr 1.35fr 1.6fr;
  gap: 12px;
  align-items: center;
  padding: 13px 16px;
  border: 1px solid #d8e8f3;
  border-top: 0;
  border-radius: 0 0 12px 12px;
  background: #f8fbff;
  color: #0f4c81;
  font-weight: 800;
}

.score-total-row strong {
  color: #8b1a1a;
  font-size: 18px;
}

.score-detail-block {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 2px solid #d8e8f3;
}

.detail-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.score-item-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.score-detail-card {
  border: 1px solid #d8e8f3;
  border-radius: 14px;
  background: #fff;
  padding: 16px;
}

.score-detail-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding-bottom: 12px;
  margin-bottom: 16px;
  border-bottom: 1px solid #e2edf4;
}

.score-detail-header strong {
  display: block;
  color: #082f49;
  font-size: 18px;
  margin-bottom: 6px;
}

.tag-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.score-detail-main {
  align-items: stretch;
}

.ai-reason-card {
  min-height: 150px;
  border: 1px solid #fecaca;
  border-radius: 12px;
  background: #fff1f2;
  padding: 14px;
}

.small-title {
  color: #64748b;
  font-size: 13px;
  font-weight: 850;
  margin-bottom: 10px;
}

.ai-reason-card p {
  margin: 0;
  color: #0f172a;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
}

.max-score-line {
  display: inline-block;
  color: #133b7a;
  font-weight: 950;
  font-size: 21px;
  border-bottom: 4px solid #2563eb;
  padding-bottom: 2px;
  margin-bottom: 12px;
}

.next-item-btn {
  width: 100%;
  margin-top: 16px;
}

.total-card {
  min-width: 250px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #fecaca;
  background: #fff7ed;
  border-left: 5px solid #b91c1c;
}

.total-card.in-detail {
  margin-top: 14px;
  min-width: 0;
}

.total-card span {
  display: block;
  color: #991b1b;
  font-weight: 850;
}

.total-card strong {
  display: block;
  margin-top: 6px;
  color: #7f1d1d;
  font-size: 34px;
  line-height: 1.1;
}

.total-card small {
  display: block;
  margin-top: 8px;
  color: #475569;
  line-height: 1.5;
}

.text-preview {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  max-height: 480px;
  overflow: auto;
}

.path-list {
  line-height: 1.8;
  word-break: break-all;
}

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .score-header {
    display: block;
  }

  .total-card {
    margin-top: 12px;
  }
}
</style>
