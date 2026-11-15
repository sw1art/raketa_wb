<script setup lang="ts">
import type { ReservationView } from '~/types/api'
import { useApi } from '~/composables/useApi'
import { useAsyncAction } from '~/composables/useAsyncAction'

const props = defineProps<{
  reservations: ReservationView[]
}>()

const emit = defineEmits<{
  (e: 'success'): void
}>()

const api = useApi()
const { submitting, error, run } = useAsyncAction()

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
  if (!window.confirm(`Отправить ${r.quantity} шт. товара «${r.sku}» со склада «${r.warehouse_name}» (FBS)?`)) return

  const ok = await run(() => api.shipFbs({ reservation_id: r.id }))
  if (ok) {
    emit('success')
    reset()
  }
}
</script>

<template>
  <form class="card" @submit.prevent="submit">
    <h3 class="card__title">Отправка FBS</h3>
    <div class="field">
      <label class="label">Активный резерв</label>
      <select class="input" :value="reservationId" @change="onChange">
        <option value="" disabled>— выберите резерв —</option>
        <option v-for="r in reservations" :key="r.id" :value="r.id">
          {{ r.sku }} · {{ r.product_name }} — {{ r.warehouse_name }} ({{ r.quantity }} шт.)
        </option>
      </select>
    </div>
    <p v-if="!selected" class="form-hint">Выберите активный резерв для отправки.</p>
    <ErrorAlert :error="error" />
    <div class="form-actions">
      <button type="submit" class="btn btn--primary" :disabled="submitting || !selected">
        {{ submitting ? 'Выполняется…' : 'Отправить FBS' }}
      </button>
    </div>
  </form>
</template>
