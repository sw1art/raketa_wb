<script setup lang="ts">
import type { Product, Shipment, TransferView, Warehouse } from '~/types/api'
import { useApi } from '~/composables/useApi'
import { useAsyncAction } from '~/composables/useAsyncAction'
import { useConfirm } from '~/composables/useConfirm'

const props = defineProps<{
  transfers: TransferView[]
  shipments: Shipment[]
  productsById: Record<string, Product>
  warehousesById: Record<string, Warehouse>
}>()

const emit = defineEmits<{
  (e: 'success'): void
}>()

const api = useApi()
const { submitting, error, run } = useAsyncAction()
const { confirm } = useConfirm()

const draftTransfers = computed<TransferView[]>(() => props.transfers.filter((t) => t.status === 'DRAFT'))
const inTransitTransfers = computed<TransferView[]>(() => props.transfers.filter((t) => t.status === 'IN_TRANSIT'))
const draftShipments = computed<Shipment[]>(() => props.shipments.filter((s) => s.status === 'DRAFT'))
const inTransitShipments = computed<Shipment[]>(() => props.shipments.filter((s) => s.status === 'IN_TRANSIT'))

function shortId(id: string): string {
  return id.slice(0, 8)
}

function transferItems(t: TransferView): string {
  return t.items.map((i) => `${i.sku} × ${i.quantity}`).join(', ')
}

function shipmentItems(s: Shipment): string {
  return s.items
    .map((i) => `${props.productsById[i.product_id]?.sku ?? shortId(i.product_id)} × ${i.quantity}`)
    .join(', ')
}

function shipmentWarehouse(s: Shipment): string {
  return props.warehousesById[s.source_warehouse_id]?.name ?? shortId(s.source_warehouse_id)
}

async function dispatchTransfer(t: TransferView): Promise<void> {
  const okConfirm = await confirm({
    title: 'Отправить перемещение',
    message: `Отправить перемещение со склада «${t.source_warehouse_name}» на «${t.target_warehouse_name}»?`,
    confirmText: 'Отправить',
  })
  if (!okConfirm) return
  const ok = await run(() => api.dispatchTransfer(t.id))
  if (ok) emit('success')
}

async function receiveTransfer(t: TransferView): Promise<void> {
  const okConfirm = await confirm({
    title: 'Принять перемещение',
    message: `Принять перемещение на склад «${t.target_warehouse_name}»?`,
    confirmText: 'Принять',
  })
  if (!okConfirm) return
  const ok = await run(() => api.receiveTransfer(t.id))
  if (ok) emit('success')
}

async function dispatchShipment(s: Shipment): Promise<void> {
  const okConfirm = await confirm({
    title: 'Отправить FBO',
    message: `Отправить FBO-отправку со склада «${shipmentWarehouse(s)}» на Wildberries?`,
    confirmText: 'Отправить',
  })
  if (!okConfirm) return
  const ok = await run(() => api.dispatchShipment(s.id))
  if (ok) emit('success')
}

async function receiveShipment(s: Shipment): Promise<void> {
  const okConfirm = await confirm({
    title: 'Приёмка FBO',
    message: 'Подтвердить приёмку FBO-отправки на Wildberries?',
    confirmText: 'Принять',
  })
  if (!okConfirm) return
  const ok = await run(() => api.receiveShipment(s.id))
  if (ok) emit('success')
}

const isEmpty = computed<boolean>(
  () =>
    draftTransfers.value.length === 0 &&
    inTransitTransfers.value.length === 0 &&
    draftShipments.value.length === 0 &&
    inTransitShipments.value.length === 0,
)
</script>

<template>
  <div class="card">
    <h3 class="card__title">Приёмка</h3>
    <ErrorAlert :error="error" />
    <EmptyState v-if="isEmpty" text="Нет перемещений или FBO-отправок, ожидающих отправки или приёмки." />

    <div v-if="draftTransfers.length" class="receiving-group">
      <div class="receiving-group__title">Перемещения — черновики</div>
      <div class="table-scroll">
        <table class="table">
          <thead>
            <tr><th>Откуда</th><th>Куда</th><th>Товары</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="t in draftTransfers" :key="t.id">
              <td>{{ t.source_warehouse_name }}</td>
              <td>{{ t.target_warehouse_name }}</td>
              <td>{{ transferItems(t) }}</td>
              <td>
                <button class="btn btn--sm btn--primary" :disabled="submitting" @click="dispatchTransfer(t)">
                  Отправить
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="draftShipments.length" class="receiving-group">
      <div class="receiving-group__title">Отправки FBO — черновики</div>
      <div class="table-scroll">
        <table class="table">
          <thead>
            <tr><th>Склад</th><th>Товары</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="s in draftShipments" :key="s.id">
              <td>{{ shipmentWarehouse(s) }}</td>
              <td>{{ shipmentItems(s) }}</td>
              <td>
                <button class="btn btn--sm btn--primary" :disabled="submitting" @click="dispatchShipment(s)">
                  Отправить
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="inTransitTransfers.length" class="receiving-group">
      <div class="receiving-group__title">Перемещения — в пути</div>
      <div class="table-scroll">
        <table class="table">
          <thead>
            <tr><th>Откуда</th><th>Куда</th><th>Товары</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="t in inTransitTransfers" :key="t.id">
              <td>{{ t.source_warehouse_name }}</td>
              <td>{{ t.target_warehouse_name }}</td>
              <td>{{ transferItems(t) }}</td>
              <td>
                <button class="btn btn--sm" :disabled="submitting" @click="receiveTransfer(t)">Принять</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="inTransitShipments.length" class="receiving-group">
      <div class="receiving-group__title">Отправки FBO — в пути</div>
      <div class="table-scroll">
        <table class="table">
          <thead>
            <tr><th>Склад</th><th>Товары</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="s in inTransitShipments" :key="s.id">
              <td>{{ shipmentWarehouse(s) }}</td>
              <td>{{ shipmentItems(s) }}</td>
              <td>
                <button class="btn btn--sm" :disabled="submitting" @click="receiveShipment(s)">Принять</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
