/**
 * Global toast notifications (success / error / info).
 * Shared singleton state, so toasts survive across component unmounts.
 */

export type ToastType = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
}

const toasts = ref<Toast[]>([])
let nextId = 0

function dismiss(id: number): void {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}

function push(type: ToastType, message: string, timeoutMs = 4000): void {
  const id = ++nextId
  toasts.value.push({ id, type, message })
  if (timeoutMs > 0) {
    setTimeout(() => dismiss(id), timeoutMs)
  }
}

export function useToast() {
  return {
    toasts: readonly(toasts),
    success: (message: string) => push('success', message),
    error: (message: string) => push('error', message, 7000),
    info: (message: string) => push('info', message),
    dismiss,
  }
}
