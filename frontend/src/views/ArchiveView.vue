<template>
  <div class="stack">
    <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

    <el-card class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>学期归档</strong>
            <div class="muted">
              按“学期 + 课程 + 教学班”统一归档批改任务。归档不会删除课程、班级、学生名单、报告或成绩，只会让对应批改任务默认退出后续批改流程。
            </div>
          </div>
          <el-button :loading="loading" @click="loadUnits">刷新</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="建议每学期结束并完成成绩导出后，再在此页面归档对应课程班级。误归档后可以恢复为进行中。"
      />

      <div class="archive-toolbar">
        <el-segmented
          v-model="scope"
          :options="[
            { label: '当前学期', value: 'current' },
            { label: '历史学期', value: 'history' },
            { label: '已归档', value: 'archived' },
            { label: '全部', value: 'all' }
          ]"
        />
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索学期、课程或教学班"
          class="archive-search"
        />
      </div>

      <el-row :gutter="14" class="summary-row">
        <el-col :span="6">
          <el-card class="metric-card" shadow="never">
            <div class="metric-label">当前显示组合</div>
            <div class="metric-value">{{ visibleRows.length }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="metric-card" shadow="never">
            <div class="metric-label">进行中任务</div>
            <div class="metric-value">{{ sumField('active_task_count') }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="metric-card" shadow="never">
            <div class="metric-label">已结束任务</div>
            <div class="metric-value">{{ sumField('ended_task_count') }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="metric-card" shadow="never">
            <div class="metric-label">已归档任务</div>
            <div class="metric-value">{{ sumField('archived_task_count') }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-table
        v-loading="loading"
        :data="visibleRows"
        border
        stripe
        empty-text="暂无可归档的课程班级组合"
      >
        <el-table-column prop="semester" label="学期" width="170" />
        <el-table-column prop="course_name" label="课程" min-width="180" show-overflow-tooltip />
        <el-table-column prop="class_name" label="教学班" width="150" />
        <el-table-column prop="course_student_count" label="课程名单人数" width="120" align="center" />
        <el-table-column prop="class_student_count" label="班级基础人数" width="120" align="center" />
        <el-table-column label="批改任务" min-width="240">
          <template #default="{ row }">
            <div class="task-counts">
              <el-tag type="success" effect="light">进行中 {{ row.active_task_count }}</el-tag>
              <el-tag type="warning" effect="light">已结束 {{ row.ended_task_count }}</el-tag>
              <el-tag type="info" effect="light">已归档 {{ row.archived_task_count }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="submission_count" label="提交记录" width="100" align="center" />
        <el-table-column prop="archive_state" label="归档状态" width="110">
          <template #default="{ row }">
            <el-tag :type="archiveStateTag(row.archive_state)" effect="light">{{ row.archive_state }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="latest_task_updated_at" label="最近任务更新" width="170" />
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="info"
              plain
              :disabled="row.active_task_count + row.ended_task_count <= 0"
              @click="archiveUnit(row)"
            >
              归档
            </el-button>
            <el-button
              size="small"
              type="primary"
              plain
              :disabled="row.archived_task_count <= 0"
              @click="restoreUnit(row)"
            >
              恢复
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-alert
        class="mt"
        type="warning"
        :closable="false"
        title="归档只影响批改任务的生命周期。已归档任务默认不会出现在报告上传、解析脱敏、AI 初评、教师复核和成绩分析页面；如果需要继续处理，请先在本页恢复。"
      />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import { useActionNotice } from '@/composables/useActionNotice'
import { currentAcademicYearStart, currentSemesterTerm, formatSemester } from '@/utils/semester'

const loading = ref(false)
const rows = ref([])
const keyword = ref('')
const scope = ref('current')
const { actionNotice, showNotice, clearNotice } = useActionNotice()

const currentSemester = computed(() => formatSemester(currentAcademicYearStart(), currentSemesterTerm()))
const visibleRows = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return rows.value.filter((row) => {
    if (scope.value === 'current' && row.semester !== currentSemester.value) return false
    if (scope.value === 'history' && row.semester === currentSemester.value) return false
    if (scope.value === 'archived' && row.archive_state !== '已归档' && row.archive_state !== '部分归档') return false
    if (!text) return true
    return [row.semester, row.course_name, row.class_name, row.archive_state]
      .some((value) => String(value || '').toLowerCase().includes(text))
  })
})

async function loadUnits() {
  loading.value = true
  try {
    const result = await api.listArchiveUnits()
    rows.value = result.data || []
  } finally {
    loading.value = false
  }
}

function sumField(field) {
  return visibleRows.value.reduce((sum, row) => sum + Number(row[field] || 0), 0)
}

function archiveStateTag(value) {
  if (value === '已归档') return 'info'
  if (value === '部分归档') return 'warning'
  if (value === '未归档') return 'success'
  return ''
}

async function archiveUnit(row) {
  await ElMessageBox.confirm(
    `确认归档“${row.semester} / ${row.course_name} / ${row.class_name}”下的进行中和已结束批改任务？该操作不会删除任何数据。`,
    '归档确认',
    { type: 'warning', confirmButtonText: '确认归档', cancelButtonText: '取消' }
  )
  const result = await api.archiveCourseClassUnit(row.course_id, row.class_id)
  showNotice('success', result.message || '归档完成。')
  await loadUnits()
}

async function restoreUnit(row) {
  await ElMessageBox.confirm(
    `确认恢复“${row.semester} / ${row.course_name} / ${row.class_name}”下的已归档批改任务为进行中？恢复后这些任务会重新出现在后续流程页面。`,
    '恢复确认',
    { type: 'info', confirmButtonText: '确认恢复', cancelButtonText: '取消' }
  )
  const result = await api.restoreCourseClassUnit(row.course_id, row.class_id)
  showNotice('success', result.message || '恢复完成。')
  await loadUnits()
}

onMounted(loadUnits)
</script>

<style scoped>
.stack {
  display: grid;
  gap: 20px;
}

.archive-toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 18px 0 16px;
}

.archive-search {
  max-width: 420px;
}

.summary-row {
  margin-bottom: 16px;
}

.task-counts {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.mt {
  margin-top: 16px;
}
</style>
