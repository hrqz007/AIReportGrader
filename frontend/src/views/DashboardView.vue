<template>
  <div class="dashboard-page">
    <section class="dashboard-hero">
      <div>
        <div class="eyebrow">本地教学评阅工作台</div>
        <h1>实验智评</h1>
        <p>
          面向高校课程实验报告评阅场景，支持课程、班级、学生名单、实验任务、评分标准、报告上传、
          AI 建议评分、教师复核和成绩导出的一体化本地工作流。
        </p>
      </div>
      <div class="hero-status">
        <div class="status-dot" :class="{ ok: health.ok }"></div>
        <div>
          <strong>{{ health.ok ? '后端服务正常' : '后端服务未连接' }}</strong>
          <span>{{ health.database || '等待服务响应' }}</span>
        </div>
      </div>
    </section>

    <el-row :gutter="18" class="metric-row">
      <el-col :xs="24" :sm="12" :lg="4" v-for="item in metrics" :key="item.label">
        <div class="metric-card dashboard-metric">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-note">{{ item.note }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="18" class="content-row">
      <el-col :xs="24" :lg="14">
        <el-card class="page-card">
          <template #header>
            <div class="toolbar header-tight">
              <div>
                <strong>推荐使用流程</strong>
                <div class="muted">按照真实教学批改顺序组织，减少跨页面来回查找。</div>
              </div>
            </div>
          </template>

          <div class="workflow-list">
            <div v-for="step in workflow" :key="step.title" class="workflow-item">
              <div class="workflow-index">{{ step.index }}</div>
              <div class="workflow-content">
                <div class="workflow-title">{{ step.title }}</div>
                <div class="workflow-desc">{{ step.desc }}</div>
              </div>
              <el-button link type="primary" @click="$router.push(step.path)">进入</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card class="page-card">
          <template #header>
            <div class="toolbar header-tight">
              <div>
                <strong>当前建设重点</strong>
                <div class="muted">V2 面向长期教学使用，优先提升稳定性和操作效率。</div>
              </div>
            </div>
          </template>

          <div class="module-list">
            <div v-for="module in modules" :key="module.title" class="module-item">
              <div>
                <div class="module-title">{{ module.title }}</div>
                <div class="module-desc">{{ module.desc }}</div>
              </div>
              <el-tag :type="module.type" effect="light">{{ module.status }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="page-card">
      <template #header>
        <div class="toolbar header-tight">
          <div>
            <strong>近期批改任务看板</strong>
            <div class="muted">默认只展示进行中的批改任务，已结束任务不会干扰后续工作流。</div>
          </div>
          <el-button :loading="taskBoardLoading" @click="loadTaskBoard">刷新</el-button>
        </div>
      </template>

      <el-table
        v-loading="taskBoardLoading"
        :data="taskBoardRows"
        border
        stripe
        empty-text="暂无进行中的批改任务"
      >
        <el-table-column prop="task_name" label="批改任务" min-width="260" show-overflow-tooltip />
        <el-table-column prop="course_name" label="课程" width="150" show-overflow-tooltip />
        <el-table-column prop="class_name" label="教学班" width="120" show-overflow-tooltip />
        <el-table-column prop="experiment_name" label="实验任务" min-width="210" show-overflow-tooltip />
        <el-table-column label="报告/学生" width="110" align="center">
          <template #default="{ row }">{{ row.upload_count }} / {{ row.student_count }}</template>
        </el-table-column>
        <el-table-column prop="ai_done_count" label="AI 完成" width="100" align="center" />
        <el-table-column prop="reviewed_count" label="已复核" width="90" align="center" />
        <el-table-column label="操作" width="260" align="center" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button link type="primary" @click="$router.push({ path: '/report-upload', query: { task_id: row.id, tab: 'upload' } })">上传</el-button>
              <el-button link type="primary" @click="$router.push({ path: '/report-parsing', query: { task_id: row.id, tab: 'batch' } })">解析</el-button>
              <el-button link type="primary" @click="$router.push({ path: '/ai-scoring', query: { task_id: row.id, tab: 'settings' } })">初评</el-button>
              <el-button link type="primary" @click="$router.push({ path: '/review', query: { task_id: row.id, tab: 'review' } })">复核</el-button>
              <el-button link type="primary" @click="$router.push({ path: '/export-analysis', query: { task_id: row.id, tab: 'overview' } })">成绩</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="page-card safety-card">
      <template #header>
        <strong>使用边界</strong>
      </template>
      <el-alert
        type="info"
        show-icon
        :closable="false"
        title="AI 初评结果只作为建议分，最终成绩必须由教师复核确认。系统默认在本地保存实名数据，发送给 AI 的文本应使用脱敏内容。"
      />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/api/client'
import { isTaskActive } from '@/utils/taskStatus'

const health = reactive({ ok: false, database: '', converter: null })
const taskBoardLoading = ref(false)
const taskBoardRows = ref([])

const metrics = computed(() => [
  { label: '运行方式', value: '本地单机', note: '数据保存在本机 SQLite' },
  { label: '主要对象', value: '教师', note: '不提供学生端' },
  { label: '报告格式', value: '.docx', note: '优先支持 Word 实验报告' },
  { label: '评阅机制', value: '人机协同', note: 'AI 建议分 + 教师确认分' },
  {
    label: '文档预览',
    value: health.converter?.available ? 'PDF 预览可用' : 'HTML 降级预览',
    note: health.converter?.available
      ? (health.converter.kind === 'bundled_libreoffice' ? '使用系统内置转换器' : '使用本机转换能力')
      : '建议打包内置 LibreOffice'
  }
])

const workflow = [
  { index: '01', title: '基础数据准备', desc: '创建课程、教学班，导入或维护学生名单。', path: '/courses' },
  { index: '02', title: '实验任务与评分标准', desc: '维护实验要求和分项评分标准，后续 AI 初评严格依据这些标准。', path: '/experiments' },
  { index: '03', title: '创建批改任务', desc: '将课程、教学班和实验任务组合成一次具体批改任务。', path: '/grading-tasks' },
  { index: '04', title: '上传、匹配与解析报告', desc: '批量上传 Word 报告，按文件名匹配学生，并生成脱敏文本。', path: '/report-upload' },
  { index: '05', title: 'AI 初评与教师复核', desc: '生成 AI 分项建议分，教师逐项确认最终成绩。', path: '/ai-scoring' },
  { index: '06', title: '成绩导出与班级分析', desc: '导出 Excel 成绩表，查看分数段、评分项和人机差异分析。', path: '/export-analysis' }
]

const modules = [
  { title: '数据结构重构', desc: '课程、教学班、基础名单和课程名单副本分离。', status: '已实现', type: 'success' },
  { title: '批改流程拆分', desc: '创建任务、上传报告、提交匹配等流程已拆成更清晰页面。', status: '已实现', type: 'success' },
  { title: '界面统一设计', desc: '统一侧边栏、卡片、表格、按钮和状态提示样式。', status: '本轮优化', type: 'primary' },
  { title: '便携运行能力', desc: '内置运行环境，便于发给其他教师解压试用。', status: '已验证', type: 'success' }
]

async function loadTaskBoard() {
  taskBoardLoading.value = true
  try {
    const result = await api.listGradingTasks({ include_ended: false })
    const activeTasks = (result.data || []).filter((task) => isTaskActive(task)).slice(0, 12)
    const rows = await Promise.all(activeTasks.map(async (task) => {
      try {
        const summaryResult = await api.getTaskSummary(task.id)
        return { ...task, ...(summaryResult.data || {}) }
      } catch {
        return {
          ...task,
          student_count: '-',
          upload_count: '-',
          ai_done_count: '-',
          reviewed_count: '-'
        }
      }
    }))
    taskBoardRows.value = rows
  } finally {
    taskBoardLoading.value = false
  }
}

onMounted(async () => {
  try {
    const result = await api.health()
    health.ok = Boolean(result.ok)
    health.database = result.database || result.data?.database || ''
    health.converter = result.docx_preview_converter || result.data?.docx_preview_converter || null
  } catch {
    health.ok = false
    health.converter = null
  }
  await loadTaskBoard()
})
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.dashboard-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 30px 34px;
  border: 1px solid #dbe3ee;
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(14, 165, 233, 0.14), rgba(6, 182, 212, 0.1)),
    #fff;
  box-shadow: 0 18px 42px rgba(8, 75, 116, 0.1);
}

.eyebrow {
  color: #0284c7;
  font-size: 14px;
  font-weight: 800;
}

.dashboard-hero h1 {
  margin: 8px 0 10px;
  color: #082f49;
  font-size: 42px;
  line-height: 1.05;
  letter-spacing: 0;
}

.dashboard-hero p {
  max-width: 840px;
  margin: 0;
  color: #475569;
  font-size: 16px;
  line-height: 1.8;
}

.hero-status {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
  padding: 14px 16px;
  border: 1px solid #bae6fd;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
}

.hero-status strong,
.hero-status span {
  display: block;
}

.hero-status span {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
}

.status-dot {
  width: 11px;
  height: 11px;
  border-radius: 999px;
  background: #f59e0b;
  box-shadow: 0 0 0 5px rgba(245, 158, 11, 0.16);
}

.status-dot.ok {
  background: #22c55e;
  box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.16);
}

.metric-row,
.content-row {
  row-gap: 18px;
}

.dashboard-metric {
  padding: 18px;
}

.header-tight {
  margin-bottom: 0;
}

.workflow-list,
.module-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.workflow-item,
.module-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fbfdff;
}

.workflow-index {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #dff5ff;
  color: #0284c7;
  font-weight: 900;
}

.workflow-content {
  flex: 1;
}

.workflow-title,
.module-title {
  color: #082f49;
  font-weight: 850;
}

.workflow-desc,
.module-desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
}

.module-item {
  justify-content: space-between;
}

.safety-card {
  margin-bottom: 8px;
}

@media (max-width: 1080px) {
  .dashboard-hero {
    flex-direction: column;
  }
}
</style>
