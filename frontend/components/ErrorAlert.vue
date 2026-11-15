<script setup lang="ts">
import type { ArchiveDetail, ShortageDetail } from '~/types/api'

const props = defineProps<{
  error: unknown
}>()

function isShortage(detail: unknown): detail is ShortageDetail {
  return (
    typeof detail === 'object' &&
    detail !== null &&
    'shortfall' in detail &&
    'other_warehouses' in detail
  )
}

function isArchive(detail: unknown): detail is ArchiveDetail {
  return (
    typeof detail === 'object' &&
    detail !== null &&
    'reasons' in detail &&
    'nonzero_stocks' in detail
  )
}

const message = computed<string>(() => {
  const e = props.error as { message?: unknown } | null | undefined
  if (e && typeof e.message === 'string') return e.message
  if (typeof props.error === 'string') return props.error
  return 'Произошла неизвестная ошибка'
})

const code = computed<string | null>(() => {
  const e = props.error as { code?: unknown } | null | undefined
  return e && typeof e.code === 'string' ? e.code : null
})

const detail = computed<unknown>(() => {
  const e = props.error as { detail?: unknown } | null | undefined
  return e ? e.detail : null
})

const shortage = computed<ShortageDetail | null>(() => (isShortage(detail.value) ? detail.value : null))
const archive = computed<ArchiveDetail | null>(() => (isArchive(detail.value) ? detail.value : null))
</script>

<template>
  <div v-if="error" class="alert alert--danger" role="alert">
    <div class="alert__title">
      <span v-if="code" class="alert__code">{{ code }}</span>
      {{ message }}
    </div>

    <div v-if="shortage" class="alert__detail">
      <p class="alert__detail-line">
        Запрошено: <strong>{{ shortage.requested }}</strong>, доступно:
        <strong>{{ shortage.available }}</strong>, не хватает:
        <strong>{{ shortage.shortfall }}</strong>.
      </p>
      <div v-if="shortage.other_warehouses.length">
        <p class="alert__detail-heading">Доступно на других складах:</p>
        <ul class="alert__list">
          <li v-for="wh in shortage.other_warehouses" :key="wh.warehouse_id">
            {{ wh.name }} — {{ wh.available }} шт.
          </li>
        </ul>
      </div>
      <p class="alert__hint">Создайте внутреннее перемещение с одного из этих складов.</p>
    </div>

    <div v-else-if="archive" class="alert__detail">
      <ul class="alert__list">
        <li v-for="reason in archive.reasons" :key="reason">{{ reason }}</li>
      </ul>
      <table v-if="archive.nonzero_stocks.length" class="alert__table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Товар</th>
            <th>Физический остаток</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ns in archive.nonzero_stocks" :key="ns.product_id">
            <td>{{ ns.sku }}</td>
            <td>{{ ns.name }}</td>
            <td>{{ ns.physical }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
