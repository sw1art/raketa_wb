/**
 * Small helper that wraps a single async mutation: tracks a submitting flag
 * and captures the first thrown error for display.
 */
export function useAsyncAction() {
  const submitting = ref(false)
  const error = ref<unknown>(null)

  async function run(action: () => Promise<unknown>): Promise<boolean> {
    submitting.value = true
    error.value = null
    try {
      await action()
      return true
    } catch (err) {
      error.value = err
      return false
    } finally {
      submitting.value = false
    }
  }

  function clearError(): void {
    error.value = null
  }

  return { submitting, error, run, clearError }
}
