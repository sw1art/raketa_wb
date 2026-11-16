<script setup lang="ts">
import type { ReservationView } from '~/types/api'
import { useApi } from '~/composables/useApi'
import { useAsyncAction } from '~/composables/useAsyncAction'
import { useConfirm } from '~/composables/useConfirm'

const props = defineProps<{
  reservations: ReservationView[]
}>()

const emit = defineEmits<{
  (e: 'success'): void
}>()

const api = useApi()
const { submitting, error, run } = useAsyncAction()
const { confirm } = useConfirm()

const reservationId = ref('')

const selected = computed<ReservationView | null>(
  () => props.reservations.find((r) => r.id === reservationId.value) ?? null,
)

function reset(): void {
  reservationId.value = ''
}

function onChange(e: Event): void {
  reservationId.value = (e.target as HTMLSelectElement).value
}

async function submit(): Promise<void> {
  const r = selected.value
  if (!r) return

  const okConfirm = await confirm({
    title: 'Отмена резерва',
    message: `Отменить резерв ${r.quantity} шт. товара «${r.sku}» на складе «${r.warehouse_name}»?`,
    confirmText: 'Отменить резерв',
    danger: true,
  })
  if (!okConfirm) return

  const ok = await run(() => api.cancelReservation(r.id))
  if (ok) {
    emit('success')
    reset()
  }
}
</script>

<template>
  <form class="card" @submit.prevent="submit">
    <h3 class="card__title">Отмена резерва</h3>
    <div class="field">
      <label class="label">Активный резерв</label>
      <select class="input" :value="reservationId" @change="onChange">
        <option value="" disabled>— выберите резерв —</option>
        <option v-for="r in reservations" :key="r.id" :value="r.id">
          {{ r.sku }} · {{ r.product_name }} — {{ r.warehouse_name }} ({{ r.quantity }} шт.)
        </option>
      </select>
    </div>
    <p v-if="!selected" class="form-hint">Выберите активный резерв для отмены.</p>
    <ErrorAlert :error="error" />
    <div class="form-actions">
      <button type="submit" class="btn btn--danger" :disabled="submitting || !selected">
        {{ submitting ? 'Выполняется…' : 'Отменить резерв' }}
      </button>
    </div>
  </form>
</template>
