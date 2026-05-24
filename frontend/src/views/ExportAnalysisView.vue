<template>
  <div class="stack">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="成绩统计基于教师确认分生成。AI 建议分只作为参考，未复核报告不建议作为正式成绩。"
    />
    <TaskFlowNav
      :task-id="selectedTask?.id"
      :task-name="selectedTask?.task_name"
      current="export"
    />

    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="选择批改任务" name="select">
        <GradingTaskSelectPanel
          description="先按学期、课程、教学班和实验任务筛选，再选择需要查看成绩与分析的批改任务。默认只显示进行中的任务。"
          :initial-task-id="route.query.task_id"
          @change="selectTask"
        />
      </el-tab-pane>

      <el-tab-pane label="成绩概览" name="overview">
    <el-empty v-if="!selectedTask" description="请选择一个批改任务后查看成绩概览。" />

    <template v-else>
      <el-card class="page-card" v-loading="loadingData">
        <template #header>
          <div class="toolbar">
            <div>
              <strong>成绩查看口径</strong>
              <div class="muted">这里控制页面预览和统计分析的数据范围；真正下载文件请使用下方“Excel 文件下载”。</div>
            </div>
            <el-segmented v-model="mode" :options="modeOptions" @change="loadExportData" />
          </div>
        </template>

        <div class="task-strip">
          <div><span>课程</span><strong>{{ selectedTask.course_name }}</strong></div>
          <div><span>教学班</span><strong>{{ selectedTask.class_name }}</strong></div>
          <div><span>实验任务</span><strong>{{ selectedTask.experiment_name }}</strong></div>
          <div><span>批改任务</span><strong>{{ selectedTask.task_name }}</strong></div>
        </div>

        <div class="summary-grid">
          <div v-for="item in summaryCards" :key="item.label" class="metric-card">
            <div class="metric-label">{{ item.label }}</div>
            <div class="metric-value">{{ item.value }}</div>
          </div>
        </div>
      </el-card>
    </template>
      </el-tab-pane>

      <el-tab-pane label="成绩预览" name="preview">
    <el-empty v-if="!selectedTask" description="请选择一个批改任务后查看成绩预览。" />
    <template v-else>
      <el-card class="page-card" v-loading="loadingData">
        <template #header>
          <div class="toolbar">
            <div>
              <strong>成绩预览</strong>
              <div class="muted">用于核对学生成绩、复核状态和提交文件。当前表格不会下载文件。</div>
            </div>
            <el-tag type="primary" effect="light">{{ modeLabel }}</el-tag>
          </div>
        </template>

        <el-table :data="preview.grades" border stripe empty-text="暂无成绩记录" height="420">
          <el-table-column prop="学号" label="学号" width="130" />
          <el-table-column prop="姓名" label="姓名" width="100" />
          <el-table-column prop="班级" label="班级" width="130" />
          <el-table-column prop="匿名编号" label="匿名编号" width="100" />
          <el-table-column prop="AI建议总分" label="AI 建议总分" width="120" align="right" />
          <el-table-column prop="教师确认总分" label="教师确认总分" width="130" align="right" />
          <el-table-column prop="复核状态" label="复核状态" width="100" />
          <el-table-column prop="导出状态" label="状态说明" min-width="170" show-overflow-tooltip />
          <el-table-column prop="提交文件名" label="提交文件名" min-width="240" show-overflow-tooltip />
          <el-table-column prop="复核时间" label="复核时间" width="170" />
        </el-table>

        <el-alert
          v-if="preview.unfinished.length"
          class="mt"
          type="warning"
          :closable="false"
          :title="`当前还有 ${preview.unfinished.length} 条未完成或不建议用于正式成绩的记录。`"
        />
      </el-card>
    </template>
      </el-tab-pane>

      <el-tab-pane label="班级分析" name="analysis">
    <el-empty v-if="!selectedTask" description="请选择一个批改任务后查看班级分析。" />
    <template v-else>
      <el-card class="page-card" v-loading="loadingData">
        <template #header>
          <div class="toolbar">
            <div>
              <strong>班级分析</strong>
              <div class="muted">统计图基于当前查看口径生成，重点用于发现分数段、评分项薄弱点和人机评分差异。</div>
            </div>
            <el-tag type="success" effect="light">图表预览</el-tag>
          </div>
        </template>

        <el-row :gutter="18" class="chart-row">
          <el-col :span="12">
            <div class="chart-card">
              <div class="chart-title">分数段分布</div>
              <div ref="distributionChartRef" class="chart"></div>
              <el-empty v-if="analysis.distribution.length === 0" description="暂无分数段数据" />
            </div>
          </el-col>
          <el-col :span="12">
            <div class="chart-card">
              <div class="chart-title">评分项平均得分率</div>
              <div ref="rubricChartRef" class="chart"></div>
              <el-empty v-if="analysis.rubric_analysis.length === 0" description="暂无评分项分析数据" />
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="18" class="chart-row">
          <el-col :span="10">
            <div class="chart-card">
              <div class="chart-title">及格情况</div>
              <div ref="passFailChartRef" class="chart compact"></div>
              <el-empty v-if="analysis.pass_fail.length === 0" description="暂无及格情况数据" />
            </div>
          </el-col>
          <el-col :span="14">
            <div class="chart-card">
              <div class="chart-title">人与 AI 评分差值</div>
              <div ref="aiDiffChartRef" class="chart compact"></div>
              <el-empty v-if="analysis.ai_diff.length === 0" description="暂无人机差值数据" />
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="18" class="mt">
          <el-col :span="12">
            <el-table :data="analysis.distribution" border stripe empty-text="暂无分数段数据">
              <el-table-column prop="分数段" label="分数段" />
              <el-table-column prop="人数" label="人数" width="120" align="right" />
            </el-table>
          </el-col>
          <el-col :span="12">
            <el-table :data="analysis.rubric_analysis" border stripe empty-text="暂无评分项分析数据">
              <el-table-column prop="评分项" label="评分项" min-width="180" show-overflow-tooltip />
              <el-table-column prop="满分" label="满分" width="80" align="right" />
              <el-table-column prop="平均分" label="平均分" width="90" align="right" />
              <el-table-column prop="平均得分率" label="平均得分率" width="110" align="right">
                <template #default="{ row }">{{ row.平均得分率 == null ? '-' : `${row.平均得分率}%` }}</template>
              </el-table-column>
              <el-table-column prop="教师改动次数" label="改动次数" width="100" align="right" />
            </el-table>
          </el-col>
        </el-row>
      </el-card>
    </template>
      </el-tab-pane>

      <el-tab-pane label="未完成名单" name="unfinished">
    <el-empty v-if="!selectedTask" description="请选择一个批改任务后查看未完成名单。" />
    <template v-else>
      <el-card v-if="preview.unfinished.length" class="page-card">
        <template #header>
          <strong>未完成或不建议用于正式成绩的记录</strong>
        </template>
        <el-table :data="preview.unfinished" border stripe>
          <el-table-column prop="学号" label="学号" width="130" />
          <el-table-column prop="姓名" label="姓名" width="100" />
          <el-table-column prop="班级" label="班级" width="130" />
          <el-table-column prop="状态" label="状态" width="180" />
          <el-table-column prop="提交文件名" label="提交文件名" min-width="240" show-overflow-tooltip />
        </el-table>
      </el-card>
      <el-empty v-else description="当前查看范围内暂无未完成或异常记录。" />
    </template>
      </el-tab-pane>

      <el-tab-pane label="Excel 下载" name="download">
    <el-empty v-if="!selectedTask" description="请选择一个批改任务后下载 Excel 文件。" />
    <template v-else>
      <el-card class="page-card">
        <template #header>
          <div>
            <strong>Excel 文件下载</strong>
            <div class="muted">下载文件会按当前查看口径生成。正式归档建议使用“仅查看已复核成绩”。</div>
          </div>
        </template>
        <div class="download-grid">
          <div class="download-card">
            <h3>成绩表</h3>
            <p>包含学生信息、AI 建议总分、教师确认总分、复核状态、提交文件名和分项成绩。</p>
            <el-button type="primary" @click="downloadGrades">下载成绩 Excel</el-button>
          </div>
          <div class="download-card">
            <h3>班级分析</h3>
            <p>包含分析概览、分数段分布、评分项得分率、及格情况、人机评分差值和图形分析。</p>
            <el-button @click="downloadAnalysis">下载班级分析 Excel</el-button>
          </div>
        </div>
      </el-card>
    </template>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import GradingTaskSelectPanel from '@/components/GradingTaskSelectPanel.vue'
import TaskFlowNav from '@/components/TaskFlowNav.vue'
import { isTaskActive } from '@/utils/taskStatus'

const modeOptions = [
  { label: '仅查看已复核成绩', value: 'reviewed_only' },
  { label: '查看全班状态表', value: 'all_status' }
]

const selectedTask = ref(null)
const mode = ref('reviewed_only')
const loadingData = ref(false)
const route = useRoute()
const activeTab = ref(String(route.query.tab || 'select'))
const preview = reactive({ summary: {}, grades: [], items: [], unfinished: [] })
const analysis = reactive({ summary: {}, distribution: [], rubric_analysis: [], pass_fail: [], ai_diff: [] })

const distributionChartRef = ref(null)
const rubricChartRef = ref(null)
const passFailChartRef = ref(null)
const aiDiffChartRef = ref(null)
let charts = []

watch(() => route.query.tab, (tab) => {
  if (typeof tab === 'string' && tab) {
    activeTab.value = tab
  }
})

const modeLabel = computed(() => modeOptions.find((item) => item.value === mode.value)?.label || '当前口径')
const summaryCards = computed(() => {
  const summary = preview.summary || {}
  return [
    { label: '名单人数', value: valueOrDash(summary.班级名单人数) },
    { label: '成绩记录数', value: valueOrDash(summary.成绩记录数) },
    { label: '已复核人数', value: valueOrDash(summary.已复核人数) },
    { label: '满分', value: valueOrDash(summary.满分) },
    { label: '平均分', value: valueOrDash(summary.平均分) },
    { label: '最高分', value: valueOrDash(summary.最高分) },
    { label: '最低分', value: valueOrDash(summary.最低分) },
    { label: '中位数', value: valueOrDash(summary.中位数) },
    { label: '及格率', value: summary.及格率 == null ? '-' : `${summary.及格率}%` },
    { label: '人与 AI 平均差值', value: valueOrDash(summary.人与AI平均差值) }
  ]
})

async function selectTask(row) {
  if (!row || !isActiveTask(row)) {
    selectedTask.value = null
    resetData()
    return
  }
  if (selectedTask.value?.id === row.id) return
  selectedTask.value = row
  resetData()
  await loadExportData()
}

async function loadExportData() {
  if (!selectedTask.value) return
  loadingData.value = true
  try {
    const [previewResult, analysisResult] = await Promise.all([
      api.getExportPreview(selectedTask.value.id, mode.value),
      api.getClassAnalysis(selectedTask.value.id, mode.value)
    ])
    Object.assign(preview, previewResult.data || { summary: {}, grades: [], items: [], unfinished: [] })
    Object.assign(analysis, analysisResult.data || { summary: {}, distribution: [], rubric_analysis: [], pass_fail: [], ai_diff: [] })
    await nextTick()
    renderCharts()
  } finally {
    loadingData.value = false
  }
}

function resetData() {
  Object.assign(preview, { summary: {}, grades: [], items: [], unfinished: [] })
  Object.assign(analysis, { summary: {}, distribution: [], rubric_analysis: [], pass_fail: [], ai_diff: [] })
  disposeCharts()
}

function valueOrDash(value) {
  return value == null || value === '' ? '-' : value
}

function downloadGrades() {
  if (selectedTask.value) window.open(api.gradesExcelUrl(selectedTask.value.id, mode.value), '_blank')
}

function downloadAnalysis() {
  if (selectedTask.value) window.open(api.analysisExcelUrl(selectedTask.value.id, mode.value), '_blank')
}

function renderCharts() {
  disposeCharts()
  charts = [
    renderDistributionChart(),
    renderRubricChart(),
    renderPassFailChart(),
    renderAiDiffChart()
  ].filter(Boolean)
}

function baseChartOptions(titleHidden = true) {
  return {
    animationDuration: 350,
    title: { show: !titleHidden },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 112, right: 28, top: 20, bottom: 36, containLabel: true },
    xAxis: { type: 'value', axisLine: { lineStyle: { color: '#b7d3e6' } }, splitLine: { lineStyle: { color: '#e4eef5' } } },
    yAxis: {
      type: 'category',
      axisLine: { lineStyle: { color: '#b7d3e6' } },
      axisTick: { show: false },
      axisLabel: { color: '#33576d', width: 150, overflow: 'truncate' }
    }
  }
}

function renderDistributionChart() {
  if (!distributionChartRef.value || analysis.distribution.length === 0) return null
  const chart = echarts.init(distributionChartRef.value)
  chart.setOption({
    ...baseChartOptions(),
    yAxis: { ...baseChartOptions().yAxis, data: analysis.distribution.map((item) => item.分数段) },
    series: [{
      name: '人数',
      type: 'bar',
      data: analysis.distribution.map((item) => Number(item.人数 || 0)),
      itemStyle: { color: '#0284c7', borderRadius: [0, 8, 8, 0] },
      label: { show: true, position: 'right', formatter: '{c} 人', color: '#0f2233' }
    }]
  })
  return chart
}

function renderRubricChart() {
  if (!rubricChartRef.value || analysis.rubric_analysis.length === 0) return null
  const rows = [...analysis.rubric_analysis].reverse()
  const chart = echarts.init(rubricChartRef.value)
  chart.setOption({
    ...baseChartOptions(),
    grid: { left: 160, right: 34, top: 20, bottom: 36, containLabel: true },
    xAxis: { ...baseChartOptions().xAxis, max: 100, name: '平均得分率（%）' },
    yAxis: { ...baseChartOptions().yAxis, data: rows.map((item) => item.评分项), axisLabel: { color: '#33576d', width: 190, overflow: 'truncate' } },
    series: [{
      name: '平均得分率',
      type: 'bar',
      data: rows.map((item) => Number(item.平均得分率 || 0)),
      itemStyle: { color: '#0891b2', borderRadius: [0, 8, 8, 0] },
      label: { show: true, position: 'right', formatter: '{c}%', color: '#0f2233' }
    }]
  })
  return chart
}

function renderPassFailChart() {
  if (!passFailChartRef.value || analysis.pass_fail.length === 0) return null
  const chart = echarts.init(passFailChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      name: '及格情况',
      type: 'pie',
      radius: ['48%', '72%'],
      center: ['50%', '42%'],
      data: analysis.pass_fail.map((item) => ({ name: item.类别, value: Number(item.人数 || 0) })),
      color: ['#0284c7', '#f59e0b'],
      label: { formatter: '{b}: {c} 人' }
    }]
  })
  return chart
}

function renderAiDiffChart() {
  if (!aiDiffChartRef.value || analysis.ai_diff.length === 0) return null
  const rows = [...analysis.ai_diff]
    .sort((a, b) => Math.abs(Number(b.人与AI评分差值 || 0)) - Math.abs(Number(a.人与AI评分差值 || 0)))
    .slice(0, 10)
    .reverse()
  const chart = echarts.init(aiDiffChartRef.value)
  chart.setOption({
    ...baseChartOptions(),
    grid: { left: 150, right: 34, top: 20, bottom: 36, containLabel: true },
    yAxis: { ...baseChartOptions().yAxis, data: rows.map((item) => item.学生), axisLabel: { color: '#33576d', width: 170, overflow: 'truncate' } },
    series: [{
      name: '人与 AI 评分差值',
      type: 'bar',
      data: rows.map((item) => Number(item.人与AI评分差值 || 0)),
      itemStyle: {
        borderRadius: [0, 8, 8, 0],
        color: (params) => (Number(params.value) >= 0 ? '#0f9f6e' : '#ef4444')
      },
      label: { show: true, position: 'right', formatter: '{c}', color: '#0f2233' }
    }]
  })
  return chart
}

function disposeCharts() {
  charts.forEach((chart) => chart.dispose())
  charts = []
}

function resizeCharts() {
  charts.forEach((chart) => chart.resize())
}

onMounted(() => {
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts()
})
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
  margin-top: 18px;
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

.task-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.task-strip > div {
  border: 1px solid #cfe3ee;
  border-radius: 10px;
  padding: 12px 14px;
  background: linear-gradient(180deg, #fbfdff, #f1f8fc);
  min-width: 0;
}

.task-strip span {
  display: block;
  color: #5f7890;
  font-size: 13px;
  margin-bottom: 6px;
}

.task-strip strong {
  display: block;
  color: #0f2233;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(138px, 1fr));
  gap: 12px;
}

.metric-card {
  border: 1px solid #cfe3ee;
  border-radius: 10px;
  padding: 14px;
  background: #fbfdff;
}

.metric-label {
  color: #5f7890;
  font-size: 13px;
}

.metric-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 800;
  color: #06425c;
}

.chart-row + .chart-row {
  margin-top: 18px;
}

.chart-card {
  position: relative;
  border: 1px solid #cfe3ee;
  border-radius: 12px;
  padding: 16px;
  background: #fbfdff;
  min-height: 360px;
}

.chart-title {
  font-size: 17px;
  font-weight: 800;
  color: #0f2233;
  margin-bottom: 10px;
}

.chart {
  width: 100%;
  height: 300px;
}

.chart.compact {
  height: 250px;
}

.download-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.download-card {
  border: 1px solid #cfe3ee;
  border-radius: 12px;
  padding: 18px;
  background: linear-gradient(180deg, #fbfdff, #f2f9fd);
}

.download-card h3 {
  margin: 0 0 8px;
  color: #06425c;
}

.download-card p {
  margin: 0 0 16px;
  color: #5f7890;
  line-height: 1.7;
}

@media (max-width: 1100px) {
  .task-strip,
  .download-grid {
    grid-template-columns: 1fr;
  }
}
</style>
