<template>
  <el-card class="page-card">
    <template #header>
      <div class="toolbar">
        <div>
          <strong>课程列表</strong>
          <div class="muted">课程是实验任务、评分标准和批改任务的上层组织。</div>
        </div>
        <el-button type="primary" @click="openCreate">新增课程</el-button>
      </div>
    </template>

    <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

    <div class="list-tools">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索课程名称、学期或课程说明"
      />
      <el-segmented
        v-model="semesterScope"
        :options="[
          { label: '当前学期', value: 'current' },
          { label: '历史学期', value: 'history' },
          { label: '全部', value: 'all' }
        ]"
      />
      <span class="muted">当前视图 {{ visibleCourseCount }} 门课程</span>
    </div>

    <el-alert
      v-if="semesterScope === 'current'"
      class="mb"
      type="info"
      :closable="false"
      :title="`默认显示当前学期：${currentSemester}。历史学期课程可切换到“历史学期”查看。`"
    />

    <el-table v-if="semesterScope !== 'history'" :data="visibleCourses" border stripe empty-text="暂无课程">
      <el-table-column prop="course_name" label="课程名称" min-width="180" />
      <el-table-column prop="course_type" label="课程类型" width="160" />
      <el-table-column prop="semester" label="学期" width="160" />
      <el-table-column prop="description" label="课程说明" min-width="220" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-else-if="historicalCourseGroups.length === 0" description="暂无历史学期课程" />
    <el-collapse v-else class="archive-collapse">
      <el-collapse-item
        v-for="group in historicalCourseGroups"
        :key="group.semester"
        :title="`${group.semester}（${group.rows.length} 门课程）`"
      >
        <el-table :data="group.rows" border stripe empty-text="该学期暂无课程">
          <el-table-column prop="course_name" label="课程名称" min-width="180" />
          <el-table-column prop="course_type" label="课程类型" width="160" />
          <el-table-column prop="description" label="课程说明" min-width="220" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="170" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-collapse-item>
    </el-collapse>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑课程' : '新增课程'" width="560px">
      <el-form label-position="top">
        <el-form-item label="课程名称">
          <el-input v-model="form.course_name" />
        </el-form-item>
        <el-form-item label="课程类型">
          <el-select v-model="form.course_type" style="width: 100%">
            <el-option label="实验类课程" value="实验类课程" />
            <el-option label="理论类课程" value="理论类课程" />
            <el-option label="理论+实验课程" value="理论+实验课程" />
            <el-option label="项目实践类课程" value="项目实践类课程" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="学期">
          <div class="semester-builder">
            <span class="semester-label">学年起始年份</span>
            <el-input-number
              v-model="form.semester_start_year"
              :min="2000"
              :max="2100"
              :step="1"
              controls-position="right"
            />
            <span class="semester-year-preview">- {{ Number(form.semester_start_year || 0) + 1 }} 学年</span>
            <el-radio-group v-model="form.semester_term">
              <el-radio-button label="第一学期" />
              <el-radio-button label="第二学期" />
            </el-radio-group>
          </div>
          <div class="semester-result">将保存为：{{ semesterText || '请填写学年起始年份' }}</div>
          <div class="form-tip">学期由“学年起始年份 + 学期序号”自动生成，既能支持未来新学期，也能保证筛选和归档格式一致。</div>
        </el-form-item>
        <el-form-item label="课程说明（可选）">
          <el-input v-model="form.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import { useActionNotice } from '@/composables/useActionNotice'
import {
  currentAcademicYearStart,
  currentSemesterTerm,
  formatSemester,
  isStandardSemester,
  parseSemester
} from '@/utils/semester'

const courses = ref([])
const keyword = ref('')
const semesterScope = ref('current')
const dialogVisible = ref(false)
const editingId = ref(null)
const form = reactive({
  course_name: '',
  course_type: '理论+实验课程',
  semester: '',
  semester_start_year: currentAcademicYearStart(),
  semester_term: currentSemesterTerm(),
  description: ''
})
const { actionNotice, showNotice, clearNotice } = useActionNotice()

const filteredCourses = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return courses.value
  return courses.value.filter((course) => [
    course.course_name,
    course.course_type,
    course.semester,
    course.description
  ].some((item) => String(item || '').toLowerCase().includes(text)))
})

const semesterText = computed(() => formatSemester(form.semester_start_year, form.semester_term))
const currentSemester = computed(() => formatSemester(currentAcademicYearStart(), currentSemesterTerm()))
const visibleCourses = computed(() => {
  if (semesterScope.value === 'current') {
    return filteredCourses.value.filter((course) => String(course.semester || '') === currentSemester.value)
  }
  if (semesterScope.value === 'history') {
    return filteredCourses.value.filter((course) => String(course.semester || '') !== currentSemester.value)
  }
  return filteredCourses.value
})
const visibleCourseCount = computed(() => visibleCourses.value.length)
const historicalCourseGroups = computed(() => {
  const grouped = new Map()
  visibleCourses.value.forEach((course) => {
    const semester = course.semester || '未填写学期'
    if (!grouped.has(semester)) grouped.set(semester, [])
    grouped.get(semester).push(course)
  })
  return Array.from(grouped.entries())
    .sort((a, b) => String(b[0]).localeCompare(String(a[0])))
    .map(([semester, rows]) => ({ semester, rows }))
})

const load = async () => {
  const result = await api.listCourses()
  courses.value = result.data || []
}

const openCreate = () => {
  editingId.value = null
  const startYear = currentAcademicYearStart()
  const term = currentSemesterTerm()
  Object.assign(form, {
    course_name: '',
    course_type: '理论+实验课程',
    semester: formatSemester(startYear, term),
    semester_start_year: startYear,
    semester_term: term,
    description: ''
  })
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  const parsedSemester = parseSemester(row.semester)
  Object.assign(form, {
    course_name: row.course_name || row.name || '',
    course_type: row.course_type || '理论+实验课程',
    semester: parsedSemester.value,
    semester_start_year: parsedSemester.startYear,
    semester_term: parsedSemester.term,
    description: row.description || ''
  })
  dialogVisible.value = true
}

const save = async () => {
  if (!form.course_name.trim()) {
    showNotice('warning', '课程名称不能为空。')
    return
  }
  form.semester = semesterText.value
  if (!isStandardSemester(form.semester)) {
    showNotice('warning', '请选择规范学期，例如：2025-2026第一学期。')
    return
  }
  const payload = {
    course_name: form.course_name,
    course_type: form.course_type,
    semester: form.semester,
    description: form.description
  }
  if (editingId.value) await api.updateCourse(editingId.value, payload)
  else await api.createCourse(payload)
  showNotice('success', '课程已保存。')
  dialogVisible.value = false
  await load()
}

const remove = async (row) => {
  await ElMessageBox.confirm(`确认删除课程“${row.course_name || row.name}”？`, '删除确认', { type: 'warning' })
  await api.deleteCourse(row.id)
  showNotice('success', '课程已删除。')
  await load()
}

onMounted(load)
</script>

<style scoped>
.list-tools {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}

.list-tools .el-input {
  max-width: 420px;
}

.mb {
  margin-bottom: 14px;
}

.archive-collapse {
  margin-top: 10px;
}

.form-tip {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.semester-builder {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.semester-year-preview,
.semester-label,
.semester-result {
  color: var(--text-secondary);
  font-size: 14px;
}

.semester-label {
  font-weight: 600;
}

.semester-result {
  margin-top: 8px;
  color: #0369a1;
  font-weight: 700;
}
</style>
