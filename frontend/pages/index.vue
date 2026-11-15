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

const totals = computed(() => {
  const rows = overview.value?.products ?? []
  return {
    physical: rows.reduce((sum, p) => sum + p.total_physical, 0),
    reserved: rows.reduce((sum, p) => sum + p.total_reserved, 0),
    available: rows.reduce((sum, p) => sum + p.total_available, 0),
    inTransit: rows.reduce((sum, p) => sum + p.in_transit_total, 0),
  }
})

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
    <template v-else>
      <div class="summary-grid">
        <div class="summary-card">
          <span class="summary-card__value">{{ totals.physical }}</span>
          <span class="summary-card__label">Физический остаток</span>
        </div>
        <div class="summary-card summary-card--reserved">
          <span class="summary-card__value">{{ totals.reserved }}</span>
          <span class="summary-card__label">В резерве FBS</span>
        </div>
        <div class="summary-card summary-card--available">
          <span class="summary-card__value">{{ totals.available }}</span>
          <span class="summary-card__label">Доступно</span>
        </div>
        <div class="summary-card summary-card--transit">
          <span class="summary-card__value">{{ totals.inTransit }}</span>
          <span class="summary-card__label">В пути</span>
        </div>
      </div>

      <EmptyState
        v-if="!filteredProducts.length"
        title="Товары не найдены"
        text="Измените поисковый запрос или добавьте товар."
      />
      <StocksTable v-else :warehouses="warehouses" :products="filteredProducts" />
    </template>
  </div>
</template>
