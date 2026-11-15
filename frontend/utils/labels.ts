// Russian labels, status -> tone mapping, and deterministic date formatting.
// Dates are rendered in Moscow time (UTC+3, no DST) so that server-rendered
// output is identical to the client-rendered output (no hydration mismatch).

const MSK_OFFSET_MS = 3 * 60 * 60 * 1000

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Черновик',
  IN_TRANSIT: 'В пути',
  RECEIVED: 'Принято',
  SHIPPED: 'Отправлен',
  CANCELLED: 'Отменён',
  ACTIVE: 'Активен',
  PENDING: 'Ожидает',
  PUBLISHED: 'Опубликовано',
  FAILED: 'Ошибка',
  SUCCESS: 'Успех',
  DEMO: 'Демо',
}

const STATUS_TONES: Record<string, string> = {
  DRAFT: 'neutral',
  IN_TRANSIT: 'info',
  RECEIVED: 'success',
  SHIPPED: 'purple',
  CANCELLED: 'danger',
  ACTIVE: 'success',
  PENDING: 'warning',
  PUBLISHED: 'success',
  FAILED: 'danger',
  SUCCESS: 'success',
  DEMO: 'warning',
}

const OPERATION_TYPE_LABELS: Record<string, string> = {
  RECEIPT: 'Приход',
  RESERVE: 'Резерв FBS',
  RESERVE_CANCEL: 'Отмена резерва',
  FBS_SHIP: 'Отправка FBS',
  FBO_CREATE: 'Создание FBO',
  FBO_DISPATCH: 'Отправка FBO',
  FBO_RECEIVE: 'Приёмка FBO',
  TRANSFER_CREATE: 'Создание перемещения',
  TRANSFER_DISPATCH: 'Отправка перемещения',
  TRANSFER_RECEIVE: 'Приёмка перемещения',
  WAREHOUSE_ARCHIVE: 'Архивация склада',
}

function pad(value: number): string {
  return value < 10 ? `0${value}` : String(value)
}

function toMsk(iso: string): Date | null {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return new Date(date.getTime() + MSK_OFFSET_MS)
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

export function statusTone(status: string): string {
  return STATUS_TONES[status] ?? 'neutral'
}

export function operationTypeLabel(type: string): string {
  return OPERATION_TYPE_LABELS[type] ?? type
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = toMsk(iso)
  if (!d) return '—'
  return `${pad(d.getUTCDate())}.${pad(d.getUTCMonth() + 1)}.${d.getUTCFullYear()}`
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = toMsk(iso)
  if (!d) return '—'
  return `${pad(d.getUTCDate())}.${pad(d.getUTCMonth() + 1)}.${d.getUTCFullYear()} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
}
