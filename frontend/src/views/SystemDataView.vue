<template>
  <div class="stack">
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      title="系统数据管理会影响数据库和上传文件。执行恢复或清空前，系统会自动生成安全备份；仍建议先手动下载一份备份包。"
    />

    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="数据概览" name="overview">
    <el-card class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>数据概览</strong>
            <div class="muted">查看当前数据库、上传文件、导出文件和主要业务数据量。</div>
          </div>
          <el-button :loading="loadingOverview" @click="loadOverview">刷新概览</el-button>
        </div>
      </template>

      <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

      <div class="summary-grid">
        <div v-for="item in overviewCards" :key="item.label" class="metric-card">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
        </div>
      </div>

      <el-divider />
      <el-descriptions :column="2" border>
        <el-descriptions-item label="数据库路径">{{ overview.db_path || '-' }}</el-descriptions-item>
        <el-descriptions-item label="数据库大小">{{ overview.db_size_text || '-' }}</el-descriptions-item>
        <el-descriptions-item label="上传文件大小">{{ overview.uploads_size_text || '-' }}</el-descriptions-item>
        <el-descriptions-item label="导出文件大小">{{ overview.exports_size_text || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备份文件大小">{{ overview.backup_size_text || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="备份导出" name="backup">
    <el-card class="page-card">
      <template #header>
        <div>
          <strong>数据备份导出</strong>
          <div class="muted">生成 zip 备份包，用于换电脑、演示数据分发或误操作恢复。</div>
        </div>
      </template>

      <div class="backup-grid">
        <div class="operation-card primary">
          <h3>完整本机备份</h3>
          <p>包含数据库和上传报告。适合本人换电脑、演示前留档或恢复使用。</p>
          <el-checkbox v-model="backupOptions.includeApiKeys">包含本地 AI API Key</el-checkbox>
          <el-checkbox v-model="backupOptions.includeExports">包含 exports 导出文件</el-checkbox>
          <el-button type="primary" class="mt" @click="downloadBackup">生成并下载备份包</el-button>
        </div>

        <div class="operation-card">
          <h3>演示或分享备份</h3>
          <p>不包含 API Key，适合发给他人演示或迁移样例数据，避免泄露个人服务密钥。</p>
          <el-button @click="downloadDemoBackup">下载不含 API Key 的备份包</el-button>
        </div>
      </div>
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="恢复导入" name="restore">
    <el-card class="page-card">
      <template #header>
        <div>
          <strong>数据恢复导入</strong>
          <div class="muted">从系统备份 zip 恢复数据库和上传文件。恢复前会自动备份当前数据。</div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="恢复会覆盖当前数据库和上传文件。请先确认备份包来源可靠，并建议在恢复前下载一份当前完整备份。"
      />

      <el-upload
        class="mt"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".zip"
        :on-change="onRestoreFileChange"
        :on-remove="onRestoreFileRemove"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽备份 zip 到此处，或点击选择文件</div>
        <template #tip>
          <div class="muted">仅支持由本系统生成的 zip 备份包。</div>
        </template>
      </el-upload>

      <div v-if="restoreValidation" class="mt">
        <el-alert :type="restoreValidation.ok ? 'success' : 'error'" :closable="false" :title="restoreValidation.message" />
        <el-descriptions v-if="restoreValidation.manifest" class="mt" :column="2" border>
          <el-descriptions-item label="系统名称">{{ restoreValidation.manifest.system_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备份类型">{{ restoreValidation.manifest.backup_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ restoreValidation.manifest.created_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="包含 API Key">{{ restoreValidation.manifest.include_api_keys ? '是' : '否' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="action-zone">
        <el-button
          type="warning"
          :loading="restoreLoading"
          :disabled="!restoreFile || !restoreValidation?.ok"
          @click="confirmRestore"
        >
          恢复该备份包
        </el-button>
        <span class="muted">点击后会再次弹出确认框，不需要手动输入确认文字。</span>
      </div>

      <InlineActionNotice :notice="restoreNotice" @clear="clearRestoreNotice" />
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="清空数据" name="clear">
    <el-card class="page-card danger-card danger-zone">
      <template #header>
        <div>
          <strong>清空数据</strong>
          <div class="muted">清空操作会自动生成安全备份。请只在演示重置或误操作恢复时使用。</div>
        </div>
      </template>

      <div class="danger-grid">
        <div class="operation-card danger-lite">
          <h3>只清空批改流程数据</h3>
          <p>清空批改任务、报告提交、AI 初评和教师复核数据，保留课程、教学班、学生名单、实验任务和评分标准。</p>
          <el-button type="danger" plain :loading="clearLoading" @click="confirmClearGrading">清空批改流程数据</el-button>
        </div>

        <div class="operation-card danger-strong">
          <h3>清空全部业务数据</h3>
          <p>清空课程、教学班、学生名单、实验任务、评分标准、批改任务和提交记录。可选择是否同时清空 AI 配置。</p>
          <el-checkbox v-model="includeAIConfigsOnClear">同时清空 AI 配置</el-checkbox>
          <el-button class="mt" type="danger" :loading="clearLoading" @click="confirmClearBusiness">清空全部业务数据</el-button>
        </div>
      </div>

      <InlineActionNotice :notice="dataClearNotice" @clear="clearDataClearNotice" />
    </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import { useActionNotice } from '@/composables/useActionNotice'

const overview = reactive({ counts: {} })
const loadingOverview = ref(false)
const backupOptions = reactive({ includeApiKeys: true, includeExports: false })
const restoreFile = ref(null)
const restoreValidation = ref(null)
const restoreLoading = ref(false)
const clearLoading = ref(false)
const includeAIConfigsOnClear = ref(false)
const activeTab = ref('overview')
const { actionNotice, showNotice, clearNotice } = useActionNotice()
const {
  actionNotice: restoreNotice,
  showNotice: showRestoreNotice,
  clearNotice: clearRestoreNotice
} = useActionNotice(12000)
const {
  actionNotice: dataClearNotice,
  showNotice: showClearNotice,
  clearNotice: clearDataClearNotice
} = useActionNotice(12000)

const overviewCards = computed(() => {
  const counts = overview.counts || {}
  return [
    { label: '课程', value: counts.courses ?? 0 },
    { label: '教学班', value: counts.classes ?? 0 },
    { label: '班级学生', value: counts.class_students ?? 0 },
    { label: '课程名单学生', value: counts.course_students ?? 0 },
    { label: '实验任务', value: counts.experiments ?? 0 },
    { label: '评分项', value: counts.rubric_items ?? 0 },
    { label: '批改任务', value: counts.grading_tasks ?? 0 },
    { label: '提交记录', value: counts.submissions ?? 0 },
    { label: 'AI 评分项', value: counts.ai_scores ?? 0 },
    { label: '教师复核', value: counts.teacher_scores ?? 0 },
    { label: 'AI 配置', value: counts.ai_configs ?? 0 }
  ]
})

async function loadOverview() {
  loadingOverview.value = true
  try {
    const result = await api.getSystemOverview()
    Object.assign(overview, result.data || {})
  } finally {
    loadingOverview.value = false
  }
}

function downloadBackup() {
  window.open(api.backupDownloadUrl(backupOptions.includeApiKeys, backupOptions.includeExports), '_blank')
  showNotice('info', '已打开完整备份下载，请在浏览器下载栏中确认文件是否开始下载。')
}

function downloadDemoBackup() {
  window.open(api.backupDownloadUrl(false, false), '_blank')
  showNotice('info', '已打开演示备份下载，请在浏览器下载栏中确认文件是否开始下载。')
}

async function onRestoreFileChange(uploadFile) {
  restoreFile.value = uploadFile.raw
  restoreValidation.value = null
  clearRestoreNotice()
  if (!restoreFile.value) return
  const result = await api.validateSystemBackup(restoreFile.value)
  restoreValidation.value = result.data || { ok: result.ok, message: result.message }
}

function onRestoreFileRemove() {
  restoreFile.value = null
  restoreValidation.value = null
  clearRestoreNotice()
}

async function confirmRestore() {
  if (!restoreFile.value || !restoreValidation.value?.ok) return
  try {
    await ElMessageBox.confirm(
      '恢复会覆盖当前数据库和上传文件。系统会先自动备份当前数据。确认继续恢复吗？',
      '确认恢复数据',
      { type: 'warning', confirmButtonText: '确认恢复', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  restoreLoading.value = true
  try {
    const result = await api.restoreSystemBackup(restoreFile.value, '确认恢复')
    showRestoreNotice(
      result.ok ? 'success' : 'error',
      result.message || (result.ok ? '恢复完成。' : '恢复失败。'),
      formatBackupDetail(result, '恢复前安全备份路径')
    )
    if (result.ok) {
      await loadOverview()
    }
  } finally {
    restoreLoading.value = false
  }
}

async function confirmClearGrading() {
  try {
    await ElMessageBox.confirm(
      '将清空批改任务、报告提交、AI 初评和教师复核数据，但保留基础数据。确认继续吗？',
      '确认清空批改流程数据',
      { type: 'warning', confirmButtonText: '确认清空', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await runClear(() => api.clearGradingData('清空批改数据'))
}

async function confirmClearBusiness() {
  try {
    await ElMessageBox.confirm(
      `将清空全部业务数据${includeAIConfigsOnClear.value ? '，并同时清空 AI 配置' : ''}。系统会先自动备份当前数据。确认继续吗？`,
      '确认清空全部业务数据',
      { type: 'error', confirmButtonText: '确认清空', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await runClear(() => api.clearBusinessData('清空全部数据', includeAIConfigsOnClear.value))
}

async function runClear(operation) {
  clearLoading.value = true
  clearDataClearNotice()
  try {
    const result = await operation()
    showClearNotice(
      result.ok ? 'success' : 'error',
      result.message || (result.ok ? '操作完成。' : '操作失败。'),
      formatBackupDetail(result, '清空前安全备份路径')
    )
    if (result.ok) {
      await loadOverview()
    }
  } finally {
    clearLoading.value = false
  }
}

function getSafetyBackupPath(result) {
  return result?.data?.safety_backup || result?.safety_backup || ''
}

function formatBackupDetail(result, label) {
  const backupPath = getSafetyBackupPath(result)
  return backupPath ? `${label}：${backupPath}` : ''
}

onMounted(loadOverview)
</script>

<style scoped>
.stack {
  display: grid;
  gap: 20px;
}

.function-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
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

.backup-grid,
.danger-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.operation-card {
  border: 1px solid #cfe3ee;
  border-radius: 14px;
  padding: 18px;
  background: linear-gradient(180deg, #fbfdff, #f3f9fd);
}

.operation-card.primary {
  border-color: #9bd4ee;
  background: linear-gradient(180deg, #f3fbff, #e8f6fc);
}

.operation-card.danger-lite {
  border-color: #fed7aa;
  background: #fffbeb;
}

.operation-card.danger-strong {
  border-color: #fecaca;
  background: #fff1f2;
}

.operation-card h3 {
  margin: 0 0 10px;
  color: #08344f;
}

.operation-card p {
  margin: 0 0 16px;
  color: #5f7890;
  line-height: 1.7;
}

.danger-card {
  border-color: #fca5a5;
  background: linear-gradient(180deg, #fffafa 0%, #fff7ed 100%);
  box-shadow: 0 14px 34px rgba(185, 28, 28, 0.08);
}

.danger-zone :deep(.el-card__header) {
  background: linear-gradient(180deg, #fff7ed 0%, #fee2e2 100%);
  border-bottom-color: #fecaca;
}

.action-zone {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.mt {
  margin-top: 16px;
}

@media (max-width: 1100px) {
  .backup-grid,
  .danger-grid {
    grid-template-columns: 1fr;
  }
}
</style>
