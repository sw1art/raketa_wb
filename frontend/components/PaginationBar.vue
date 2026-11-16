<script setup lang="ts">
const props = defineProps<{
  offset: number
  limit: number
  total: number
}>()

const emit = defineEmits<{
  (e: 'update:offset', value: number): void
}>()

const page = computed(() => Math.floor(props.offset / props.limit) + 1)
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.limit)))

function go(next: number): void {
  const clamped = Math.min(Math.max(next, 1), pages.value)
  emit('update:offset', (clamped - 1) * props.limit)
}
</script>

<template>
  <div v-if="total > 0" class="pagination">
    <button class="btn btn--ghost btn--sm" :disabled="page <= 1" @click="go(page - 1)">← Назад</button>
    <span class="pagination__info">Стр. {{ page }} из {{ pages }} · всего {{ total }}</span>
    <button class="btn btn--ghost btn--sm" :disabled="page >= pages" @click="go(page + 1)">Вперёд →</button>
  </div>
</template>
