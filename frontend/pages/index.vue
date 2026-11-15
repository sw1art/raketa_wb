<script setup lang="ts">
import type { StockRow, StocksOverview } from '~/types/api'
import { useApi } from '~/composables/useApi'

const api = useApi()
const search = ref('')

const { data: overview, pending, error, refresh } = await useAsyncData<StocksOverview>(
  'stocks-overview',
  () => api.getStocks(),
)

const warehouses = computed(() => overview.value?.warehouses ?? [])

const filteredProducts = computed<StockRow[]>(() => {
  const rows = overview.value?.products ?? []
  const q = search.value.trim().toLowerCase()
  if (!q) return rows
  return rows.filter((p) => p.sku.toLowerCase().includes(q) || p.name.toLowerCase().includes(q))
})
</script>

<template>
  <div class="page">
    <div class="page__header">
      <h1 class="page__title">Складские остатки</h1>
      <div class="page__toolbar">
        <input
          v-model="search"
          type="search"
          class="input search-input"
          placeholder="Поиск по SKU или названию…"
        />
        <button class="btn btn--ghost" @click="refresh()">Обновить</button>
      </div>
    </div>

    <ErrorAlert :error="error" />
    <LoadingState v-if="pending" />
    <EmptyState
      v-else-if="!filteredProducts.length"
      title="Товары не найдены"
      text="Измените поисковый запрос или добавьте товар."
    />
    <StocksTable v-else :warehouses="warehouses" :products="filteredProducts" />
  </div>
</template>
