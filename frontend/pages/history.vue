<script setup lang="ts">
import { operationTypeLabel } from '~/utils/labels'
import { useApi } from '~/composables/useApi'

const api = useApi()
const typeFilter = ref('')
const skuFilter = ref('')

const operationTypes: string[] = [
  'RECEIPT',
  'RESERVE',
  'RESERVE_CANCEL',
  'FBS_SHIP',
  'FBO_CREATE',
  'FBO_DISPATCH',
  'FBO_RECEIVE',
  'TRANSFER_CREATE',
  'TRANSFER_DISPATCH',
  'TRANSFER_RECEIVE',
  'WAREHOUSE_ARCHIVE',
]

const { data: historyData, pending, error, refresh } = await useAsyncData(
  'history',
  () =>
    api.listHistory({
      operation_type: typeFilter.value || undefined,
      sku: skuFilter.value || undefined,
      limit: 500,
    }),
  { watch: [typeFilter, skuFilter] },
)

const entries = computed(() => historyData.value?.items ?? [])
const total = computed(() => historyData.value?.total ?? 0)
</script>

<template>
  <div class="page">
    <div class="page__header">
      <h1 class="page__title">История операций</h1>
      <div class="page__toolbar">
        <select v-model="typeFilter" class="input">
          <option value="">Все операции</option>
          <option v-for="t in operationTypes" :key="t" :value="t">{{ operationTypeLabel(t) }}</option>
        </select>
        <input v-model="skuFilter" type="search" class="input search-input" placeholder="Фильтр по SKU…" />
        <button class="btn btn--ghost" @click="refresh()">Обновить</button>
      </div>
    </div>

    <p class="page__meta">Всего записей: {{ total }}</p>

    <ErrorAlert :error="error" />
    <LoadingState v-if="pending" />
    <EmptyState v-else-if="!entries.length" text="Записей в истории с выбранными фильтрами нет." />
    <HistoryTable v-else :entries="entries" />
  </div>
</template>
