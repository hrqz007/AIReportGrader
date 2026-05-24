<template>
  <div class="ai-config-page">
    <el-card class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>AI 模型配置</strong>
            <div class="muted">配置教师自己的大模型 API。配置只保存在本机，AI 初评结果仅作为建议分。</div>
          </div>
          <div class="button-row">
            <el-button @click="loadConfigs">刷新</el-button>
            <el-button type="primary" @click="openCreate">新增配置</el-button>
          </div>
        </div>
      </template>

      <el-alert
        class="mb"
        type="info"
        :closable="false"
        title="默认配置会被 AI 初评优先使用。API Key 只显示脱敏结果，编辑时不填写新 Key 将保留原 Key。"
      />

      <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

      <el-table v-loading="loading" :data="configs" border stripe empty-text="当前暂无 AI 模型配置，请先新增配置">
        <el-table-column prop="provider_name" label="服务商" width="120" />
        <el-table-column label="接口类型" width="140">
          <template #default="{ row }">{{ displayProviderType(row.provider_type) }}</template>
        </el-table-column>
        <el-table-column prop="base_url" label="API Base URL" min-width="230" show-overflow-tooltip />
        <el-table-column prop="api_key" label="API Key" width="180" />
        <el-table-column prop="text_model" label="文本模型" width="150" show-overflow-tooltip />
        <el-table-column prop="vision_model" label="视觉模型" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.vision_model || '未配置' }}</template>
        </el-table-column>
        <el-table-column label="能力" width="150">
          <template #default="{ row }">
            <el-tag :type="row.supports_vision ? 'success' : 'info'" effect="plain">
              {{ row.supports_vision ? '支持视觉' : '纯文本' }}
            </el-tag>
            <el-tag class="ml" :type="row.supports_json ? 'primary' : 'info'" effect="plain">JSON</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success">默认</el-tag>
            <el-tag v-if="row.enabled" class="ml" type="primary">启用</el-tag>
            <el-tag v-else class="ml" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="390" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :loading="testingId === row.id" @click="testConfig(row)">测试连接</el-button>
            <el-button v-if="!row.is_default" size="small" @click="setDefault(row)">设为默认</el-button>
            <el-button size="small" @click="toggleEnabled(row)">{{ row.enabled ? '停用' : '启用' }}</el-button>
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="deleteConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-alert
        v-if="testMessage"
        class="mt"
        :type="testMessage.ok ? 'success' : 'error'"
        :closable="true"
        @close="testMessage = null"
      >
        <template #title>{{ testMessage.title }}</template>
        <div v-if="testMessage.detail" class="test-detail">{{ testMessage.detail }}</div>
      </el-alert>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 AI 配置' : '新增 AI 配置'" width="760px">
      <el-form :model="form" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="服务商名称">
              <el-input v-model="form.provider_name" placeholder="例如：Kimi、GLM、DeepSeek" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="接口类型">
              <el-input :model-value="displayProviderType(form.provider_type)" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="API Base URL">
              <el-input v-model="form.base_url" placeholder="例如：https://api.moonshot.cn/v1" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item :label="editingId ? 'API Key（可选，不填则保留原值）' : 'API Key'">
              <el-input v-model="form.api_key" type="password" show-password placeholder="只保存在本机数据库，不会在页面明文显示" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="文本评分模型">
              <el-input v-model="form.text_model" placeholder="例如：kimi-k2.6" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="视觉识别模型（可选）">
              <el-input v-model="form.vision_model" placeholder="未配置时不启用截图识别" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="班级分析模型（可选）">
              <el-input v-model="form.analysis_model" placeholder="默认使用文本模型" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="能力与状态">
          <el-checkbox v-model="form.supports_vision">支持视觉</el-checkbox>
          <el-checkbox v-model="form.supports_json">支持 JSON</el-checkbox>
          <el-checkbox v-model="form.enabled">启用</el-checkbox>
          <el-checkbox v-model="form.is_default">设为默认</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import { useActionNotice } from '@/composables/useActionNotice'

const configs = ref([])
const editingId = ref(null)
const testingId = ref(null)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const testMessage = ref(null)
const form = reactive(defaultForm())
const { actionNotice, showNotice, clearNotice } = useActionNotice()

function defaultForm() {
  return {
    provider_name: '',
    provider_type: 'openai_compatible',
    base_url: '',
    api_key: '',
    text_model: '',
    vision_model: '',
    analysis_model: '',
    supports_vision: false,
    supports_json: true,
    enabled: true,
    is_default: false
  }
}

function displayProviderType(value) {
  return value === 'openai_compatible' ? '通用兼容 API' : (value || '通用兼容 API')
}

function buildPayload(extra = {}) {
  return {
    provider_name: form.provider_name.trim(),
    provider_type: form.provider_type || 'openai_compatible',
    base_url: form.base_url.trim(),
    api_key: form.api_key || null,
    text_model: form.text_model.trim(),
    vision_model: form.vision_model?.trim() || '',
    analysis_model: form.analysis_model?.trim() || form.text_model.trim(),
    supports_vision: !!form.supports_vision,
    supports_json: !!form.supports_json,
    enabled: !!form.enabled,
    is_default: !!form.is_default,
    ...extra
  }
}

async function loadConfigs() {
  loading.value = true
  try {
    const result = await api.listAIProviders()
    configs.value = result.data || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    provider_name: row.provider_name || '',
    provider_type: row.provider_type || 'openai_compatible',
    base_url: row.base_url || '',
    api_key: '',
    text_model: row.text_model || '',
    vision_model: row.vision_model || '',
    analysis_model: row.analysis_model || row.text_model || '',
    supports_vision: !!row.supports_vision,
    supports_json: !!row.supports_json,
    enabled: !!row.enabled,
    is_default: !!row.is_default
  })
  dialogVisible.value = true
}

async function saveConfig() {
  if (!form.provider_name.trim() || !form.base_url.trim() || !form.text_model.trim()) {
    showNotice('warning', '服务商名称、API Base URL 和文本模型不能为空。')
    return
  }
  if (!editingId.value && !form.api_key.trim()) {
    showNotice('warning', '新增配置时 API Key 不能为空。')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await api.updateAIProvider(editingId.value, buildPayload())
      showNotice('success', '配置已保存。')
    } else {
      await api.createAIProvider(buildPayload({ api_key: form.api_key.trim() }))
      showNotice('success', '配置已创建。')
    }
    dialogVisible.value = false
    await loadConfigs()
  } finally {
    saving.value = false
  }
}

async function setDefault(row) {
  await api.updateAIProvider(row.id, { ...row, api_key: null, is_default: true })
  showNotice('success', '已设为默认配置。')
  await loadConfigs()
}

async function toggleEnabled(row) {
  await api.updateAIProvider(row.id, { ...row, api_key: null, enabled: !row.enabled })
  showNotice('success', row.enabled ? '配置已停用。' : '配置已启用。')
  await loadConfigs()
}

async function deleteConfig(row) {
  await ElMessageBox.confirm(`确认删除 AI 配置“${row.provider_name}”？删除后不可恢复。`, '删除确认', { type: 'warning' })
  await api.deleteAIProvider(row.id)
  showNotice('success', '配置已删除。')
  await loadConfigs()
}

async function testConfig(row) {
  testingId.value = row.id
  testMessage.value = null
  try {
    const result = await api.testAIProvider(row.id)
    testMessage.value = {
      ok: !!result.ok,
      title: result.message || (result.ok ? '连接成功。' : '连接失败。'),
      detail: result.error || result.content || ''
    }
  } finally {
    testingId.value = null
  }
}

onMounted(loadConfigs)
</script>

<style scoped>
.ai-config-page {
  display: grid;
  gap: 18px;
}

.ml {
  margin-left: 6px;
}

.test-detail {
  margin-top: 6px;
  word-break: break-word;
  color: #52677a;
}
</style>
