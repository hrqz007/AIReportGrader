<template>
  <el-alert
    v-if="notice?.text"
    class="inline-action-notice"
    :type="notice.type || 'success'"
    :closable="true"
    show-icon
    @close="clear"
  >
    <template #title>
      <span>{{ notice.text }}</span>
      <span v-if="notice.countdown" class="notice-countdown">约 {{ notice.countdown }} 秒后自动隐藏</span>
    </template>
    <div v-if="notice.detail" class="notice-detail">{{ notice.detail }}</div>
  </el-alert>
</template>

<script setup>
defineProps({
  notice: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['clear'])

function clear() {
  emit('clear')
}
</script>

<style scoped>
.inline-action-notice {
  margin: 12px 0 14px;
}

.notice-countdown {
  margin-left: 12px;
  color: #64748b;
  font-weight: 500;
}

.notice-detail {
  margin-top: 6px;
  line-height: 1.6;
  word-break: break-word;
}
</style>
