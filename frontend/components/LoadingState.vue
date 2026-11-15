<script setup lang="ts">
defineProps<{
  text?: string
}>()
</script>

<template>
  <div class="loading">
    <span class="spinner" aria-hidden="true"></span>
    <span>{{ text ?? 'Загрузка…' }}</span>
  </div>
</template>
