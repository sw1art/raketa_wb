<script setup lang="ts">
import type { Product, Shipment, Warehouse } from '~/types/api'
import { formatDateTime } from '~/utils/labels'

const props = defineProps<{
  shipments: Shipment[]
  productsById: Record<string, Product>
  warehousesById: Record<string, Warehouse>
}>()

function shortId(id: string): string {
  return id.slice(0, 8)
}

function skuList(s: Shipment): string {
  return s.items
    .map((i) => props.productsById[i.product_id]?.sku ?? shortId(i.product_id))
    .join(', ')
}

function totalQuantity(s: Shipment): number {
  return s.items.reduce((sum, i) => sum + i.quantity, 0)
}

function warehouseName(s: Shipment): string {
  return props.warehousesById[s.source_warehouse_id]?.name ?? shortId(s.source_warehouse_id)
}
</script>

<template>
  <div class="table-scroll">
    <table class="table">
      <thead>
        <tr>
          <th>Тип</th>
          <th>SKU</th>
          <th>Кол-во</th>
          <th>Склад</th>
          <th>Назначение</th>
          <th>Статус</th>
          <th>Создано</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in shipments" :key="s.id">
          <td>
            <span class="badge" :class="s.type === 'FBS' ? 'badge--purple' : 'badge--info'">
              {{ s.type }}
            </span>
          </td>
          <td class="sku">{{ skuList(s) }}</td>
          <td class="num">{{ totalQuantity(s) }}</td>
          <td>{{ warehouseName(s) }}</td>
          <td>{{ s.destination ?? '—' }}</td>
          <td><StatusBadge :status="s.status" /></td>
          <td class="muted">{{ formatDateTime(s.created_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
