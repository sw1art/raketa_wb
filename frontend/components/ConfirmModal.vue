<script setup lang="ts">
import { useConfirm } from '~/composables/useConfirm'

const { state, accept, cancel } = useConfirm()

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') cancel()
}

// Блокируем прокрутку фона, пока открыто окно; позиция скролла сохраняется.
watch(
  () => state.open,
  (open) => {
    if (typeof document === 'undefined') return
    if (open) {
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', onKeydown)
    } else {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKeydown)
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="state.open" class="modal-overlay" @click.self="cancel">
        <div
          class="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-modal-title"
        >
          <h3 id="confirm-modal-title" class="modal__title">{{ state.title }}</h3>
          <p class="modal__message">{{ state.message }}</p>
          <div class="modal__actions">
            <button class="btn" @click="cancel">{{ state.cancelText }}</button>
            <button
              class="btn"
              :class="state.danger ? 'btn--danger' : 'btn--primary'"
              @click="accept"
            >
              {{ state.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
