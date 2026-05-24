<template>
  <div class="stack">
    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="选择实验任务" name="select">
    <el-card class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>评分标准管理</strong>
            <div class="muted">先选择课程和实验任务，再为该实验配置分项评分标准。后续 AI 初评和教师复核都会以这些分项为依据。</div>
          </div>
          <el-button type="primary" :disabled="!selectedExperimentId" @click="openCreate">新增评分项</el-button>
        </div>
      </template>

      <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="选择课程">
            <SearchTablePicker
              v-model="selectedCourseId"
              :items="courseOptions"
              label-key="display_name"
              placeholder="请选择课程"
              dialog-title="选择课程"
              :columns="courseColumns"
              @change="loadExperiments"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="选择实验任务">
            <SearchTablePicker
              v-model="selectedExperimentId"
              :items="experiments"
              label-key="experiment_name"
              placeholder="请选择实验任务"
              dialog-title="选择实验任务"
              :columns="experimentColumns"
              :disabled="experiments.length === 0"
              @change="loadRubrics"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-alert
        v-if="selectedCourse"
        class="mb"
        type="info"
        :closable="false"
        show-icon
        :title="`当前课程：${selectedCourse.course_name} / ${selectedCourse.semester || '未填写学期'}${selectedExperiment ? `；当前实验：${selectedExperiment.experiment_name}` : ''}`"
      />
      <el-empty v-if="selectedCourseId && experiments.length === 0" description="当前课程暂无实验任务，请先到实验任务页面创建。" />
      <el-alert v-else-if="!selectedCourseId" type="info" :closable="false" show-icon title="请先选择课程。" />
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="评分项列表" name="list">
    <el-empty v-if="!selectedExperimentId" description="请先选择实验任务后维护评分项。" />
    <el-card v-else class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>评分项列表</strong>
            <div class="muted">总分建议设置为 100 分；如实验按 50 分或其他满分制，也可以按实际教学要求配置。</div>
          </div>
          <div class="actions">
            <el-button plain @click="createTemplate">生成实验报告通用评分标准</el-button>
          </div>
        </div>
      </template>

      <el-alert
        class="mb"
        :type="Number(totalScore) === 100 ? 'success' : 'warning'"
        :closable="false"
        show-icon
        :title="Number(totalScore) === 100 ? '当前评分标准总分为 100 分。' : `当前评分标准总分为 ${formatScore(totalScore)} 分，请确认是否符合本次实验评分要求。`"
      />

      <el-table :data="rubrics" border stripe empty-text="当前实验任务暂无评分项，可新增或生成通用模板。">
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="item_name" label="评分项名称" min-width="180" />
        <el-table-column prop="max_score" label="满分" width="90">
          <template #default="{ row }">{{ formatScore(row.max_score) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="评分说明摘要" min-width="260" show-overflow-tooltip />
        <el-table-column label="是否重点复核" width="130">
          <template #default="{ row }">
            <el-tag :type="row.requires_review ? 'warning' : 'info'" effect="plain">
              {{ row.requires_review ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑评分项' : '新增评分项'" width="680px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="16">
            <el-form-item label="评分项名称">
              <el-input v-model="form.item_name" placeholder="例如：实验报告结构完整性" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="满分">
              <el-input-number v-model="form.max_score" :min="0.5" :step="0.5" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="排序">
              <el-input-number v-model="form.sort_order" :min="0" :step="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否需要教师重点复核">
              <el-switch v-model="form.requires_review" active-text="需要" inactive-text="常规" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="评分说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="例如：检查实验报告是否包含实验目的、实验环境、实验步骤、实验结果、结果分析和实验总结等基本组成部分。"
          />
        </el-form-item>
        <el-form-item label="扣分规则">
          <el-input
            v-model="form.deduction_rules"
            type="textarea"
            :rows="4"
            placeholder="例如：
- 缺少实验目的扣 1-2 分
- 缺少结果分析扣 2-4 分
- 报告结构混乱扣 1-3 分"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存评分项</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import SearchTablePicker from '@/components/SearchTablePicker.vue'
import { useActionNotice } from '@/composables/useActionNotice'

const courses = ref([])
const experiments = ref([])
const rubrics = ref([])
const selectedCourseId = ref(null)
const selectedExperimentId = ref(null)
const totalScore = ref(0)
const activeTab = ref('select')
const dialogVisible = ref(false)
const editingId = ref(null)
const courseColumns = [{ prop: 'display_name', label: '课程与学期', minWidth: 260 }]
const experimentColumns = [{ prop: 'experiment_name', label: '实验任务', minWidth: 260 }, { prop: 'created_at', label: '创建时间', width: 170 }]
const { actionNotice, showNotice, clearNotice } = useActionNotice()

const emptyForm = () => ({
  experiment_id: null,
  item_name: '',
  max_score: 10,
  description: '',
  deduction_rules: '',
  requires_review: false,
  sort_order: 1
})

const form = reactive(emptyForm())

const selectedCourse = computed(() => courses.value.find((item) => item.id === selectedCourseId.value))
const selectedExperiment = computed(() => experiments.value.find((item) => item.id === selectedExperimentId.value))
const courseOptions = computed(() => courses.value.map((course) => ({
  ...course,
  display_name: `${course.course_name || course.name || '未命名课程'} / ${course.semester || '未填写学期'}`
})))

function formatScore(value) {
  const num = Number(value || 0)
  return Number.isInteger(num) ? String(num) : num.toFixed(1)
}

async function loadCourses() {
  const result = await api.listCourses()
  courses.value = result.data || []
  if (!selectedCourseId.value && courses.value.length > 0) {
    selectedCourseId.value = courses.value[0].id
  }
  await loadExperiments()
}

async function loadExperiments() {
  selectedExperimentId.value = null
  rubrics.value = []
  totalScore.value = 0
  if (!selectedCourseId.value) {
    experiments.value = []
    return
  }
  const result = await api.listExperiments(selectedCourseId.value)
  experiments.value = result.data || []
  if (experiments.value.length > 0) {
    selectedExperimentId.value = experiments.value[0].id
    await loadRubrics()
  }
}

async function loadRubrics() {
  if (!selectedExperimentId.value) {
    rubrics.value = []
    totalScore.value = 0
    return
  }
  const result = await api.listRubrics(selectedExperimentId.value)
  rubrics.value = result.data?.items || []
  totalScore.value = result.data?.total_score || 0
}

function resetForm() {
  Object.assign(form, emptyForm(), {
    experiment_id: selectedExperimentId.value,
    sort_order: rubrics.value.length + 1
  })
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, emptyForm(), row, {
    requires_review: Boolean(row.requires_review)
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.item_name.trim()) {
    showNotice('warning', '评分项名称不能为空。')
    return
  }
  if (Number(form.max_score) <= 0) {
    showNotice('warning', '满分必须大于 0。')
    return
  }
  const payload = { ...form, experiment_id: selectedExperimentId.value }
  if (editingId.value) {
    await api.updateRubric(editingId.value, payload)
    showNotice('success', '评分项已保存。')
  } else {
    await api.createRubric(payload)
    showNotice('success', '评分项已创建。')
  }
  dialogVisible.value = false
  await loadRubrics()
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除评分项“${row.item_name}”？`, '删除确认', { type: 'warning' })
  await api.deleteRubric(row.id)
  showNotice('success', '评分项已删除。')
  await loadRubrics()
}

async function createTemplate() {
  await ElMessageBox.confirm('仅当当前实验任务没有评分项时可以生成通用模板。确认继续？', '生成模板', {
    type: 'info'
  })
  const result = await api.createCommonRubricTemplate(selectedExperimentId.value)
  showNotice('success', result.message || '通用评分标准已生成。')
  await loadRubrics()
}

onMounted(loadCourses)
</script>

<style scoped>
.stack {
  display: grid;
  gap: 20px;
}

.actions {
  display: flex;
  gap: 8px;
}

.function-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}

.mb {
  margin-bottom: 16px;
}
</style>
