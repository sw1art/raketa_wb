<script setup lang="ts">
import { statusLabel, statusTone } from '~/utils/labels'

const props = defineProps<{
  status: string
}>()

const label = computed(() => statusLabel(props.status))
const tone = computed(() => statusTone(props.status))
</script>

<template>
  <span class="badge" :class="`badge--${tone}`">{{ label }}</span>
</template>
