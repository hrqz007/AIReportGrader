<template>
  <el-card class="page-card">
    <template #header>
      <div class="toolbar">
        <div>
          <strong>{{ title }}</strong>
          <div class="muted">{{ description }}</div>
        </div>
        <el-button :loading="loadingTasks" @click="reload">刷新</el-button>
      </div>
    </template>

    <el-row :gutter="16" class="mb">
      <el-col :span="6">
        <el-select v-model="semesterFilter" clearable placeholder="按学期筛选" style="width: 100%" @change="onSemesterChange">
          <el-option v-for="semester in semesterOptions" :key="semester" :label="semester" :value="semester" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <SearchTablePicker
          v-model="filters.course_id"
          clearable
          :items="filteredCourses"
          label-key="display_name"
          placeholder="按课程筛选"
          dialog-title="选择课程"
          :columns="courseColumns"
          @change="onCourseFilterChange"
        />
      </el-col>
      <el-col :span="6">
        <SearchTablePicker
          v-model="filters.class_id"
          clearable
          :items="classes"
          label-key="class_name"
          placeholder="按教学班筛选"
          dialog-title="选择教学班"
          :columns="classColumns"
          @change="loadTasks"
        />
      </el-col>
      <el-col :span="6">
        <SearchTablePicker
          v-model="filters.experiment_id"
          clearable
          :items="experiments"
          label-key="experiment_name"
          placeholder="按实验任务筛选"
          dialog-title="选择实验任务"
          :columns="experimentColumns"
          @change="loadTasks"
        />
      </el-col>
    </el-row>

    <div class="list-tools">
      <el-input v-model="taskKeyword" clearable placeholder="搜索批改任务、课程、教学班或实验任务" />
      <span class="muted">共 {{ filteredTasks.length }} 个批改任务</span>
      <el-tag v-if="hideEnded" type="success" effect="light">仅显示进行中任务</el-tag>
    </div>

    <el-table
      v-loading="loadingTasks"
      :data="filteredTasks"
      border
      stripe
      highlight-current-row
      :empty-text="emptyText"
      @current-change="selectTask"
      @row-click="selectTask"
    >
      <el-table-column prop="task_name" label="批改任务" min-width="260" show-overflow-tooltip />
      <el-table-column label="课程与学期" width="190" show-overflow-tooltip>
        <template #default="{ row }">
          {{ taskCourseDisplay(row) }}
        </template>
      </el-table-column>
      <el-table-column prop="class_name" label="教学班" width="130" show-overflow-tooltip />
      <el-table-column prop="experiment_name" label="实验任务" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="taskStatusTagType(row.status)" effect="light">{{ normalizeTaskStatus(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170" />
    </el-table>
  </el-card>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '@/api/client'
import SearchTablePicker from '@/components/SearchTablePicker.vue'
import { mergeSemesterOptions } from '@/utils/semester'
import { isTaskActive, normalizeTaskStatus, taskStatusTagType, TASK_STATUS } from '@/utils/taskStatus'

const props = defineProps({
  title: { type: String, default: '选择批改任务' },
  description: { type: String, default: '先按学期、课程、教学班和实验任务缩小范围，再选择批改任务。' },
  emptyText: { type: String, default: '暂无批改任务' },
  hideEnded: { type: Boolean, default: true },
  autoSelectFirst: { type: Boolean, default: false },
  initialTaskId: { type: [Number, String], default: null }
})

const emit = defineEmits(['change'])

const courses = ref([])
const classes = ref([])
const experiments = ref([])
const tasks = ref([])
const loadingTasks = ref(false)
const taskKeyword = ref('')
const semesterFilter = ref('')
const selectedTaskId = ref(null)
const preferredTaskId = ref(null)

const filters = reactive({
  course_id: null,
  class_id: null,
  experiment_id: null
})

const courseColumns = [{ prop: 'display_name', label: '课程与学期', minWidth: 260 }]
const classColumns = [{ prop: 'class_name', label: '教学班', minWidth: 220 }, { prop: 'description', label: '说明', minWidth: 220 }]
const experimentColumns = [{ prop: 'experiment_name', label: '实验任务', minWidth: 260 }, { prop: 'created_at', label: '创建时间', width: 170 }]

const semesterOptions = computed(() => {
  return mergeSemesterOptions(courses.value.map((course) => course.semester), [])
})

const filteredCourses = computed(() => {
  const rows = courses.value.map((course) => ({
    ...course,
    display_name: `${course.course_name || course.name || '未命名课程'} / ${course.semester || '未填写学期'}`
  }))
  if (!semesterFilter.value) return rows
  return rows.filter((course) => String(course.semester || '') === semesterFilter.value)
})

const courseOptions = computed(() => courses.value.map((course) => ({
  ...course,
  display_name: `${course.course_name || course.name || '未命名课程'} / ${course.semester || '未填写学期'}`
})))

const visibleTasks = computed(() => {
  const rows = props.hideEnded ? tasks.value.filter((task) => isTaskActive(task)) : tasks.value
  return rows
})

const filteredTasks = computed(() => {
  const semesterRows = semesterFilter.value
    ? visibleTasks.value.filter((task) => String(task.course_semester || '') === semesterFilter.value)
    : visibleTasks.value
  const text = taskKeyword.value.trim().toLowerCase()
  if (!text) return semesterRows
  return semesterRows.filter((task) => [
    task.task_name,
    task.course_name,
    task.course_semester,
    task.class_name,
    task.experiment_name,
    task.status
  ].some((value) => String(value || '').toLowerCase().includes(text)))
})

async function reload() {
  await loadBase()
}

async function loadBase() {
  const result = await api.listCourses()
  courses.value = result.data || []

  const preferredTask = await loadPreferredTask()
  if (preferredTask) {
    const course = courses.value.find((item) => Number(item.id) === Number(preferredTask.course_id))
    semesterFilter.value = String(course?.semester || semesterFilter.value || '')
    filters.course_id = preferredTask.course_id || null
    filters.class_id = null
    filters.experiment_id = null
    const [classResult, experimentResult] = await Promise.all([
      api.listClasses(filters.course_id || undefined),
      api.listExperiments(filters.course_id || undefined)
    ])
    classes.value = classResult.data || []
    experiments.value = experimentResult.data || []
    filters.class_id = preferredTask.class_id || null
    filters.experiment_id = preferredTask.experiment_id || null
    preferredTaskId.value = preferredTask.id
    selectedTaskId.value = null
    await loadTasks()
    return
  }

  if (!semesterFilter.value && semesterOptions.value.length > 0) {
    semesterFilter.value = semesterOptions.value[0]
  }
  await onCourseFilterChange()
}

async function loadPreferredTask() {
  const taskId = Number(props.initialTaskId || 0)
  if (!taskId) return null
  try {
    const result = await api.getGradingTask(taskId)
    const task = result.data
    if (!task || (props.hideEnded && !isTaskActive(task))) return null
    return task
  } catch {
    return null
  }
}

async function onSemesterChange() {
  if (filters.course_id && !filteredCourses.value.some((course) => course.id === filters.course_id)) {
    filters.course_id = null
  }
  await onCourseFilterChange()
}

async function onCourseFilterChange() {
  filters.class_id = null
  filters.experiment_id = null
  emitSelection(null)
  const [classResult, experimentResult] = await Promise.all([
    api.listClasses(filters.course_id || undefined),
    api.listExperiments(filters.course_id || undefined)
  ])
  classes.value = classResult.data || []
  experiments.value = experimentResult.data || []
  await loadTasks()
}

async function loadTasks() {
  loadingTasks.value = true
  try {
    const result = await api.listGradingTasks({
      course_id: filters.course_id || undefined,
      class_id: filters.class_id || undefined,
      experiment_id: filters.experiment_id || undefined,
      include_ended: !props.hideEnded,
      status: props.hideEnded ? TASK_STATUS.active : undefined
    })
    tasks.value = result.data || []
    if (selectedTaskId.value && !visibleTasks.value.some((task) => task.id === selectedTaskId.value)) {
      emitSelection(null)
    }
    const preferredTask = preferredTaskId.value
      ? filteredTasks.value.find((task) => Number(task.id) === Number(preferredTaskId.value))
      : null
    if (!selectedTaskId.value && preferredTask) {
      preferredTaskId.value = null
      selectTask(preferredTask)
    } else if (!selectedTaskId.value && props.autoSelectFirst && filteredTasks.value.length > 0) {
      selectTask(filteredTasks.value[0])
    } else if (!selectedTaskId.value) {
      emitSelection(null)
    }
  } finally {
    loadingTasks.value = false
  }
}

function selectTask(row) {
  if (!row || (props.hideEnded && !isTaskActive(row))) return
  if (selectedTaskId.value === row.id) return
  emitSelection(row)
}

function taskCourseDisplay(row) {
  const course = courseOptions.value.find((item) => Number(item.id) === Number(row.course_id))
  return course?.display_name || row.course_name || '未命名课程'
}

function emitSelection(row) {
  selectedTaskId.value = row?.id || null
  emit('change', row || null)
}

onMounted(loadBase)

watch(
  () => props.initialTaskId,
  async (value, oldValue) => {
    if (value && String(value) !== String(oldValue || '')) {
      await loadBase()
    }
  }
)
</script>

<style scoped>
.mb {
  margin-bottom: 16px;
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
</style>
