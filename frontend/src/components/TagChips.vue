<script setup>
import { ref, computed, onMounted } from 'vue'
import { listTags, addShowTag, removeShowTag } from '../api'

const props = defineProps({
  show: { type: Object, required: true },
})
const emit = defineEmits(['update'])

const suggestions = ref([])
const newTag = ref('')
const busy = ref(false)

// Only tags this show doesn't already carry are worth suggesting.
const available = computed(() => {
  const applied = new Set(props.show.tags.map((t) => t.name))
  return suggestions.value.filter((t) => !applied.has(t.name))
})

async function loadSuggestions() {
  try {
    suggestions.value = await listTags()
  } catch {
    // autocomplete is a nicety; ignore failures
  }
}

async function removeTag(name) {
  if (busy.value) return
  busy.value = true
  try {
    const updated = await removeShowTag(props.show.id, name)
    emit('update', updated)
  } finally {
    busy.value = false
  }
}

async function addTag(raw = newTag.value) {
  const name = raw.trim()
  if (!name || busy.value) return
  busy.value = true
  try {
    const updated = await addShowTag(props.show.id, name)
    emit('update', updated)
    newTag.value = ''
    await loadSuggestions()
  } finally {
    busy.value = false
  }
}

// Picking a datalist option fires `input` with inputType
// 'insertReplacementText' (or none at all on older Firefox); typed characters
// always report their own inputType, so typing a word that happens to match a
// suggestion never submits itself. Requiring an exact match on top keeps
// spellcheck/autofill replacements from firing a request.
// Read the value off the element, not off `newTag` — this listener runs before
// v-model's, so the ref still holds the previous text.
function onInput(event) {
  const value = event.target.value
  const replaced = !event.inputType || event.inputType === 'insertReplacementText'
  if (replaced && available.value.some((t) => t.name === value)) {
    addTag(value)
  }
}

onMounted(loadSuggestions)
</script>

<template>
  <div class="tag-chips">
    <ul class="chips">
      <li v-for="tag in show.tags" :key="tag.name" class="chip">
        {{ tag.name }}
        <button
          type="button"
          class="remove-btn"
          :disabled="busy"
          :aria-label="`Remove tag ${tag.name}`"
          @click="removeTag(tag.name)"
        >✕</button>
      </li>
    </ul>
    <input
      v-model="newTag"
      list="tag-suggestions"
      type="text"
      placeholder="Add a tag…"
      class="tag-input"
      :disabled="busy"
      @input="onInput"
      @keyup.enter="addTag()"
    />
    <datalist id="tag-suggestions">
      <option v-for="t in available" :key="t.name" :value="t.name" />
    </datalist>
  </div>
</template>

<style scoped>
.tag-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 12px;
  color: var(--text-h);
  background: var(--accent-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-size: 11px;
  line-height: 1;
  color: var(--text);
  font-family: inherit;
}

.remove-btn:hover:not(:disabled) {
  color: var(--accent);
}

.remove-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.tag-input {
  padding: 3px 8px;
  font-size: 12px;
  font-family: var(--sans);
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text-h);
  min-width: 120px;
}

.tag-input:focus {
  outline: none;
  border-color: var(--accent);
}

.tag-input:disabled {
  opacity: 0.5;
}
</style>
