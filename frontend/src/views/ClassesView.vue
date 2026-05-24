<template>
  <el-card class="page-card">
    <template #header>
      <div class="toolbar">
        <div>
          <strong>教学班管理</strong>
          <div class="muted">教学班独立建档，可按需关联到一门或多门课程。</div>
        </div>
        <el-button type="primary" @click="openCreate">新增教学班</el-button>
      </div>
    </template>

    <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

    <el-row :gutter="12" class="filter-row">
      <el-col :span="10">
        <SearchTablePicker
          v-model="courseFilter"
          clearable
          :items="courseOptions"
          label-key="display_name"
          placeholder="按课程筛选"
          dialog-title="选择课程"
          :columns="courseColumns"
          @change="loadClasses"
        />
      </el-col>
      <el-col :span="10">
        <el-input v-model="keyword" clearable placeholder="搜索班级名称、说明或已关联课程" />
      </el-col>
      <el-col :span="4">
        <div class="count-text">共 {{ filteredClasses.length }} 个教学班</div>
      </el-col>
    </el-row>

    <el-table :data="filteredClasses" border stripe empty-text="暂无教学班">
      <el-table-column prop="class_name" label="班级名称" min-width="160" />
      <el-table-column prop="description" label="班级说明" min-width="220" show-overflow-tooltip />
      <el-table-column prop="linked_course_names" label="已关联课程" min-width="220" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" @click="openLink(row)">关联课程</el-button>
          <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑教学班' : '新增教学班'" width="520px">
      <el-form label-position="top">
        <el-form-item label="班级名称">
          <el-input v-model="form.class_name" />
        </el-form-item>
        <el-form-item label="关联课程（可选）" v-if="!editingId">
          <SearchTablePicker
            v-model="form.course_id"
            clearable
            :items="courseOptions"
            label-key="display_name"
            placeholder="可暂不关联课程"
            dialog-title="选择关联课程"
            :columns="courseColumns"
          />
        </el-form-item>
        <el-form-item label="班级说明（可选）">
          <el-input v-model="form.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="linkDialogVisible" title="关联教学班到课程" width="520px">
      <el-alert type="info" :closable="false" title="这里每次只新增一个课程关联，不会覆盖已有课程关联。" />
      <el-form label-position="top" class="link-form">
        <el-form-item label="当前教学班">
          <el-input :model-value="linkClass?.class_name" disabled />
        </el-form-item>
        <el-form-item label="选择要关联的课程">
          <SearchTablePicker
            v-model="linkCourseId"
            :items="courseOptions"
            label-key="display_name"
            placeholder="请选择课程"
            dialog-title="选择要关联的课程"
            :columns="courseColumns"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="linkDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveLink">添加关联</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/api/client'
import InlineActionNotice from '@/components/InlineActionNotice.vue'
import SearchTablePicker from '@/components/SearchTablePicker.vue'
import { useActionNotice } from '@/composables/useActionNotice'

const courses = ref([])
const classes = ref([])
const courseFilter = ref(null)
const keyword = ref('')
const dialogVisible = ref(false)
const linkDialogVisible = ref(false)
const editingId = ref(null)
const linkClass = ref(null)
const linkCourseId = ref(null)
const form = reactive({ class_name: '', description: '', course_id: null })
const courseColumns = [{ prop: 'display_name', label: '课程与学期', minWidth: 260 }, { prop: 'course_type', label: '课程类型', width: 160 }]
const { actionNotice, showNotice, clearNotice } = useActionNotice()

const courseOptions = computed(() => courses.value.map((course) => ({
  ...course,
  display_name: `${course.course_name || course.name || '未命名课程'} / ${course.semester || '未填写学期'}`
})))

const filteredClasses = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return classes.value
  return classes.value.filter((item) => [
    item.class_name,
    item.description,
    item.linked_course_names
  ].some((value) => String(value || '').toLowerCase().includes(text)))
})

const loadCourses = async () => {
  courses.value = (await api.listCourses()).data || []
}

const loadClasses = async () => {
  classes.value = (await api.listClasses(courseFilter.value)).data || []
}

const openCreate = () => {
  editingId.value = null
  Object.assign(form, { class_name: '', description: '', course_id: null })
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  Object.assign(form, { class_name: row.class_name || row.name || '', description: row.description || '', course_id: null })
  dialogVisible.value = true
}

const save = async () => {
  if (!form.class_name.trim()) {
    showNotice('warning', '班级名称不能为空。')
    return
  }
  if (editingId.value) await api.updateClass(editingId.value, form)
  else await api.createClass(form)
  showNotice('success', '教学班已保存。')
  dialogVisible.value = false
  await loadClasses()
}

const openLink = (row) => {
  linkClass.value = row
  linkCourseId.value = null
  linkDialogVisible.value = true
}

const saveLink = async () => {
  if (!linkCourseId.value) {
    showNotice('warning', '请选择课程。')
    return
  }
  await api.linkClass({ class_id: linkClass.value.id, course_id: linkCourseId.value })
  showNotice('success', '课程关联已添加。')
  linkDialogVisible.value = false
  await loadClasses()
}

const remove = async (row) => {
  await ElMessageBox.confirm(`确认删除教学班“${row.class_name || row.name}”？`, '删除确认', { type: 'warning' })
  await api.deleteClass(row.id)
  showNotice('success', '教学班已删除。')
  await loadClasses()
}

onMounted(async () => {
  await loadCourses()
  await loadClasses()
})
</script>

<style scoped>
.filter-row,
.link-form {
  margin-bottom: 16px;
}

.count-text {
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  color: #52677a;
  font-size: 14px;
}
</style>
