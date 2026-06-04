/**
 * Build an optimistic-update helper bound to a piece of state.
 *
 *   const applyPatch = createPatchHelper({
 *     getter: () => show.value,
 *     setter: (v) => { show.value = v },
 *     update: updateShow,
 *   })
 *
 *   await applyPatch({ is_favorite: true })
 *
 * The returned function:
 *   1. Reads the current value via `getter()`.
 *   2. Writes an optimistic merge via `setter(...)` — UI updates immediately.
 *   3. Calls `update(id, patch)` to PATCH the server.
 *   4. On success, replaces state with the server's response.
 *   5. On failure, reverts to the original value.
 */
export function createPatchHelper({ getter, setter, update }) {
  return async function applyPatch(patch) {
    const original = getter()
    setter({ ...original, ...patch })
    try {
      setter(await update(original.id, patch))
    } catch (err) {
      setter(original)
      console.error('Failed to update:', err)
    }
  }
}
