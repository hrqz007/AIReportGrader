export const TASK_STATUS = Object.freeze({
  active: '进行中',
  ended: '已结束',
  archived: '已归档'
})

export const ACTIVE_TASK_STATUSES = [TASK_STATUS.active]

export function normalizeTaskStatus(status) {
  if (!status || status === '草稿') return TASK_STATUS.active
  return status
}

export function isTaskActive(task) {
  return normalizeTaskStatus(task?.status) === TASK_STATUS.active
}

export function taskStatusTagType(status) {
  const value = normalizeTaskStatus(status)
  if (value === TASK_STATUS.active) return 'success'
  if (value === TASK_STATUS.ended) return 'info'
  if (value === TASK_STATUS.archived) return ''
  return 'info'
}
