<script setup lang="ts">
import type { Product } from '~/types/api'

const props = defineProps<{
  products: Product[]
  modelValue: string
  label?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const query = ref('')

const filtered = computed<Product[]>(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.products
  return props.products.filter(
    (p) => p.sku.toLowerCase().includes(q) || p.name.toLowerCase().includes(q),
  )
})

function onChange(e: Event): void {
  const target = e.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <div class="field">
    <label v-if="label" class="label">{{ label }}</label>
    <input
      v-model="query"
      type="search"
      class="input"
      placeholder="Поиск по SKU или названию…"
    />
    <select class="input" :value="modelValue" @change="onChange">
      <option value="" disabled>— выберите товар —</option>
      <option v-for="p in filtered" :key="p.id" :value="p.id">
        {{ p.sku }} · {{ p.name }}
      </option>
    </select>
  </div>
</template>
