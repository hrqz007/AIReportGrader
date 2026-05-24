import { reactive } from 'vue'

export function useActionNotice(defaultDuration = 10000) {
  const actionNotice = reactive({
    type: 'success',
    text: '',
    detail: '',
    countdown: 0
  })

  let hideTimer = null
  let countdownTimer = null

  function clearNotice() {
    if (hideTimer) window.clearTimeout(hideTimer)
    if (countdownTimer) window.clearInterval(countdownTimer)
    hideTimer = null
    countdownTimer = null
    actionNotice.type = 'success'
    actionNotice.text = ''
    actionNotice.detail = ''
    actionNotice.countdown = 0
  }

  function showNotice(type, text, detail = '', duration = defaultDuration) {
    clearNotice()
    actionNotice.type = type || 'success'
    actionNotice.text = text || ''
    actionNotice.detail = detail || ''
    if (!actionNotice.text) return

    if (duration && duration > 0) {
      actionNotice.countdown = Math.ceil(duration / 1000)
      countdownTimer = window.setInterval(() => {
        actionNotice.countdown = Math.max(actionNotice.countdown - 1, 0)
      }, 1000)
      hideTimer = window.setTimeout(clearNotice, duration)
    }
  }

  return { actionNotice, showNotice, clearNotice }
}
