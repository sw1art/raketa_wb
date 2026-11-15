<script setup lang="ts">
defineProps<{
  title?: string
  text?: string
}>()
</script>

<template>
  <div class="empty">
    <div class="empty__icon" aria-hidden="true">◌</div>
    <p class="empty__title">{{ title ?? 'Ничего не найдено' }}</p>
    <p v-if="text" class="empty__text">{{ text }}</p>
  </div>
</template>
