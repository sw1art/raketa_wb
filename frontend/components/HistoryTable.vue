<script setup lang="ts">
import type { HistoryEntry } from '~/types/api'
import { formatDateTime, operationTypeLabel } from '~/utils/labels'

defineProps<{
  entries: HistoryEntry[]
}>()
</script>

<template>
  <div class="table-scroll">
    <table class="table">
      <thead>
        <tr>
          <th>Операция</th>
          <th>SKU</th>
          <th>Товар</th>
          <th>Кол-во</th>
          <th>Откуда</th>
          <th>Куда</th>
          <th>Дата</th>
          <th>Статус</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(e, idx) in entries" :key="`${e.operation_id}-${idx}`">
          <td><span class="badge badge--neutral">{{ operationTypeLabel(e.operation_type) }}</span></td>
          <td class="sku">{{ e.sku ?? '—' }}</td>
          <td>{{ e.product_name ?? '—' }}</td>
          <td class="num">{{ e.quantity }}</td>
          <td>{{ e.source_warehouse_name ?? '—' }}</td>
          <td>{{ e.target_warehouse_name ?? '—' }}</td>
          <td class="muted">{{ formatDateTime(e.created_at) }}</td>
          <td><StatusBadge :status="e.status" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
