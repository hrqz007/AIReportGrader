<template>
  <div class="search-table-picker">
    <button
      type="button"
      class="picker-trigger"
      :class="{ disabled }"
      :disabled="disabled"
      @click="openDialog"
    >
      <span :class="{ placeholder: !selectedLabel }">{{ selectedLabel || placeholder }}</span>
      <span class="trigger-actions">
        <span v-if="clearable && modelValue != null" class="clear-action" @click.stop="clearValue">清空</span>
        <span class="open-action">选择</span>
      </span>
    </button>

    <el-dialog v-model="visible" :title="dialogTitle" width="760px" append-to-body>
      <div class="dialog-stack">
        <el-input
          v-model="keyword"
          clearable
          :placeholder="searchPlaceholder"
          @keyup.enter="selectFirst"
        />
        <el-table
          :data="filteredItems"
          border
          stripe
          highlight-current-row
          height="420"
          :empty-text="emptyText"
          @row-click="choose"
        >
          <el-table-column
            v-for="column in normalizedColumns"
            :key="column.prop"
            :prop="column.prop"
            :label="column.label"
            :width="column.width"
            :min-width="column.minWidth"
            :show-overflow-tooltip="column.tooltip !== false"
          />
        </el-table>
      </div>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button v-if="clearable" @click="clearValue">清空选择</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number, null], default: null },
  items: { type: Array, default: () => [] },
  valueKey: { type: String, default: 'id' },
  labelKey: { type: String, default: 'name' },
  placeholder: { type: String, default: '请选择' },
  dialogTitle: { type: String, default: '选择项目' },
  searchPlaceholder: { type: String, default: '输入关键词搜索' },
  emptyText: { type: String, default: '暂无可选数据' },
  columns: { type: Array, default: () => [] },
  clearable: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  searchKeys: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'change'])
const visible = ref(false)
const keyword = ref('')

const selected = computed(() => props.items.find((item) => item?.[props.valueKey] === props.modelValue))
const selectedLabel = computed(() => selected.value ? String(selected.value[props.labelKey] ?? '') : '')
const normalizedColumns = computed(() => {
  if (props.columns.length) return props.columns
  return [{ prop: props.labelKey, label: '名称', minWidth: 220 }]
})
const searchableKeys = computed(() => {
  if (props.searchKeys.length) return props.searchKeys
  return [...new Set([props.labelKey, ...normalizedColumns.value.map((item) => item.prop)])]
})
const filteredItems = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return props.items
  return props.items.filter((item) => searchableKeys.value.some((key) => String(item?.[key] ?? '').toLowerCase().includes(text)))
})

function openDialog() {
  if (props.disabled) return
  keyword.value = ''
  visible.value = true
}

function choose(row) {
  const value = row?.[props.valueKey]
  emit('update:modelValue', value)
  emit('change', value, row)
  visible.value = false
}

function clearValue() {
  emit('update:modelValue', null)
  emit('change', null, null)
  visible.value = false
}

function selectFirst() {
  if (filteredItems.value.length) choose(filteredItems.value[0])
}
</script>

<style scoped>
.picker-trigger {
  width: 100%;
  min-height: 40px;
  padding: 8px 10px 8px 12px;
  border: 1px solid #bfd7e7;
  border-radius: 8px;
  background: #fbfdff;
  color: #0f2233;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.picker-trigger:hover {
  border-color: #38a6d9;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.1);
}

.picker-trigger.disabled {
  cursor: not-allowed;
  opacity: 0.62;
  background: #eef5f9;
}

.placeholder {
  color: #7b93a7;
}

.trigger-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
  color: #0284c7;
  font-size: 13px;
  font-weight: 700;
}

.clear-action {
  color: #7b93a7;
}

.dialog-stack {
  display: grid;
  gap: 12px;
}
</style>
