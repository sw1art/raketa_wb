<script setup lang="ts">
interface NavLink {
  to: string
  label: string
}

const links: NavLink[] = [
  { to: '/', label: 'Остатки' },
  { to: '/warehouses', label: 'Склады' },
  { to: '/operations', label: 'Операции' },
  { to: '/shipments', label: 'Отправки' },
  { to: '/history', label: 'История' },
]
</script>

<template>
  <header class="app-header">
    <div class="container header-inner">
      <NuxtLink to="/" class="brand">
        Check<span class="brand__accent">Stock</span>
      </NuxtLink>
      <nav class="nav">
        <NuxtLink v-for="link in links" :key="link.to" :to="link.to" class="nav-link">
          {{ link.label }}
        </NuxtLink>
      </nav>
    </div>
  </header>
</template>
