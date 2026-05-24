<template>
  <div class="stack">
    <el-tabs v-model="activeTab" class="function-tabs">
      <el-tab-pane label="选择课程" name="select">
    <el-card class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>实验任务管理</strong>
            <div class="muted">先选择课程，再维护该课程下的实验任务。评分标准会基于实验任务继续配置。</div>
          </div>
          <el-button type="primary" :disabled="!selectedCourseId" @click="openCreate">新增实验任务</el-button>
        </div>
      </template>

      <InlineActionNotice :notice="actionNotice" @clear="clearNotice" />

      <el-form label-position="top">
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
      </el-form>

      <el-alert
        v-if="selectedCourse"
        class="mt"
        type="info"
        :closable="false"
        show-icon
        :title="`当前课程：${selectedCourse.course_name} / ${selectedCourse.semester || '未填写学期'}；实验任务数：${experiments.length}`"
      />
      <el-empty v-else description="请先选择课程；如暂无课程，请先到课程管理页面创建。" />
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="实验任务列表" name="list">
    <el-empty v-if="!selectedCourseId" description="请先选择课程后维护实验任务。" />
    <el-card v-else class="page-card">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>实验任务列表</strong>
            <div class="muted">可在表格中查看实验任务摘要，并通过操作列编辑或删除。</div>
          </div>
        </div>
      </template>

      <el-table :data="experiments" border stripe empty-text="当前课程暂无实验任务">
        <el-table-column prop="experiment_name" label="实验名称" min-width="220" />
        <el-table-column prop="experiment_objectives" label="实验目标摘要" min-width="240" show-overflow-tooltip />
        <el-table-column prop="required_screenshots" label="必须截图摘要" min-width="240" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="复用历史实验" name="reuse">
        <el-empty v-if="!selectedCourseId" description="请先选择当前课程，再从历史课程中复制实验任务和评分标准。" />
        <el-card v-else class="page-card">
          <template #header>
            <div class="toolbar">
              <div>
                <strong>从历史实验复用</strong>
                <div class="muted">复制历史实验任务和评分标准到当前课程。复制后会生成独立记录，后续修改不会影响历史学期。</div>
              </div>
            </div>
          </template>

          <el-alert
            class="mt"
            type="info"
            :closable="false"
            show-icon
            :title="`目标课程：${selectedCourse?.course_name || ''} / ${selectedCourse?.semester || '未填写学期'}`"
          />

          <el-form label-position="top" class="reuse-form">
            <el-form-item label="第一步：选择来源课程和学期">
              <SearchTablePicker
                v-model="selectedSourceCourseId"
                :items="sourceCourseOptions"
                label-key="display_name"
                placeholder="先选择历史课程和学期"
                dialog-title="选择来源课程和学期"
                :columns="sourceCourseColumns"
                @change="onSourceCourseChange"
              />
              <div class="form-tip">建议优先选择同一门课历史学期的实验。系统会复制实验说明和全部评分标准，而不是共用原记录。</div>
            </el-form-item>

            <el-form-item label="第二步：选择该课程下的实验任务">
              <SearchTablePicker
                v-model="selectedSourceExperimentId"
                :items="sourceExperimentsForCourse"
                label-key="experiment_name"
                placeholder="请选择具体实验任务"
                dialog-title="选择历史实验任务"
                :columns="sourceExperimentColumns"
                :disabled="!selectedSourceCourseId"
                @change="prepareCloneName"
              />
              <div class="form-tip">先按课程和学期缩小范围，再选择具体实验，避免历史实验过多时列表混乱。</div>
            </el-form-item>

            <div v-if="selectedSourceExperiment" class="reuse-preview">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="来源课程">{{ selectedSourceExperiment.course_name || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="来源学期">{{ selectedSourceExperiment.semester || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="实验名称">{{ selectedSourceExperiment.experiment_name }}</el-descriptions-item>
                <el-descriptions-item label="评分标准">{{ selectedSourceExperiment.rubric_count || 0 }} 项 / {{ selectedSourceExperiment.rubric_total_score || 0 }} 分</el-descriptions-item>
                <el-descriptions-item label="必须截图" :span="2">{{ selectedSourceExperiment.required_screenshots || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="重点检查" :span="2">{{ selectedSourceExperiment.key_evaluation_points || '未填写' }}</el-descriptions-item>
              </el-descriptions>

              <el-form-item label="复制后的实验名称">
                <el-input v-model="cloneExperimentName" placeholder="可调整名称，避免和当前课程已有实验重名" />
              </el-form-item>

              <div class="reuse-actions">
                <el-button type="primary" :loading="cloneLoading" @click="cloneSelectedExperiment">复制实验任务和评分标准到当前课程</el-button>
              </div>
            </div>
            <el-empty v-else description="请选择一个历史实验后预览并复制。" />
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑实验任务' : '新增实验任务'" width="760px">
      <el-form label-position="top">
        <el-form-item label="实验名称">
          <el-input v-model="form.experiment_name" placeholder="例如：实验三 静态路由配置实验" />
        </el-form-item>
        <el-form-item label="实验目标">
          <el-input
            v-model="form.experiment_objectives"
            type="textarea"
            :rows="5"
            placeholder="例如：
- 理解静态路由的基本作用
- 掌握路由器接口 IP 配置方法
- 掌握静态路由命令配置方法
- 能够通过 ping 命令验证跨网段连通性
- 能够解释数据包跨网段转发过程"
          />
        </el-form-item>
        <el-form-item label="实验要求">
          <el-input
            v-model="form.experiment_requirements"
            type="textarea"
            :rows="4"
            placeholder="例如：学生需完成网络拓扑搭建、IP 地址规划、路由器接口配置、静态路由配置、连通性测试，并在实验报告中说明关键配置过程和实验结果。"
          />
        </el-form-item>
        <el-form-item label="必须包含的截图">
          <el-input
            v-model="form.required_screenshots"
            type="textarea"
            :rows="4"
            placeholder="例如：
- 网络拓扑截图
- 路由器接口 IP 配置截图
- 静态路由配置命令截图
- 路由表查看截图
- ping 连通性测试截图"
          />
        </el-form-item>
        <el-form-item label="重点检查内容">
          <el-input
            v-model="form.key_evaluation_points"
            type="textarea"
            :rows="4"
            placeholder="例如：
- IP 地址规划是否合理
- 静态路由配置是否完整
- ping 测试是否能证明跨网段连通
- 是否解释了数据包转发路径"
          />
        </el-form-item>
        <el-form-item label="常见错误">
          <el-input
            v-model="form.common_errors"
            type="textarea"
            :rows="4"
            placeholder="例如：
- 只展示 ping 成功，但没有解释为什么成功
- 路由表截图缺失
- 静态路由命令写了，但没有说明下一跳含义
- IP 地址与拓扑图不一致"
          />
        </el-form-item>
        <el-form-item label="特殊说明（可选）">
          <el-input
            v-model="form.special_notes"
            type="textarea"
            :rows="3"
            placeholder="例如：本次实验重点考查学生对跨网段通信过程的理解，不能只根据截图数量给高分。"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存实验任务</el-button>
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
const sourceExperiments = ref([])
const selectedCourseId = ref(null)
const selectedSourceCourseId = ref(null)
const selectedSourceExperimentId = ref(null)
const cloneExperimentName = ref('')
const cloneLoading = ref(false)
const activeTab = ref('select')
const dialogVisible = ref(false)
const editingId = ref(null)
const courseColumns = [{ prop: 'display_name', label: '课程与学期', minWidth: 260 }, { prop: 'course_type', label: '课程类型', width: 160 }]
const sourceCourseColumns = [{ prop: 'display_name', label: '来源课程与学期', minWidth: 300 }, { prop: 'course_type', label: '课程类型', width: 160 }]
const sourceExperimentColumns = [
  { prop: 'experiment_name', label: '实验任务', minWidth: 240 },
  { prop: 'rubric_count', label: '评分项', width: 90 },
  { prop: 'rubric_total_score', label: '总分', width: 90 }
]
const { actionNotice, showNotice, clearNotice } = useActionNotice()

const emptyForm = () => ({
  course_id: null,
  experiment_name: '',
  experiment_objectives: '',
  experiment_requirements: '',
  required_screenshots: '',
  key_evaluation_points: '',
  common_errors: '',
  special_notes: ''
})

const form = reactive(emptyForm())

const selectedCourse = computed(() => courses.value.find((item) => item.id === selectedCourseId.value))
const courseOptions = computed(() => courses.value.map(withCourseDisplayName))
const sourceCourseOptions = computed(() => courseOptions.value.filter((item) => item.id !== selectedCourseId.value))
const sourceExperimentsForCourse = computed(() => sourceExperiments.value.filter((item) => item.course_id === selectedSourceCourseId.value))
const selectedSourceExperiment = computed(() => sourceExperimentsForCourse.value.find((item) => item.id === selectedSourceExperimentId.value))

function withCourseDisplayName(course) {
  const semester = course.semester || '未填写学期'
  return { ...course, display_name: `${course.course_name || course.name || '未命名课程'} / ${semester}` }
}

async function loadCourses() {
  const result = await api.listCourses()
  courses.value = result.data || []
  if (!selectedCourseId.value && courses.value.length > 0) {
    selectedCourseId.value = courses.value[0].id
  }
  await Promise.all([loadExperiments(), loadSourceExperiments()])
}

async function loadExperiments() {
  if (!selectedCourseId.value) {
    experiments.value = []
    return
  }
  const result = await api.listExperiments(selectedCourseId.value)
  experiments.value = result.data || []
  if (selectedSourceExperiment.value?.course_id === selectedCourseId.value) {
    selectedSourceCourseId.value = null
    selectedSourceExperimentId.value = null
    cloneExperimentName.value = ''
  }
}

async function loadSourceExperiments() {
  const result = await api.listExperiments()
  sourceExperiments.value = result.data || []
}

function resetForm() {
  Object.assign(form, emptyForm(), { course_id: selectedCourseId.value })
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, emptyForm(), row, { course_id: row.course_id })
  dialogVisible.value = true
}

async function save() {
  if (!form.experiment_name.trim()) {
    showNotice('warning', '实验名称不能为空。')
    return
  }
  const payload = { ...form, course_id: selectedCourseId.value }
  if (editingId.value) {
    await api.updateExperiment(editingId.value, payload)
    showNotice('success', '实验任务已保存。')
  } else {
    await api.createExperiment(payload)
    showNotice('success', '实验任务已创建。')
  }
  dialogVisible.value = false
  await Promise.all([loadExperiments(), loadSourceExperiments()])
}

async function remove(row) {
  const deps = await api.getExperimentDependencies(row.id)
  const count = deps.data || {}
  const warning =
    count.rubric_items || count.grading_tasks
      ? `该实验任务下已有 ${count.rubric_items || 0} 个评分项、${count.grading_tasks || 0} 个批改任务引用。删除后可能影响后续流程。`
      : '确认删除该实验任务？'
  await ElMessageBox.confirm(warning, '删除确认', { type: 'warning' })
  await api.deleteExperiment(row.id)
  showNotice('success', '实验任务已删除。')
  await loadExperiments()
  await loadSourceExperiments()
}

function prepareCloneName() {
  if (!selectedSourceExperiment.value) {
    cloneExperimentName.value = ''
    return
  }
  cloneExperimentName.value = selectedSourceExperiment.value.experiment_name || ''
}

function onSourceCourseChange() {
  selectedSourceExperimentId.value = null
  cloneExperimentName.value = ''
}

async function cloneSelectedExperiment() {
  if (!selectedCourseId.value) {
    showNotice('warning', '请先选择目标课程。')
    return
  }
  if (!selectedSourceExperimentId.value) {
    showNotice('warning', '请先选择要复用的历史实验。')
    return
  }
  if (!cloneExperimentName.value.trim()) {
    showNotice('warning', '复制后的实验名称不能为空。')
    return
  }
  cloneLoading.value = true
  try {
    const result = await api.cloneExperiment({
      source_experiment_id: selectedSourceExperimentId.value,
      target_course_id: selectedCourseId.value,
      experiment_name: cloneExperimentName.value.trim()
    })
    showNotice('success', result.message || '历史实验任务和评分标准已复制。')
    selectedSourceCourseId.value = null
    selectedSourceExperimentId.value = null
    cloneExperimentName.value = ''
    await Promise.all([loadExperiments(), loadSourceExperiments()])
    activeTab.value = 'list'
  } finally {
    cloneLoading.value = false
  }
}

onMounted(loadCourses)
</script>

<style scoped>
.stack {
  display: grid;
  gap: 20px;
}

.mt {
  margin-top: 16px;
}

.function-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}

.reuse-form {
  margin-top: 16px;
}

.reuse-preview {
  display: grid;
  gap: 16px;
  margin-top: 18px;
}

.reuse-actions {
  display: flex;
  justify-content: flex-end;
}

.form-tip {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}
</style>
