<template>
  <div class="stack">
    <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="创建批改任务" name="create">
        <el-card class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>创建批改任务</strong>
            <div class="muted">批改任务由课程、教学班、实验任务和评分标准共同确定，创建后到“报告上传”页面上传学生实验报告。</div>
          </div>
        </div>
      </template>

      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="选择课程">
              <SearchTablePicker
                v-model="form.course_id"
                :items="courseOptions"
                label-key="display_name"
                placeholder="请选择课程"
                dialog-title="选择课程"
                :columns="courseColumns"
                @change="onCourseChange"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="选择教学班">
              <SearchTablePicker
                v-model="form.class_id"
                :items="classes"
                label-key="class_name"
                placeholder="请选择教学班"
                dialog-title="选择教学班"
                :columns="classColumns"
                :disabled="classes.length === 0"
                @change="updateTaskName"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="选择实验任务">
              <SearchTablePicker
                v-model="form.experiment_id"
                :items="experimentOptions"
                label-key="display_name"
                placeholder="请选择实验任务"
                dialog-title="选择实验任务"
                :columns="experimentColumns"
                :disabled="experiments.length === 0"
                @change="updateTaskName"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-alert v-if="form.course_id && experiments.length === 0" class="mb" type="warning" :closable="false" title="当前课程下暂无实验任务，请先到“实验任务”页面创建。" />
        <el-alert v-if="rubricWarning" class="mb" type="warning" :closable="false" title="该实验任务尚未配置评分标准，后续 AI 初评前请先补充评分标准。" />
        <el-form-item label="批改任务名称">
          <el-input v-model="form.task_name" placeholder="例如：计算机网络-22软工班-实验三 静态路由配置实验" />
        </el-form-item>
        <el-form-item label="任务说明（可选）">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-button type="primary" :disabled="!canCreate" @click="createTask">创建批改任务</el-button>
      </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="已创建批改任务" name="list">
        <el-card class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>已创建批改任务</strong>
            <div class="muted">默认按上方所选课程筛选；任务生命周期分为进行中、已结束和已归档。</div>
          </div>
          <el-button @click="loadTasks">刷新列表</el-button>
        </div>
      </template>

      <el-row :gutter="16" class="mb">
        <el-col :span="8">
          <SearchTablePicker
            v-model="filters.course_id"
            clearable
            :items="courseOptions"
            label-key="display_name"
            placeholder="按课程筛选"
            dialog-title="选择课程"
            :columns="courseColumns"
            @change="onFilterCourseChange"
          />
        </el-col>
        <el-col :span="8">
          <SearchTablePicker
            v-model="filters.class_id"
            clearable
            :items="filterClasses"
            label-key="class_name"
            placeholder="按教学班筛选"
            dialog-title="选择教学班"
            :columns="classColumns"
            @change="loadTasks"
          />
        </el-col>
        <el-col :span="8">
          <SearchTablePicker
            v-model="filters.experiment_id"
            clearable
            :items="filterExperimentOptions"
            label-key="display_name"
            placeholder="按实验任务筛选"
            dialog-title="选择实验任务"
            :columns="experimentColumns"
            @change="loadTasks"
          />
        </el-col>
      </el-row>

      <div class="list-tools">
        <el-input v-model="taskKeyword" clearable placeholder="搜索批改任务、课程、教学班或实验任务" />
        <el-segmented
          v-model="taskStatusScope"
          :options="[
            { label: '进行中', value: 'active' },
            { label: '已结束', value: 'ended' },
            { label: '已归档', value: 'archived' },
            { label: '全部', value: 'all' }
          ]"
        />
        <span class="muted">共 {{ filteredTasks.length }} 个批改任务</span>
      </div>

      <el-table :data="filteredTasks" border stripe empty-text="暂无批改任务">
        <el-table-column prop="task_name" label="批改任务" min-width="260" show-overflow-tooltip />
        <el-table-column label="课程与学期" width="190" show-overflow-tooltip>
          <template #default="{ row }">
            {{ taskCourseDisplay(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="教学班" width="130" />
        <el-table-column prop="experiment_name" label="实验任务" min-width="220" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="taskStatusTagType(row.status)" effect="light">{{ normalizeTaskStatus(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === TASK_STATUS.active"
              size="small"
              type="warning"
              plain
              @click="finishTask(row)"
            >
              结束
            </el-button>
            <el-button
              v-if="row.status === TASK_STATUS.ended"
              size="small"
              type="primary"
              plain
              @click="restoreTask(row)"
            >
              恢复
            </el-button>
            <el-button
              v-if="row.status === TASK_STATUS.ended"
              size="small"
              type="info"
              plain
              @click="archiveTask(row)"
            >
              归档
            </el-button>
            <el-button
              v-if="row.status === TASK_STATUS.archived"
              size="small"
              type="primary"
              plain
              @click="restoreTask(row)"
            >
              恢复
            </el-button>
            <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-alert class="mt" type="info" :closable="false" title="后续流程页面默认只显示“进行中”的批改任务。结束或归档后的任务不会干扰报告上传、AI 初评、教师复核和成绩分析；如需继续处理，可在这里恢复为进行中。" />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import SearchTablePicker from '@/components/SearchTablePicker.vue'
import { useActionNotice } from '@/composables/useActionNotice'
import { normalizeTaskStatus, taskStatusTagType, TASK_STATUS } from '@/utils/taskStatus'

const courses = ref([])
const classes = ref([])
const experiments = ref([])
const filterClasses = ref([])
const filterExperiments = ref([])
const tasks = ref([])
const rubricWarning = ref(false)
const taskKeyword = ref('')
const activeTab = ref('create')
const taskStatusScope = ref('active')
const courseColumns = [{ prop: 'display_name', label: '课程与学期', minWidth: 260 }]
const classColumns = [{ prop: 'class_name', label: '教学班', minWidth: 220 }, { prop: 'description', label: '说明', minWidth: 220 }]
const experimentColumns = [
  { prop: 'display_name', label: '实验任务', minWidth: 300 },
  { prop: 'rubric_summary', label: '评分标准', width: 150 },
  { prop: 'created_at', label: '创建时间', width: 170 }
]
const { actionNotice, showNotice, clearNotice } = useActionNotice()

const form = reactive({
  course_id: null,
  class_id: null,
  experiment_id: null,
  task_name: '',
  description: ''
})

const filters = reactive({
  course_id: null,
  class_id: null,
  experiment_id: null
})

const canCreate = computed(() => form.course_id && form.class_id && form.experiment_id && form.task_name.trim())
const courseOptions = computed(() => courses.value.map((course) => ({
  ...course,
  display_name: `${course.course_name || course.name || '未命名课程'} / ${course.semester || '未填写学期'}`
})))
const experimentOptions = computed(() => decorateExperiments(experiments.value))
const filterExperimentOptions = computed(() => decorateExperiments(filterExperiments.value))
const filteredTasks = computed(() => {
  const text = taskKeyword.value.trim().toLowerCase()
  let rows = tasks.value
  if (taskStatusScope.value === 'active') {
    rows = rows.filter((task) => normalizeTaskStatus(task.status) === TASK_STATUS.active)
  } else if (taskStatusScope.value === 'ended') {
    rows = rows.filter((task) => normalizeTaskStatus(task.status) === TASK_STATUS.ended)
  } else if (taskStatusScope.value === 'archived') {
    rows = rows.filter((task) => normalizeTaskStatus(task.status) === TASK_STATUS.archived)
  }
  if (!text) return rows
  return rows.filter((task) => [
    task.task_name,
    task.course_name,
    task.class_name,
    task.experiment_name,
    task.status
  ].some((value) => String(value || '').toLowerCase().includes(text)))
})

function findById(items, id) {
  return items.find((item) => Number(item.id) === Number(id))
}

function decorateExperiments(rows) {
  return rows.map((item) => {
    const name = item.experiment_name || item.title || '未命名实验'
    const count = Number(item.rubric_count || 0)
    const total = Number(item.rubric_total_score || 0)
    const summary = count > 0 ? `${count} 项 / ${formatScore(total)} 分` : '未配置'
    return {
      ...item,
      display_name: `${name}（评分标准：${summary}）`,
      rubric_summary: summary
    }
  })
}

function formatScore(value) {
  const number = Number(value || 0)
  return Number.isInteger(number) ? String(number) : number.toFixed(1)
}

function taskCourseDisplay(row) {
  const course = courseOptions.value.find((item) => Number(item.id) === Number(row.course_id))
  if (course?.display_name) return course.display_name
  return `${row.course_name || '未命名课程'} / ${row.course_semester || '未填写学期'}`
}

function updateTaskName() {
  const course = findById(courses.value, form.course_id)
  const klass = findById(classes.value, form.class_id)
  const experiment = findById(experiments.value, form.experiment_id)
  if (course && klass && experiment && !form.task_name) {
    form.task_name = `${course.course_name}-${klass.class_name}-${experiment.experiment_name}`
  }
}

async function loadBase() {
  const result = await api.listCourses()
  courses.value = result.data || []
  if (courses.value.length > 0) {
    form.course_id = courses.value[0].id
    filters.course_id = form.course_id
  }
  await onCourseChange()
  await loadFilterOptions()
  await loadTasks()
}

async function onCourseChange() {
  form.class_id = null
  form.experiment_id = null
  form.task_name = ''
  rubricWarning.value = false
  if (!form.course_id) {
    classes.value = []
    experiments.value = []
    return
  }
  const [classResult, experimentResult] = await Promise.all([
    api.listClasses(form.course_id),
    api.listExperiments(form.course_id)
  ])
  classes.value = classResult.data || []
  experiments.value = experimentResult.data || []
  form.class_id = classes.value[0]?.id || null
  form.experiment_id = experiments.value[0]?.id || null
  filters.course_id = form.course_id
  await loadTasks()
  updateTaskName()
}

async function loadFilterOptions() {
  const [classResult, experimentResult] = await Promise.all([
    api.listClasses(filters.course_id || undefined),
    api.listExperiments(filters.course_id || undefined)
  ])
  filterClasses.value = classResult.data || []
  filterExperiments.value = experimentResult.data || []
}

async function onFilterCourseChange() {
  filters.class_id = null
  filters.experiment_id = null
  await loadFilterOptions()
  await loadTasks()
}

async function loadTasks() {
  const params = {
    course_id: filters.course_id || undefined,
    class_id: filters.class_id || undefined,
    experiment_id: filters.experiment_id || undefined,
    include_ended: true
  }
  const result = await api.listGradingTasks(params)
  tasks.value = (result.data || []).map((task) => ({ ...task, status: normalizeTaskStatus(task.status) }))
}

async function createTask() {
  const createdContext = {
    course_id: form.course_id,
    class_id: form.class_id,
    experiment_id: form.experiment_id
  }
  const result = await api.createGradingTask({ ...form })
  showNotice('success', result.message || '批改任务已创建。')
  rubricWarning.value = Number(result.data?.rubric_total || 0) <= 0
  form.description = ''
  form.task_name = ''
  taskStatusScope.value = 'active'
  filters.course_id = createdContext.course_id
  filters.class_id = createdContext.class_id
  filters.experiment_id = createdContext.experiment_id
  activeTab.value = 'list'
  await loadFilterOptions()
  updateTaskName()
  await loadTasks()
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除批改任务“${row.task_name}”？已有提交记录的任务不能删除。`, '删除确认', { type: 'warning' })
  await api.deleteGradingTask(row.id)
  showNotice('success', '批改任务已删除。')
  await loadTasks()
}

async function finishTask(row) {
  await ElMessageBox.confirm(
    `确认结束批改任务“${row.task_name}”？结束后，后续报告上传、AI 初评、教师复核和成绩分析页面将默认不再显示该任务。`,
    '结束批改任务',
    { type: 'warning', confirmButtonText: '确认结束', cancelButtonText: '取消' }
  )
  await api.updateGradingTask(row.id, {
    task_name: row.task_name,
    description: row.description || '',
    status: TASK_STATUS.ended
  })
  showNotice('success', '批改任务已结束。后续流程页面将默认隐藏该任务。')
  await loadTasks()
}

async function restoreTask(row) {
  await ElMessageBox.confirm(
    `确认将批改任务“${row.task_name}”恢复为进行中？恢复后可继续上传报告、AI 初评、教师复核和成绩分析。`,
    '恢复批改任务',
    { type: 'info', confirmButtonText: '确认恢复', cancelButtonText: '取消' }
  )
  await api.updateGradingTask(row.id, {
    task_name: row.task_name,
    description: row.description || '',
    status: TASK_STATUS.active
  })
  showNotice('success', '批改任务已恢复。')
  taskStatusScope.value = 'active'
  await loadTasks()
}

async function archiveTask(row) {
  await ElMessageBox.confirm(
    `确认归档批改任务“${row.task_name}”？归档后默认不进入任何后续批改流程。`,
    '归档批改任务',
    { type: 'warning', confirmButtonText: '确认归档', cancelButtonText: '取消' }
  )
  await api.updateGradingTask(row.id, {
    task_name: row.task_name,
    description: row.description || '',
    status: TASK_STATUS.archived
  })
  showNotice('success', '批改任务已归档。')
  taskStatusScope.value = 'archived'
  await loadTasks()
}

watch(() => form.experiment_id, () => {
  form.task_name = ''
  updateTaskName()
})

onMounted(loadBase)
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

.mt-small {
  margin-top: 8px;
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

.function-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}
</style>
