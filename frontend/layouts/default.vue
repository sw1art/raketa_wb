<template>
  <div class="app-shell">
    <AppHeader />
    <main class="app-main">
      <div class="container">
        <slot />
      </div>
    </main>
    <ToastStack />
  </div>
</template>
