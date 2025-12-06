<template>
  <div class="character-card">
    <div class="header">
      <span class="name">{{ character.name }}</span>
      <span class="class-level">{{ character.char_class }} {{ character.level }}</span>
    </div>

    <div class="stats">
      <div class="stat hp">
        <span class="label">HP</span>
        <div class="bar-container">
          <div class="bar" :style="{ width: hpPercent + '%' }"></div>
        </div>
        <span class="value">{{ character.hp }}/{{ character.hp_max }}</span>
      </div>

      <div class="stat ac">
        <span class="label">AC</span>
        <span class="value">{{ character.ac }}</span>
      </div>
    </div>

    <div v-if="character.conditions?.length" class="conditions">
      <span
        v-for="condition in character.conditions"
        :key="condition"
        class="condition"
      >
        {{ condition }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  character: {
    type: Object,
    required: true,
  },
})

const hpPercent = computed(() => {
  const { hp, hp_max } = props.character
  if (!hp_max) return 0
  return Math.max(0, Math.min(100, (hp / hp_max) * 100))
})
</script>

<style scoped>
.character-card {
  background: #1a1a2e;
  border-radius: 4px;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
}

.header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.name {
  font-weight: bold;
  color: #eee;
}

.class-level {
  font-size: 0.875rem;
  color: #888;
}

.stats {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stat.hp {
  flex: 1;
}

.label {
  font-size: 0.75rem;
  color: #888;
  width: 20px;
}

.bar-container {
  flex: 1;
  height: 8px;
  background: #333;
  border-radius: 4px;
  overflow: hidden;
}

.bar {
  height: 100%;
  background: #4caf50;
  transition: width 0.3s ease;
}

.value {
  font-size: 0.875rem;
  color: #eee;
  min-width: 50px;
  text-align: right;
}

.conditions {
  margin-top: 0.5rem;
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.condition {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  background: #e65100;
  color: white;
  border-radius: 4px;
}
</style>
