<script setup>
// Small segmented toggle. v-model holds the selected value.
defineProps({
  options: { type: Array, required: true }, // [{ label, value }]
  modelValue: { required: true },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="segmented" role="group">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      class="seg"
      :class="{ active: opt.value === modelValue }"
      :disabled="opt.disabled"
      @click="$emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.seg {
  border: none;
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 12px;
  line-height: 1.6;
  padding: 3px 10px;
  cursor: pointer;
}

.seg + .seg {
  border-left: 1px solid var(--border);
}

.seg.active {
  background: var(--accent-bg);
  color: var(--text-h);
  font-weight: 500;
}

.seg:hover:not(.active):not(:disabled) {
  color: var(--text-h);
}

.seg:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
