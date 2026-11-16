<script setup lang="ts">
import type { Product, Warehouse } from '~/types/api'
import { statusLabel } from '~/utils/labels'
import { useApi } from '~/composables/useApi'

const api = useApi()
const PAGE_SIZE = 25

const typeFilter = ref('')
const statusFilter = ref('')
const offset = ref(0)

const shipmentStatuses: string[] = ['DRAFT', 'IN_TRANSIT', 'SHIPPED', 'RECEIVED', 'CANCELLED']

const { data: productsData } = await useAsyncData('shipments-products', () =>
  api.listProducts({ limit: 500 }),
)
const { data: warehouses } = await useAsyncData('shipments-warehouses', () => api.listWarehouses())

const { data: shipmentsData, pending, error, refresh } = await useAsyncData(
  'shipments',
  () =>
    api.listShipments({
      type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
      offset: offset.value,
      limit: PAGE_SIZE,
    }),
  { watch: [typeFilter, statusFilter, offset] },
)

const shipments = computed(() => shipmentsData.value?.items ?? [])
const total = computed(() => shipmentsData.value?.total ?? 0)

const productsById = computed<Record<string, Product>>(() => {
  const map: Record<string, Product> = {}
  for (const p of productsData.value?.items ?? []) map[p.id] = p
  return map
})

const warehousesById = computed<Record<string, Warehouse>>(() => {
  const map: Record<string, Warehouse> = {}
  for (const w of warehouses.value ?? []) map[w.id] = w
  return map
})

watch([typeFilter, statusFilter], () => {
  offset.value = 0
})
</script>

<template>
  <div class="page">
    <div class="page__header">
      <h1 class="page__title">Отправки</h1>
      <div class="page__toolbar">
        <select v-model="typeFilter" class="input">
          <option value="">Все типы</option>
          <option value="FBS">FBS</option>
          <option value="FBO">FBO</option>
        </select>
        <select v-model="statusFilter" class="input">
          <option value="">Все статусы</option>
          <option v-for="s in shipmentStatuses" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <button class="btn btn--ghost" @click="refresh()">Обновить</button>
      </div>
    </div>

    <ErrorAlert :error="error" />
    <LoadingState v-if="pending" />
    <EmptyState v-else-if="!shipments.length" text="Отправок с выбранными фильтрами нет." />
    <template v-else>
      <ShipmentsTable
        :shipments="shipments"
        :products-by-id="productsById"
        :warehouses-by-id="warehousesById"
      />
      <PaginationBar v-model:offset="offset" :limit="PAGE_SIZE" :total="total" />
    </template>
  </div>
</template>
