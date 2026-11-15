<script setup lang="ts">
import type { Product, Warehouse } from '~/types/api'
import { useApi } from '~/composables/useApi'
import { useAsyncAction } from '~/composables/useAsyncAction'

const props = defineProps<{
  products: Product[]
  warehouses: Warehouse[]
}>()

const emit = defineEmits<{
  (e: 'success'): void
}>()

const api = useApi()
const { submitting, error, run } = useAsyncAction()

const sourceWarehouseId = ref('')
const targetWarehouseId = ref('')
const productId = ref('')
const quantity = ref('')

const quantityNumber = computed<number | null>(() => {
  const n = Number(quantity.value)
  return Number.isInteger(n) && n > 0 ? n : null
})

const targetWarehouses = computed<Warehouse[]>(() =>
  props.warehouses.filter((w) => w.id !== sourceWarehouseId.value),
)

const isValid = computed<boolean>(
  () =>
    sourceWarehouseId.value !== '' &&
    targetWarehouseId.value !== '' &&
    productId.value !== '' &&
    quantityNumber.value !== null,
)

function reset(): void {
  sourceWarehouseId.value = ''
  targetWarehouseId.value = ''
  productId.value = ''
  quantity.value = ''
}

async function submit(): Promise<void> {
  const qty = quantityNumber.value
  if (qty === null) return
  const src = props.warehouses.find((w) => w.id === sourceWarehouseId.value)
  const tgt = props.warehouses.find((w) => w.id === targetWarehouseId.value)
  const p = props.products.find((x) => x.id === productId.value)
  if (!window.confirm(`Переместить ${qty} шт. товара «${p?.sku ?? ''}» со склада «${src?.name ?? ''}» на «${tgt?.name ?? ''}»?`)) return

  const ok = await run(() =>
    api.createTransfer({
      source_warehouse_id: sourceWarehouseId.value,
      target_warehouse_id: targetWarehouseId.value,
      items: [{ product_id: productId.value, quantity: qty }],
    }),
  )
  if (ok) {
    emit('success')
    reset()
  }
}
</script>

<template>
  <form class="card" @submit.prevent="submit">
    <h3 class="card__title">Перемещение</h3>
    <WarehousePicker v-model="sourceWarehouseId" :warehouses="warehouses" label="Со склада" />
    <WarehousePicker
      v-model="targetWarehouseId"
      :warehouses="targetWarehouses"
      label="На склад"
      placeholder="— выберите склад назначения —"
    />
    <ProductPicker v-model="productId" :products="products" label="Товар" />
    <div class="field">
      <label class="label">Количество</label>
      <input v-model="quantity" type="number" min="1" step="1" inputmode="numeric" class="input" placeholder="0" />
    </div>
    <p v-if="!isValid" class="form-hint">Укажите разные склады, товар и целое количество больше нуля.</p>
    <ErrorAlert :error="error" />
    <div class="form-actions">
      <button type="submit" class="btn btn--primary" :disabled="submitting || !isValid">
        {{ submitting ? 'Выполняется…' : 'Создать перемещение' }}
      </button>
    </div>
  </form>
</template>
