<script setup lang="ts">
import type { StockRow, Warehouse, WarehouseStockRow } from '~/types/api'

const props = defineProps<{
  warehouses: Warehouse[]
  products: StockRow[]
}>()

const zero: WarehouseStockRow = {
  warehouse_id: '',
  warehouse_name: '',
  physical: 0,
  reserved: 0,
  available: 0,
}

function cell(product: StockRow, warehouseId: string): WarehouseStockRow {
  return product.warehouses.find((w) => w.warehouse_id === warehouseId) ?? zero
}
</script>

<template>
  <div class="table-scroll">
    <table class="table stocks-table">
      <thead>
        <tr>
          <th rowspan="2">SKU</th>
          <th rowspan="2">Название</th>
          <th v-for="wh in warehouses" :key="wh.id" colspan="3" class="col-warehouse">
            {{ wh.name }}
          </th>
          <th colspan="3" class="col-total">Итого</th>
          <th colspan="3" class="col-transit">В пути</th>
        </tr>
        <tr>
          <template v-for="wh in warehouses" :key="`h-${wh.id}`">
            <th class="sub">Физ.</th>
            <th class="sub">Резерв</th>
            <th class="sub">Доступно</th>
          </template>
          <th class="sub">Физ.</th>
          <th class="sub">Резерв</th>
          <th class="sub">Доступно</th>
          <th class="sub transit-transfer">Перемещ.</th>
          <th class="sub transit-fbo">FBO</th>
          <th class="sub transit-fbs">FBS</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in products" :key="p.product_id">
          <td class="sku">{{ p.sku }}</td>
          <td>
            <div>{{ p.name }}</div>
            <div v-if="p.wb_external_id" class="muted">WB: {{ p.wb_external_id }}</div>
          </td>
          <template v-for="wh in warehouses" :key="`b-${wh.id}`">
            <td class="num">{{ cell(p, wh.id).physical }}</td>
            <td class="num">{{ cell(p, wh.id).reserved }}</td>
            <td class="num available">{{ cell(p, wh.id).available }}</td>
          </template>
          <td class="num total">{{ p.total_physical }}</td>
          <td class="num total">{{ p.total_reserved }}</td>
          <td class="num total available">{{ p.total_available }}</td>
          <td class="num transit-transfer">{{ p.in_transit.transfer }}</td>
          <td class="num transit-fbo">{{ p.in_transit.fbo }}</td>
          <td class="num transit-fbs">{{ p.in_transit.fbs }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
