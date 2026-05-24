<template>
  <div class="stack">
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      title="AI 初评结果仅作为建议分，不作为最终成绩。系统发送给 AI 的文本使用脱敏文本，不发送学生真实姓名、学号和班级。"
    />

    <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />
    <TaskFlowNav
      :task-id="selectedTask?.id"
      :task-name="selectedTask?.task_name"
      current="ai"
    />

    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="选择批改任务" name="select">
        <GradingTaskSelectPanel
          description="先按学期、课程、教学班和实验任务筛选，再选择需要执行 AI 初评的批改任务。默认只显示进行中的任务。"
          :initial-task-id="route.query.task_id"
          @change="selectTask"
        />
      </el-tab-pane>

      <el-tab-pane label="批量初评" name="settings">
    <el-empty v-if="!selectedTask" description="请先在“选择批改任务”中选择一个批改任务。" />
    <el-card v-else class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>AI 配置与批量初评设置</strong>
            <div class="muted">批量初评采用统一策略处理多份报告；如需逐份选择截图，请使用“单份初评”。</div>
          </div>
          <el-button :loading="testing" @click="testDefault">测试 AI 配置</el-button>
        </div>
      </template>

      <el-alert
        v-if="!defaultConfig"
        type="error"
        :closable="false"
        title="当前没有默认 AI 配置，请先到 AI 模型配置页面设置默认配置。"
      />

      <div v-else class="config-panel">
        <div class="config-row">
          <div>
            <span>服务商</span>
            <strong>{{ defaultConfig.provider_name }}</strong>
          </div>
          <div>
            <span>文本模型</span>
            <strong>{{ defaultConfig.text_model }}</strong>
          </div>
          <div>
            <span>视觉模型</span>
            <strong>{{ defaultConfig.vision_model || '未配置' }}</strong>
          </div>
          <div>
            <span>支持视觉</span>
            <strong>{{ defaultConfig.supports_vision ? '是' : '否' }}</strong>
          </div>
        </div>
          <div class="mode-note">
          调用方式：OpenAI SDK + 流式输出；评分模式：快速评分；Prompt 模板版本：scoring_prompt_v2.2；批量截图策略：{{ batchUseVisionScoring ? (batchImageMode === 'first_3' ? '每份报告前 3 张' : '每份报告全部截图') : '不发送截图' }}；最大发送报告文本：6000 字符；最大输出：2048 tokens。
        </div>
      </div>

      <div class="vision-settings mt">
        <div class="setting-line">
          <el-checkbox v-model="batchUseVisionScoring" :disabled="!visionAvailable">
            批量初评启用截图识别 / 图文评分
          </el-checkbox>
          <span class="muted" v-if="!visionAvailable">当前默认 AI 配置未启用视觉模型，不能发送截图。</span>
        </div>
        <el-radio-group v-model="batchImageMode" :disabled="!batchUseVisionScoring">
          <el-radio-button label="first_3">前 3 张截图</el-radio-button>
          <el-radio-button label="all">全部截图</el-radio-button>
        </el-radio-group>
        <el-alert
          v-if="batchUseVisionScoring"
          class="mt"
          type="warning"
          :closable="false"
          title="批量初评会对每份可初评报告使用同一截图策略，不支持逐份自选截图。截图可能包含账号、路径、头像等敏感信息，请确认后再启用。"
        />
        <div class="mode-note">
          当前批量模式：{{ batchUseVisionScoring ? '图文评分' : '纯文本评分' }}；截图范围：{{ batchImageMode === 'first_3' ? '每份报告前 3 张' : '每份报告全部截图' }}。
          纯文本模式下只发送截图数量说明，不发送图片内容。
        </div>
      </div>

      <div class="summary-grid mt">
        <div class="ai-metric">
          <span>总提交数</span>
          <strong>{{ aiSummary.total }}</strong>
        </div>
        <div class="ai-metric">
          <span>已解析</span>
          <strong>{{ aiSummary.parsed }}</strong>
        </div>
        <div class="ai-metric warning">
          <span>待初评/失败</span>
          <strong>{{ aiSummary.pending }}</strong>
        </div>
        <div class="ai-metric success">
          <span>初评完成</span>
          <strong>{{ aiSummary.done }}</strong>
        </div>
        <div class="ai-metric danger">
          <span>初评失败</span>
          <strong>{{ aiSummary.failed }}</strong>
        </div>
      </div>

      <div class="button-row">
        <el-button type="primary" :loading="batchScoring" :disabled="!defaultConfig || aiSummary.parsed === 0" @click="scoreTask(false)">
          批量初评
        </el-button>
        <el-button :loading="batchScoring" :disabled="!defaultConfig || aiSummary.parsed === 0" @click="scoreTask(true)">
          重新初评已完成报告
        </el-button>
      </div>

      <el-alert
        class="mt"
        type="info"
        :closable="false"
        title="批量初评只处理已匹配或姓名不一致、且已完成解析与脱敏的报告。未匹配、重复提交和重复作废记录不会进入 AI 初评。"
      />
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="单份初评" name="submissions">
    <el-empty v-if="!selectedTask" description="请先选择批改任务后查看提交列表。" />
    <el-card v-else class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>选择单份报告</strong>
            <div class="muted">点击任意行选择报告，然后在下方查看截图并决定本次单份初评是否发送图片。</div>
          </div>
          <el-button :loading="loadingSubmissions" @click="refreshTaskData">刷新列表</el-button>
        </div>
      </template>

      <el-row :gutter="16" class="mb">
        <el-col :span="8">
          <el-select v-model="aiStatusFilter" style="width: 100%" placeholder="按 AI 状态筛选">
            <el-option label="全部 AI 状态" value="" />
            <el-option label="未初评" value="未初评" />
            <el-option label="初评中" value="初评中" />
            <el-option label="初评完成" value="初评完成" />
            <el-option label="初评失败" value="初评失败" />
          </el-select>
        </el-col>
      </el-row>

      <el-table
        :data="filteredSubmissions"
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
        <el-table-column label="AI 状态" width="120">
          <template #default="{ row }">
            <el-tag :type="aiTagType(row.ai_status)">{{ row.ai_status || '未初评' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AI 建议总分" width="120">
          <template #default="{ row }">{{ formatScore(row.ai_total_score) }}</template>
        </el-table-column>
        <el-table-column prop="ai_error" label="错误信息" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :loading="singleScoringId === row.id" :disabled="!canScore(row)" @click.stop="scoreOne(row)">
              初评
            </el-button>
            <el-button size="small" :disabled="row.ai_status === '未初评'" @click.stop="resetAI(row)">重置</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="image-select-panel mt">
        <div class="toolbar image-panel-header">
          <div>
            <div class="panel-title">单份报告截图预览与发送选择</div>
            <div class="muted">
              这里仅影响当前选中报告的单份初评；批量初评不会使用“自选截图”。
            </div>
          </div>
          <div class="button-row compact">
            <el-button v-if="selectedDetail" @click="refreshImages">刷新截图预览</el-button>
            <el-button v-if="selectedDetail" @click="activeTab = 'detail'">查看 AI 结果</el-button>
            <el-button
              v-if="selectedDetail"
              type="primary"
              :loading="singleScoringId === selectedDetail.id"
              :disabled="!canScore(selectedDetail)"
              @click="scoreOne(selectedDetail)"
            >
              对当前报告执行 AI 初评
            </el-button>
          </div>
        </div>

        <el-empty v-if="!selectedDetail" description="请先在上方提交列表中选择一份报告。" />
        <template v-else>
          <el-descriptions :column="4" border class="mb">
            <el-descriptions-item label="当前报告">{{ selectedDetail.original_filename }}</el-descriptions-item>
            <el-descriptions-item label="学号">{{ selectedDetail.student_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ selectedDetail.student_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="截图数量">{{ selectedDetailImagePaths.length }}</el-descriptions-item>
          </el-descriptions>

          <div class="vision-settings single-vision-settings">
            <div class="setting-line">
              <el-checkbox v-model="useVisionScoring" :disabled="!visionAvailable">
                本报告启用截图识别 / 图文评分
              </el-checkbox>
              <span class="muted" v-if="!visionAvailable">当前默认 AI 配置未启用视觉模型，不能发送截图。</span>
            </div>
            <el-radio-group v-model="imageMode" :disabled="!useVisionScoring">
              <el-radio-button label="first_3">前 3 张截图</el-radio-button>
              <el-radio-button label="all">全部截图</el-radio-button>
              <el-radio-button label="custom">自选截图</el-radio-button>
            </el-radio-group>
          </div>

          <div class="request-diagnostics">
            <div><span>当前模式</span><strong>{{ useVisionScoring ? '图文评分' : '纯文本评分' }}</strong></div>
            <div><span>截图数量</span><strong>{{ selectedDetailImagePaths.length }}</strong></div>
            <div><span>预计发送图片</span><strong>{{ estimatedImageCount }}</strong></div>
            <div><span>图片策略</span><strong>{{ imageMode === 'first_3' ? '前 3 张' : imageMode === 'all' ? '全部截图' : '自选截图' }}</strong></div>
          </div>

          <el-alert
            v-if="useVisionScoring"
            class="mt"
            type="warning"
            :closable="false"
            title="截图可能包含账号、路径、头像等敏感信息。请教师确认截图安全后再发送给 AI。"
          />
          <el-alert
            v-if="useVisionScoring && imageMode === 'custom'"
            class="mt"
            type="info"
            :closable="false"
            title="自选截图模式下，请在缩略图下方勾选需要发送给 AI 的截图。"
          />
          <el-empty v-if="selectedDetailImagePaths.length === 0" description="当前报告没有提取到截图" />
          <div v-else class="image-grid">
            <div
              v-for="(path, index) in selectedDetailImagePaths"
              :key="path"
              class="image-choice-card"
              :class="{ selected: shouldSendImage(index + 1), muted: useVisionScoring && !shouldSendImage(index + 1) }"
            >
              <el-image
                :src="reviewImageUrl(index + 1)"
                fit="contain"
                :preview-src-list="selectedDetailImageUrls"
              >
                <template #error>
                  <div class="image-error">
                    图片加载失败<br />
                    请重新解析报告或检查图片文件是否存在
                  </div>
                </template>
              </el-image>
              <div class="image-choice-footer">
                <strong>截图 {{ index + 1 }}</strong>
                <el-checkbox
                  v-if="imageMode === 'custom'"
                  v-model="selectedImageIndices"
                  :label="index + 1"
                  :disabled="!useVisionScoring"
                >
                  发送给 AI
                </el-checkbox>
                <el-tag v-else :type="shouldSendImage(index + 1) ? 'success' : 'info'">
                  {{ shouldSendImage(index + 1) ? '将发送' : '不发送' }}
                </el-tag>
              </div>
            </div>
          </div>
        </template>
      </div>
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="AI 初评结果" name="detail">
    <el-empty v-if="!selectedDetail" description="请先在提交列表中选择一份报告。" />
    <el-card v-else class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>AI 初评结果查看</strong>
            <div class="muted">{{ selectedDetail.original_filename }}</div>
          </div>
          <el-button type="primary" :loading="singleScoringId === selectedDetail.id" :disabled="!canScore(selectedDetail)" @click="scoreOne(selectedDetail)">
            对该报告执行 AI 初评
          </el-button>
        </div>
      </template>

      <el-descriptions :column="4" border>
        <el-descriptions-item label="学号">{{ selectedDetail.student_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ selectedDetail.student_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="AI 状态">
          <el-tag :type="aiTagType(selectedDetail.ai_status)">{{ selectedDetail.ai_status || '未初评' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="AI 建议总分">{{ formatScore(selectedDetail.ai_total_score) }}</el-descriptions-item>
        <el-descriptions-item label="Prompt 版本">{{ selectedDetail.ai_prompt_version || '未记录' }}</el-descriptions-item>
      </el-descriptions>

      <el-alert v-if="!canScore(selectedDetail)" class="mt" type="warning" :closable="false" :title="scoreBlockReason(selectedDetail)" />
      <el-alert v-if="selectedDetail.ai_error" class="mt" type="error" :closable="false" :title="selectedDetail.ai_error" />

      <el-table class="mt" :data="aiScores" border stripe empty-text="暂无分项建议分">
        <el-table-column prop="item_name" label="评分项" min-width="180" show-overflow-tooltip />
        <el-table-column prop="max_score" label="满分" width="90" />
        <el-table-column prop="ai_score" label="AI 建议分" width="120" />
        <el-table-column prop="deduction_reason" label="扣分原因" min-width="280" show-overflow-tooltip />
        <el-table-column prop="confidence" label="置信度" width="90" />
        <el-table-column label="重点复核" width="100">
          <template #default="{ row }">{{ row.need_teacher_review ? '是' : '否' }}</template>
        </el-table-column>
      </el-table>

      <el-collapse class="mt">
        <el-collapse-item title="查看脱敏文本摘要">
          <pre class="text-preview">{{ previewText(selectedDetail.anonymized_text) }}</pre>
        </el-collapse-item>
        <el-collapse-item title="查看原始 AI 响应">
          <pre class="text-preview">{{ selectedDetail.ai_raw_response || '暂无' }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
const aiScores = ref([])
const defaultConfig = ref(null)
const testing = ref(false)
const batchScoring = ref(false)
const singleScoringId = ref(null)
const loadingSubmissions = ref(false)
const aiStatusFilter = ref('')
const route = useRoute()
const activeTab = ref(String(route.query.tab || 'select'))
const batchUseVisionScoring = ref(false)
const batchImageMode = ref('first_3')
const useVisionScoring = ref(false)
const imageMode = ref('first_3')
const selectedImageIndices = ref([])
const imageReloadKey = ref(Date.now())
const { actionNotice, showNotice, clearNotice } = useActionNotice()

watch(() => route.query.tab, (tab) => {
  if (typeof tab === 'string' && tab) {
    activeTab.value = tab
  }
})

const aiSummary = reactive({
  total: 0,
  parsed: 0,
  pending: 0,
  done: 0,
  failed: 0
})

const filteredSubmissions = computed(() =>
  aiStatusFilter.value ? submissions.value.filter((row) => row.ai_status === aiStatusFilter.value) : submissions.value
)

const selectedDetailImagePaths = computed(() => parseImagePaths(selectedDetail.value?.image_paths))
const selectedDetailImageUrls = computed(() => selectedDetailImagePaths.value.map((_, index) => reviewImageUrl(index + 1)))
const estimatedImageCount = computed(() => {
  if (!useVisionScoring.value) return 0
  const count = selectedDetailImagePaths.value.length
  if (imageMode.value === 'all') return count
  if (imageMode.value === 'custom') return selectedImageIndices.value.length
  return Math.min(3, count)
})
const visionAvailable = computed(() => Boolean(defaultConfig.value?.supports_vision && (defaultConfig.value?.vision_model || defaultConfig.value?.text_model)))

async function loadDefaultConfig() {
  const configResult = await api.getDefaultAIProvider()
  defaultConfig.value = configResult.data
}

async function selectTask(row) {
  if (!row || !isActiveTask(row)) {
    selectedTask.value = null
    selectedDetail.value = null
    aiScores.value = []
    submissions.value = []
    resetSummary()
    return
  }
  if (selectedTask.value?.id === row.id) return
  selectedTask.value = row
  selectedDetail.value = null
  aiScores.value = []
  await refreshTaskData()
}

async function refreshTaskData() {
  if (!selectedTask.value) return
  await Promise.all([loadSubmissions(), loadAISummary()])
}

async function loadSubmissions() {
  if (!selectedTask.value) return
  loadingSubmissions.value = true
  try {
    const result = await api.listSubmissions(selectedTask.value.id)
    submissions.value = result.data || []
    if (selectedDetail.value && !submissions.value.some((item) => item.id === selectedDetail.value.id)) {
      selectedDetail.value = null
      aiScores.value = []
    }
  } finally {
    loadingSubmissions.value = false
  }
}

async function loadAISummary() {
  if (!selectedTask.value) return
  const result = await api.getAISummary(selectedTask.value.id)
  Object.assign(aiSummary, result.data || {})
}

async function testDefault() {
  testing.value = true
  try {
    const result = await api.testDefaultAIProvider()
    if (result.ok) {
      showNotice('success', result.message || '默认 AI 配置可用。')
    } else {
      showNotice('error', result.message || '默认 AI 配置测试失败。')
    }
  } finally {
    testing.value = false
  }
}

async function scoreTask(rescoreCompleted) {
  if (!selectedTask.value) return
  if (rescoreCompleted) {
    await ElMessageBox.confirm('确认重新初评已完成报告？原有 AI 分项建议分会被覆盖。', '重新初评确认', {
      type: 'warning'
    })
  }
  batchScoring.value = true
  try {
    const result = await api.scoreTask(selectedTask.value.id, rescoreCompleted, batchUseVisionScoring.value, batchImageMode.value)
    const data = result.data || {}
    showNotice('success', `批量初评完成：成功 ${data.success || 0} 份，失败 ${data.failed || 0} 份，跳过 ${data.skipped || 0} 份。`)
    await refreshTaskData()
  } finally {
    batchScoring.value = false
  }
}

async function scoreOne(row) {
  if (!row || !canScore(row)) return
  if (useVisionScoring.value && imageMode.value === 'custom' && selectedDetail.value?.id !== row.id) {
    showNotice('warning', '自选截图模式下，请先点击该报告所在行，查看并勾选要发送的截图。')
    return
  }
  if (useVisionScoring.value && imageMode.value === 'custom' && selectedImageIndices.value.length === 0) {
    showNotice('warning', '已选择自选截图模式，请先勾选至少一张截图，或切换为纯文本模式。')
    return
  }
  singleScoringId.value = row.id
  try {
    const result = await api.scoreSubmission(
      row.id,
      true,
      useVisionScoring.value,
      imageMode.value,
      imageMode.value === 'custom' ? selectedImageIndices.value : []
    )
    if (result.ok) {
      showNotice('success', result.message || 'AI 初评完成。')
    } else {
      showNotice('error', result.message || 'AI 初评失败。')
    }
    await refreshTaskData()
    await selectSubmission(row)
  } finally {
    singleScoringId.value = null
  }
}

async function resetAI(row) {
  if (!row) return
  await api.resetSubmissionAI(row.id)
  showNotice('success', 'AI 状态已重置。')
  await refreshTaskData()
  await selectSubmission(row)
}

async function selectSubmission(row) {
  if (!row) {
    selectedDetail.value = null
    aiScores.value = []
    return
  }
  const [detailResult, scoreResult] = await Promise.all([api.getSubmission(row.id), api.listAIScores(row.id)])
  selectedDetail.value = detailResult.data
  aiScores.value = scoreResult.data || []
  selectedImageIndices.value = []
  imageReloadKey.value = Date.now()
}

function refreshImages() {
  imageReloadKey.value = Date.now()
  showNotice('success', '截图预览已刷新。')
}

function shouldSendImage(index) {
  if (!useVisionScoring.value) return false
  const imageCount = selectedDetailImagePaths.value.length
  if (index < 1 || index > imageCount) return false
  if (imageMode.value === 'all') return true
  if (imageMode.value === 'custom') return selectedImageIndices.value.includes(index)
  return index <= Math.min(3, imageCount)
}

function canScore(row) {
  return (
    !!defaultConfig.value &&
    ['已匹配', '姓名不一致'].includes(row?.match_status) &&
    row?.parse_status === '解析完成'
  )
}

function scoreBlockReason(row) {
  if (!defaultConfig.value) return '当前没有默认 AI 配置，请先配置默认模型。'
  if (!['已匹配', '姓名不一致'].includes(row?.match_status)) {
    if (row?.match_status === '重复提交') return '该报告为重复提交，请先到“提交匹配”页面确认使用哪一份报告。'
    if (row?.match_status === '重复作废') return '该报告已标记为重复作废，不参与 AI 初评。'
    return '该报告尚未完成学生匹配，不能进行 AI 初评。'
  }
  if (row?.parse_status !== '解析完成') return '该报告尚未完成解析与脱敏，请先到“解析与脱敏”页面处理。'
  return ''
}

function previewText(text) {
  if (!text) return '暂无内容。'
  return text.length > 3000 ? `${text.slice(0, 3000)}\n\n……（仅显示前 3000 字）` : text
}

function parseImagePaths(value) {
  if (!value) return []
  if (Array.isArray(value)) return value
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function reviewImageUrl(index) {
  if (!selectedDetail.value?.id) return ''
  return `${api.reviewImageUrl(selectedDetail.value.id, index)}?t=${imageReloadKey.value}`
}

function formatScore(value) {
  if (value === null || value === undefined || value === '') return '暂无'
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : '暂无'
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

function aiTagType(status) {
  if (status === '初评完成') return 'success'
  if (status === '初评失败') return 'danger'
  if (status === '初评中') return 'warning'
  return 'info'
}

function resetSummary() {
  Object.assign(aiSummary, {
    total: 0,
    parsed: 0,
    pending: 0,
    done: 0,
    failed: 0
  })
}

onMounted(loadDefaultConfig)
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

.list-tools {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}

.list-tools .el-input {
  max-width: 460px;
}

.config-panel {
  display: grid;
  gap: 14px;
}

.config-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.config-row > div,
.ai-metric {
  padding: 14px 16px;
  border: 1px solid #d8e8f3;
  border-radius: 12px;
  background: linear-gradient(180deg, #fff 0%, #f3fbff 100%);
}

.config-row span,
.ai-metric span {
  display: block;
  color: #64748b;
  font-size: 13px;
  line-height: 1.4;
}

.config-row strong {
  display: block;
  margin-top: 8px;
  color: #0f4c81;
  font-size: 22px;
  line-height: 1.2;
  word-break: break-word;
}

.mode-note {
  padding: 12px 14px;
  border-radius: 12px;
  background: #eff8ff;
  color: #0f4c81;
  border: 1px solid #c9e7fb;
  line-height: 1.7;
}

.vision-settings {
  display: grid;
  gap: 12px;
}

.setting-line {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.request-diagnostics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.request-diagnostics > div {
  padding: 12px 14px;
  border: 1px solid #d8e8f3;
  border-radius: 12px;
  background: #fbfdff;
}

.request-diagnostics span {
  display: block;
  color: #64748b;
  font-size: 13px;
}

.request-diagnostics strong {
  display: block;
  margin-top: 6px;
  color: #0f4c81;
  font-size: 18px;
}

.image-select-panel {
  border: 1px solid #d8e8f3;
  border-radius: 14px;
  background: #fbfdff;
  padding: 14px;
}

.panel-title {
  color: #08344f;
  font-size: 17px;
  font-weight: 850;
  margin-bottom: 10px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.image-choice-card {
  border: 1px solid #d8e8f3;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.image-choice-card .el-image {
  width: 100%;
  height: 160px;
  border-radius: 8px;
  background: #f8fafc;
}

.image-choice-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.ai-metric strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  color: #0f4c81;
  line-height: 1.1;
}

.ai-metric.success strong {
  color: #15803d;
}

.ai-metric.warning strong {
  color: #b45309;
}

.ai-metric.danger strong {
  color: #b91c1c;
}

.button-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.button-row.compact {
  margin-top: 0;
  justify-content: flex-end;
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

@media (max-width: 1180px) {
  .config-row,
  .summary-grid,
  .request-diagnostics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
