/**
 * Глобальный сервис модального подтверждения (вместо window.confirm).
 * Возвращает Promise<boolean>: true — подтверждено, false — отменено.
 */

export interface ConfirmOptions {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}

interface ConfirmState {
  open: boolean
  title: string
  message: string
  confirmText: string
  cancelText: string
  danger: boolean
  resolver: ((value: boolean) => void) | null
}

const state = reactive<ConfirmState>({
  open: false,
  title: '',
  message: '',
  confirmText: 'Подтвердить',
  cancelText: 'Отмена',
  danger: false,
  resolver: null,
})

export function useConfirm() {
  function confirm(options: ConfirmOptions): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      state.title = options.title
      state.message = options.message
      state.confirmText = options.confirmText ?? 'Подтвердить'
      state.cancelText = options.cancelText ?? 'Отмена'
      state.danger = options.danger ?? false
      state.resolver = resolve
      state.open = true
    })
  }

  function settle(value: boolean): void {
    state.open = false
    const resolver = state.resolver
    state.resolver = null
    resolver?.(value)
  }

  return {
    state,
    confirm,
    accept: () => settle(true),
    cancel: () => settle(false),
  }
}
