<script setup lang="ts">
import type { Product, Warehouse } from '~/types/api'
import { useApi } from '~/composables/useApi'

const api = useApi()

const { data: productsData, pending: productsPending, error: productsError } =
  await useAsyncData('ops-products', () => api.listProducts({ limit: 500 }))
const { data: warehouses, pending: warehousesPending, error: warehousesError } =
  await useAsyncData('ops-warehouses', () => api.listWarehouses())
const {
  data: reservations,
  pending: reservationsPending,
  error: reservationsError,
  refresh: refreshReservations,
} = await useAsyncData('ops-reservations', () => api.listReservations('ACTIVE'))
const {
  data: transfers,
  pending: transfersPending,
  error: transfersError,
  refresh: refreshTransfers,
} = await useAsyncData('ops-transfers', () => api.listTransfers())
const {
  data: shipmentsData,
  pending: shipmentsPending,
  error: shipmentsError,
  refresh: refreshShipments,
} = await useAsyncData('ops-fbo-shipments', () => api.listShipments({ type: 'FBO', limit: 500 }))

const products = computed<Product[]>(() => productsData.value?.items ?? [])
const activeWarehouses = computed<Warehouse[]>(() => (warehouses.value ?? []).filter((w) => w.is_active))
const activeReservations = computed(() => reservations.value ?? [])
const transferList = computed(() => transfers.value ?? [])
const fboShipments = computed(() => shipmentsData.value?.items ?? [])

const productsById = computed<Record<string, Product>>(() => {
  const map: Record<string, Product> = {}
  for (const p of products.value) map[p.id] = p
  return map
})

const warehousesById = computed<Record<string, Warehouse>>(() => {
  const map: Record<string, Warehouse> = {}
  for (const w of warehouses.value ?? []) map[w.id] = w
  return map
})

const anyError = computed(
  () =>
    productsError.value ??
    warehousesError.value ??
    reservationsError.value ??
    transfersError.value ??
    shipmentsError.value,
)

const anyPending = computed(
  () =>
    productsPending.value ||
    warehousesPending.value ||
    reservationsPending.value ||
    transfersPending.value ||
    shipmentsPending.value,
)

async function refreshAll(): Promise<void> {
  await Promise.all([refreshReservations(), refreshTransfers(), refreshShipments()])
}
</script>

<template>
  <div class="page">
    <div class="page__header">
      <h1 class="page__title">Операции</h1>
    </div>

    <ErrorAlert :error="anyError" />
    <LoadingState v-if="anyPending" text="Загрузка данных…" />

    <div v-else-if="!anyError" class="sections">
      <section class="section">
        <h2 class="section__title">Приход и резервирование</h2>
        <div class="card-grid">
          <ReceiptForm :products="products" :warehouses="activeWarehouses" @success="refreshAll" />
          <ReserveForm :products="products" :warehouses="activeWarehouses" @success="refreshAll" />
        </div>
      </section>

      <section class="section">
        <h2 class="section__title">FBS</h2>
        <div class="card-grid">
          <CancelReservationForm :reservations="activeReservations" @success="refreshAll" />
          <ShipFbsForm :reservations="activeReservations" @success="refreshAll" />
        </div>
      </section>

      <section class="section">
        <h2 class="section__title">Перемещение</h2>
        <div class="card-grid">
          <TransferForm :products="products" :warehouses="activeWarehouses" @success="refreshAll" />
        </div>
      </section>

      <section class="section">
        <h2 class="section__title">FBO</h2>
        <div class="card-grid">
          <ShipFboForm :products="products" :warehouses="activeWarehouses" @success="refreshAll" />
        </div>
      </section>

      <section class="section section--full">
        <h2 class="section__title">Приёмка</h2>
        <ReceivingPanel
          :transfers="transferList"
          :shipments="fboShipments"
          :products-by-id="productsById"
          :warehouses-by-id="warehousesById"
          @success="refreshAll"
        />
      </section>
    </div>
  </div>
</template>
