<script setup lang="ts">
import { useToast } from '~/composables/useToast'

const { toasts, dismiss } = useToast()
</script>

<template>
  <div class="toast-stack" role="status" aria-live="polite">
    <div v-for="toast in toasts" :key="toast.id" class="toast" :class="`toast--${toast.type}`">
      <span class="toast__icon" aria-hidden="true">{{ toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : 'ℹ' }}</span>
      <span class="toast__message">{{ toast.message }}</span>
      <button class="toast__close" aria-label="Закрыть" @click="dismiss(toast.id)">×</button>
    </div>
  </div>
</template>
