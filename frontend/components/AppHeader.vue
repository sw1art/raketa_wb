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

const menuOpen = ref(false)

function closeMenu(): void {
  menuOpen.value = false
}
</script>

<template>
  <header class="app-header">
    <div class="container header-inner">
      <NuxtLink to="/" class="brand" @click="closeMenu">
        Check<span class="brand__accent">Stock</span>
      </NuxtLink>

      <button
        class="nav-toggle"
        aria-label="Меню"
        :aria-expanded="menuOpen"
        @click="menuOpen = !menuOpen"
      >
        <span class="nav-toggle__bar" :class="{ 'is-open': menuOpen }" />
        <span class="nav-toggle__bar" :class="{ 'is-open': menuOpen }" />
        <span class="nav-toggle__bar" :class="{ 'is-open': menuOpen }" />
      </button>

      <nav class="nav" :class="{ 'nav--open': menuOpen }">
        <NuxtLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="nav-link"
          @click="closeMenu"
        >
          {{ link.label }}
        </NuxtLink>
      </nav>
    </div>
  </header>
</template>
