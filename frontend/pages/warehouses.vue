<script setup lang="ts">
import type { Warehouse, WarehouseStockRow } from '~/types/api'
import { useApi } from '~/composables/useApi'

interface WarehouseStockLine extends WarehouseStockRow {
  product_id: string
  sku: string
  name: string
}

const api = useApi()

const { data: warehouses, pending: pendingWh, error: errorWh, refresh: refreshWh } =
  await useAsyncData('warehouses', () => api.listWarehouses())
const { data: stocks, pending: pendingStocks, error: errorStocks, refresh: refreshStocks } =
  await useAsyncData('stocks-for-warehouses', () => api.getStocks())

const warehouseList = computed<Warehouse[]>(() => warehouses.value ?? [])
const pageError = computed(() => errorWh.value ?? errorStocks.value)
const pending = computed(() => pendingWh.value || pendingStocks.value)

const stockLines = computed<Record<string, WarehouseStockLine[]>>(() => {
  const map: Record<string, WarehouseStockLine[]> = {}
  for (const p of stocks.value?.products ?? []) {
    for (const w of p.warehouses) {
      if (w.physical > 0 || w.reserved > 0) {
        const list = map[w.warehouse_id] ?? []
        list.push({ ...w, product_id: p.product_id, sku: p.sku, name: p.name })
        map[w.warehouse_id] = list
      }
    }
  }
  return map
})

interface StockSummary {
  physical: number
  reserved: number
  available: number
}

function summary(warehouseId: string): StockSummary {
  const lines: WarehouseStockLine[] = stockLines.value[warehouseId] ?? []
  const result: StockSummary = { physical: 0, reserved: 0, available: 0 }
  for (const line of lines) {
    result.physical += line.physical
    result.reserved += line.reserved
    result.available += line.available
  }
  return result
}

async function refreshAll(): Promise<void> {
  await Promise.all([refreshWh(), refreshStocks()])
}

// Create
const createName = ref('')
const createSubmitting = ref(false)
const createError = ref<unknown>(null)

async function createWarehouse(): Promise<void> {
  const name = createName.value.trim()
  if (!name) return
  createSubmitting.value = true
  createError.value = null
  try {
    await api.createWarehouse({ name })
    createName.value = ''
    await refreshAll()
  } catch (err) {
    createError.value = err
  } finally {
    createSubmitting.value = false
  }
}

// Rename
const editingId = ref<string | null>(null)
const renameValue = ref('')
const renameSubmitting = ref(false)
const renameError = ref<unknown>(null)

function startRename(wh: Warehouse): void {
  editingId.value = wh.id
  renameValue.value = wh.name
  renameError.value = null
}

function cancelRename(): void {
  editingId.value = null
  renameValue.value = ''
}

async function saveRename(wh: Warehouse): Promise<void> {
  const name = renameValue.value.trim()
  if (!name) return
  renameSubmitting.value = true
  renameError.value = null
  try {
    await api.renameWarehouse(wh.id, { name })
    editingId.value = null
    await refreshAll()
  } catch (err) {
    renameError.value = err
  } finally {
    renameSubmitting.value = false
  }
}

// Archive
const archiveSubmitting = ref(false)
const archiveErrors = ref<Record<string, unknown>>({})

async function archive(wh: Warehouse): Promise<void> {
  if (!window.confirm(`Архивировать склад «${wh.name}»? Это действие нельзя отменить.`)) return
  archiveSubmitting.value = true
  delete archiveErrors.value[wh.id]
  try {
    await api.archiveWarehouse(wh.id)
    await refreshAll()
  } catch (err) {
    archiveErrors.value[wh.id] = err
  } finally {
    archiveSubmitting.value = false
  }
}

// Expand per-warehouse stock
const expandedId = ref<string | null>(null)

function toggleExpand(id: string): void {
  expandedId.value = expandedId.value === id ? null : id
}
</script>

<template>
  <div class="page">
    <div class="page__header">
      <h1 class="page__title">Склады</h1>
      <div class="page__toolbar">
        <button class="btn btn--ghost" @click="refreshAll">Обновить</button>
      </div>
    </div>

    <ErrorAlert :error="pageError" />

    <form class="card" @submit.prevent="createWarehouse">
      <h3 class="card__title">Новый склад</h3>
      <div class="inline-form">
        <input v-model="createName" class="input" placeholder="Название склада" maxlength="255" />
        <button type="submit" class="btn btn--primary" :disabled="createSubmitting || !createName.trim()">
          {{ createSubmitting ? 'Создание…' : 'Создать' }}
        </button>
      </div>
      <ErrorAlert :error="createError" />
    </form>

    <LoadingState v-if="pending" text="Загрузка складов…" />
    <EmptyState v-else-if="!warehouseList.length" text="Складов пока нет. Создайте первый склад." />

    <div v-else class="warehouse-grid">
      <div
        v-for="wh in warehouseList"
        :key="wh.id"
        class="warehouse-card"
        :class="{ 'warehouse-card--archived': !wh.is_active }"
      >
        <div class="warehouse-card__header">
          <h2 class="warehouse-card__name">{{ wh.name }}</h2>
          <span class="badge" :class="wh.is_active ? 'badge--active' : 'badge--archived'">
            {{ wh.is_active ? 'Активен' : 'Архивирован' }}
          </span>
          <div v-if="wh.is_active" class="warehouse-card__actions">
            <button class="btn btn--sm" @click="startRename(wh)">Переименовать</button>
            <button class="btn btn--sm btn--danger" :disabled="archiveSubmitting" @click="archive(wh)">
              Архив
            </button>
          </div>
        </div>

        <div v-if="editingId === wh.id" class="inline-form" style="margin-top: 12px">
          <input v-model="renameValue" class="input" maxlength="255" />
          <button class="btn btn--sm btn--primary" :disabled="renameSubmitting" @click="saveRename(wh)">
            Сохранить
          </button>
          <button class="btn btn--sm" @click="cancelRename">Отмена</button>
        </div>

        <ErrorAlert :error="renameError" />
        <ErrorAlert :error="archiveErrors[wh.id] ?? null" />

        <div class="warehouse-card__stats">
          <div class="stat">
            <div class="stat__value">{{ summary(wh.id).physical }}</div>
            <div class="stat__label">Физический</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ summary(wh.id).reserved }}</div>
            <div class="stat__label">Резерв</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ summary(wh.id).available }}</div>
            <div class="stat__label">Доступно</div>
          </div>
        </div>

        <button class="btn btn--sm btn--ghost" @click="toggleExpand(wh.id)">
          {{ expandedId === wh.id ? 'Скрыть остатки' : 'Показать остатки' }}
        </button>

        <div v-if="expandedId === wh.id" class="table-scroll" style="margin-top: 12px">
          <table class="table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Товар</th>
                <th>Физ.</th>
                <th>Резерв</th>
                <th>Доступно</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in stockLines[wh.id] ?? []" :key="line.product_id">
                <td class="sku">{{ line.sku }}</td>
                <td>{{ line.name }}</td>
                <td class="num">{{ line.physical }}</td>
                <td class="num">{{ line.reserved }}</td>
                <td class="num available">{{ line.available }}</td>
              </tr>
              <tr v-if="!(stockLines[wh.id]?.length)">
                <td colspan="5" class="muted">Нет остатков на этом складе.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
