<script setup lang="ts">
import type { Warehouse } from '~/types/api'

const props = defineProps<{
  warehouses: Warehouse[]
  modelValue: string
  label?: string
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

function onChange(e: Event): void {
  const target = e.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <div class="field">
    <label v-if="label" class="label">{{ label }}</label>
    <select class="input" :value="modelValue" @change="onChange">
      <option value="" disabled>{{ placeholder ?? '— выберите склад —' }}</option>
      <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
    </select>
  </div>
</template>
