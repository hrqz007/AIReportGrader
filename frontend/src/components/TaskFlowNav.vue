<template>
  <el-card v-if="taskId" class="task-flow-nav" shadow="never">
    <div class="flow-layout">
      <div class="flow-context">
        <span>当前批改任务</span>
        <strong>{{ taskName || '已选择' }}</strong>
      </div>
      <el-button-group class="flow-actions">
        <el-button :type="current === 'upload' ? 'primary' : 'default'" @click="go('/report-upload')">报告上传</el-button>
        <el-button :type="current === 'parsing' ? 'primary' : 'default'" @click="go('/report-parsing')">解析与脱敏</el-button>
        <el-button :type="current === 'ai' ? 'primary' : 'default'" @click="go('/ai-scoring')">AI 初评</el-button>
        <el-button :type="current === 'review' ? 'primary' : 'default'" @click="go('/review')">教师复核</el-button>
        <el-button :type="current === 'export' ? 'primary' : 'default'" @click="go('/export-analysis')">成绩分析</el-button>
      </el-button-group>
    </div>
  </el-card>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  taskId: { type: [Number, String], default: null },
  taskName: { type: String, default: '' },
  current: { type: String, default: '' }
})

const router = useRouter()

const targetTabs = {
  '/report-upload': 'upload',
  '/report-parsing': 'batch',
  '/ai-scoring': 'settings',
  '/review': 'review',
  '/export-analysis': 'overview'
}

function go(path) {
  if (!props.taskId) return
  router.push({ path, query: { task_id: props.taskId, tab: targetTabs[path] || 'select' } })
}
</script>

<style scoped>
.task-flow-nav {
  border-color: #cfe8f7;
  background: linear-gradient(135deg, #f2fbff, #ffffff);
}

.flow-layout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.flow-context {
  min-width: 0;
}

.flow-context span {
  display: block;
  margin-bottom: 4px;
  color: #64748b;
  font-size: 13px;
}

.flow-context strong {
  display: block;
  overflow: hidden;
  color: #075985;
  font-size: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flow-actions {
  flex-shrink: 0;
}

@media (max-width: 1080px) {
  .flow-layout {
    align-items: stretch;
    flex-direction: column;
  }

  .flow-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
