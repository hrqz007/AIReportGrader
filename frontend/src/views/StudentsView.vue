<template>
  <div class="student-page stack">
    <el-card class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>学生名单</strong>
            <div class="muted">班级基础名单用于维护原始教学班学生；课程名单副本用于某一门课程内独立处理补选、重修和退课。</div>
          </div>
        </div>
      </template>

      <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

      <el-tabs v-model="activeTab">
        <el-tab-pane label="班级基础名单" name="class">
          <div class="section-panel">
            <div class="toolbar">
              <div>
                <strong>选择教学班</strong>
                <div class="muted">先选择教学班，再进行模板导入、手动维护或导出。</div>
              </div>
            </div>
            <el-row :gutter="14">
              <el-col :span="12">
                <SearchTablePicker
                  v-model="selectedClassId"
                  :items="classes"
                  label-key="class_name"
                  placeholder="选择教学班"
                  dialog-title="选择教学班"
                  :columns="classColumns"
                  @change="loadClassStudents"
                />
              </el-col>
              <el-col :span="12">
                <div class="action-line">
                  <el-button type="primary" :disabled="!selectedClassId" @click="openClassStudentCreate">新增学生</el-button>
                  <el-button :disabled="!selectedClassId" tag="a" :href="selectedClassId ? api.classStudentsExcelUrl(selectedClassId) : undefined" target="_blank">导出班级名单</el-button>
                </div>
              </el-col>
            </el-row>
          </div>

          <div class="section-panel import-panel">
            <div>
              <div class="section-title">Excel 导入</div>
              <div class="muted">支持 .xlsx，表头至少包含“学号、姓名、班级”。导入后只更新班级基础名单，不会自动改动课程名单副本；需要时请到“课程名单副本”中手动补齐。</div>
            </div>
            <el-row :gutter="16" class="mt">
              <el-col :span="8">
                <el-button tag="a" :href="api.studentTemplateUrl()" target="_blank">下载学生名单模板</el-button>
              </el-col>
              <el-col :span="8">
                <el-select v-model="importMode" style="width: 100%">
                  <el-option label="追加导入：只导入新学号" value="append" />
                  <el-option label="清空班级基础名单后重新导入" value="replace" />
                </el-select>
              </el-col>
              <el-col :span="8">
                <el-upload
                  :auto-upload="false"
                  :limit="1"
                  accept=".xlsx"
                  :show-file-list="true"
                  :on-change="onImportFileChange"
                  :on-remove="onImportFileRemove"
                >
                  <el-button :disabled="!selectedClassId">选择 Excel 文件</el-button>
                </el-upload>
              </el-col>
            </el-row>
            <div class="button-row">
              <el-button type="primary" :loading="importing" :disabled="!selectedClassId || !importFile" @click="importClassRoster">导入到当前教学班</el-button>
              <span v-if="importResult" class="inline-result">
                新增 {{ importResult.inserted || 0 }} 人，跳过已有 {{ importResult.skipped_existing || 0 }} 人。课程名单副本未自动改动。
              </span>
            </div>
          </div>

          <div class="section-panel">
            <div class="toolbar">
              <div>
                <strong>当前班级基础名单</strong>
                <div class="muted">可在操作列编辑或删除学生。删除班级基础名单学生不会自动删除已经形成的课程名单副本。</div>
              </div>
              <el-tag type="info">{{ classStudents.length }} 人</el-tag>
            </div>
            <el-table :data="classStudents" border stripe empty-text="请选择教学班或导入学生名单">
              <el-table-column prop="student_no" label="学号" min-width="140" />
              <el-table-column prop="student_name" label="姓名" min-width="120" />
              <el-table-column prop="class_name" label="班级" min-width="140" />
              <el-table-column prop="anonymous_id" label="匿名编号" width="120" />
              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" @click="openClassStudentEdit(row)">编辑</el-button>
                  <el-button size="small" type="danger" plain @click="removeClassStudent(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="课程名单副本" name="course">
          <div class="section-panel">
            <div class="toolbar">
              <div>
                <strong>选择课程名单副本</strong>
                <div class="muted">课程名单副本与班级基础名单分离，可单独添加重修、补选或退课学生。</div>
              </div>
            </div>
            <el-row :gutter="14">
              <el-col :span="8">
                <SearchTablePicker
                  v-model="selectedCourseId"
                  :items="courseOptions"
                  label-key="display_name"
                  placeholder="选择课程"
                  dialog-title="选择课程"
                  :columns="courseColumns"
                  @change="loadCourseRelated"
                />
              </el-col>
              <el-col :span="8">
                <SearchTablePicker
                  v-model="selectedCourseClassId"
                  clearable
                  :items="courseClasses"
                  label-key="class_name"
                  placeholder="选择教学班（可选）"
                  dialog-title="选择课程名单对应教学班"
                  :columns="classColumns"
                  @change="loadCourseStudents"
                />
              </el-col>
              <el-col :span="8">
                <div class="action-line">
                  <el-button :disabled="!selectedCourseId || !selectedCourseClassId" @click="syncCourseRoster">从班级名单补齐</el-button>
                  <el-button type="primary" :disabled="!selectedCourseId || !selectedCourseClassId" @click="openCourseStudentCreate">新增学生</el-button>
                </div>
              </el-col>
            </el-row>
          </div>

          <div class="section-panel">
            <div class="toolbar">
              <div>
                <strong>当前课程名单副本</strong>
                <div class="muted">这里的修改只影响当前课程名单副本，不会写回班级基础名单。</div>
              </div>
              <div class="action-line">
                <el-tag type="info">{{ courseStudents.length }} 人</el-tag>
                <el-button :disabled="!selectedCourseId" tag="a" :href="selectedCourseId ? api.courseStudentsExcelUrl(selectedCourseId, selectedCourseClassId) : undefined" target="_blank">导出课程名单</el-button>
              </div>
            </div>
            <el-table :data="courseStudents" border stripe empty-text="请选择课程">
              <el-table-column prop="student_no" label="学号" min-width="140" />
              <el-table-column prop="student_name" label="姓名" min-width="120" />
              <el-table-column prop="class_name" label="班级" min-width="140" />
              <el-table-column prop="anonymous_id" label="匿名编号" width="120" />
              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" @click="openCourseStudentEdit(row)">编辑</el-button>
                  <el-button size="small" type="danger" plain @click="removeCourseStudent(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="studentDialogVisible" :title="studentEditingId ? '编辑学生' : '新增学生'" width="520px">
      <el-form label-position="top">
        <el-form-item label="学号">
          <el-input v-model="studentForm.student_no" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="studentForm.student_name" />
        </el-form-item>
        <el-form-item label="班级">
          <el-input v-model="studentForm.class_name" placeholder="可填写行政班、教学班或重修来源班级" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="studentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveStudent">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import SearchTablePicker from '@/components/SearchTablePicker.vue'
import { useActionNotice } from '@/composables/useActionNotice'

const activeTab = ref('class')
const courses = ref([])
const classes = ref([])
const courseClasses = ref([])
const classStudents = ref([])
const courseStudents = ref([])
const selectedClassId = ref(null)
const selectedCourseId = ref(null)
const selectedCourseClassId = ref(null)
const courseColumns = [{ prop: 'display_name', label: '课程与学期', minWidth: 260 }]
const classColumns = [{ prop: 'class_name', label: '教学班', minWidth: 220 }, { prop: 'description', label: '说明', minWidth: 220 }]
const studentDialogVisible = ref(false)
const studentEditingId = ref(null)
const studentScope = ref('class')
const studentForm = reactive({ student_no: '', student_name: '', class_name: '' })
const importMode = ref('append')
const importFile = ref(null)
const importing = ref(false)
const importResult = ref(null)
const { actionNotice, showNotice, clearNotice } = useActionNotice()

const courseOptions = computed(() => courses.value.map((course) => ({
  ...course,
  display_name: `${course.course_name || course.name || '未命名课程'} / ${course.semester || '未填写学期'}`
})))

const loadBase = async () => {
  courses.value = (await api.listCourses()).data || []
  classes.value = (await api.listClasses()).data || []
  if (!selectedClassId.value && classes.value.length) {
    selectedClassId.value = classes.value[0].id
    await loadClassStudents()
  }
}

const loadClassStudents = async () => {
  importResult.value = null
  classStudents.value = selectedClassId.value ? (await api.listClassStudents(selectedClassId.value)).data || [] : []
}

const loadCourseRelated = async () => {
  selectedCourseClassId.value = null
  courseClasses.value = selectedCourseId.value ? (await api.listClasses(selectedCourseId.value)).data || [] : []
  await loadCourseStudents()
}

const loadCourseStudents = async () => {
  courseStudents.value = selectedCourseId.value ? (await api.listCourseStudents(selectedCourseId.value, selectedCourseClassId.value)).data || [] : []
}

const resetStudentForm = () => Object.assign(studentForm, { student_no: '', student_name: '', class_name: '' })

const openClassStudentCreate = () => {
  studentScope.value = 'class'
  studentEditingId.value = null
  resetStudentForm()
  studentForm.class_name = classes.value.find((item) => item.id === selectedClassId.value)?.class_name || ''
  studentDialogVisible.value = true
}

const openClassStudentEdit = (row) => {
  studentScope.value = 'class'
  studentEditingId.value = row.id
  Object.assign(studentForm, { student_no: row.student_no, student_name: row.student_name || row.name, class_name: row.class_name })
  studentDialogVisible.value = true
}

const openCourseStudentCreate = () => {
  studentScope.value = 'course'
  studentEditingId.value = null
  resetStudentForm()
  studentForm.class_name = courseClasses.value.find((item) => item.id === selectedCourseClassId.value)?.class_name || ''
  studentDialogVisible.value = true
}

const openCourseStudentEdit = (row) => {
  studentScope.value = 'course'
  studentEditingId.value = row.id
  Object.assign(studentForm, { student_no: row.student_no, student_name: row.student_name || row.name, class_name: row.class_name })
  studentDialogVisible.value = true
}

const saveStudent = async () => {
  if (!studentForm.student_no.trim() || !studentForm.student_name.trim()) {
    showNotice('warning', '学号和姓名不能为空。')
    return
  }
  if (studentScope.value === 'class') {
    if (studentEditingId.value) await api.updateClassStudent(studentEditingId.value, studentForm)
    else await api.createClassStudent(selectedClassId.value, studentForm)
    await loadClassStudents()
  } else {
    if (studentEditingId.value) await api.updateCourseStudent(studentEditingId.value, studentForm)
    else await api.createCourseStudent(selectedCourseId.value, selectedCourseClassId.value, studentForm)
    await loadCourseStudents()
  }
  showNotice('success', '学生名单已保存。')
  studentDialogVisible.value = false
}

const removeClassStudent = async (row) => {
  await ElMessageBox.confirm(`确认删除“${row.student_no} / ${row.student_name || row.name}”？`, '删除确认', { type: 'warning' })
  await api.deleteClassStudent(row.id)
  await loadClassStudents()
}

const removeCourseStudent = async (row) => {
  await ElMessageBox.confirm(`确认删除“${row.student_no} / ${row.student_name || row.name}”？`, '删除确认', { type: 'warning' })
  await api.deleteCourseStudent(row.id)
  await loadCourseStudents()
}

const syncCourseRoster = async () => {
  const result = await api.syncCourseRoster(selectedCourseId.value, selectedCourseClassId.value)
  showNotice('success', `补齐完成，新增 ${result.data?.inserted || 0} 人。`)
  await loadCourseStudents()
}

const onImportFileChange = (uploadFile) => {
  importFile.value = uploadFile.raw
}

const onImportFileRemove = () => {
  importFile.value = null
}

const importClassRoster = async () => {
  if (!selectedClassId.value || !importFile.value) return
  importing.value = true
  try {
    const result = await api.importClassStudents(selectedClassId.value, importFile.value, importMode.value)
    importResult.value = result.data || {}
    showNotice('success', result.message || '学生名单导入完成。')
    await loadClassStudents()
  } finally {
    importing.value = false
  }
}

onMounted(loadBase)
</script>

<style scoped>
.stack {
  display: grid;
  gap: 18px;
}

.section-panel {
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.74);
  margin-bottom: 16px;
}

.section-title {
  color: #08344f;
  font-size: 18px;
  font-weight: 850;
}

.action-line {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.import-panel {
  background: linear-gradient(135deg, rgba(240, 249, 255, 0.94), rgba(236, 254, 255, 0.74));
}

.button-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}

.inline-result {
  color: #0369a1;
  font-weight: 700;
}

.mt {
  margin-top: 14px;
}
</style>
