<template>
  <section class="state-dashboard">
    <h2>State Dashboard</h2>

    <div class="section">
      <h3>Party</h3>
      <CharacterCard
        v-for="char in party"
        :key="char.name"
        :character="char"
      />
      <p v-if="party.length === 0" class="empty">No characters loaded</p>
    </div>

    <div v-if="location" class="section">
      <h3>Location</h3>
      <p class="location">📍 {{ location }}</p>
    </div>

    <div v-if="encounter" class="section">
      <h3>Current Encounter</h3>
      <div class="encounter">
        <div v-for="(enemy, index) in encounter" :key="index" class="enemy">
          {{ enemy.name }}
          <span v-if="enemy.status" class="status">({{ enemy.status }})</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import CharacterCard from './CharacterCard.vue'

const props = defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

const party = ref([])
const location = ref('')
const encounter = ref([])

// Extract state from state_update events
watch(
  () => props.events,
  (events) => {
    const stateEvents = events.filter((e) => e.type === 'state_update')
    if (stateEvents.length > 0) {
      const latest = stateEvents[stateEvents.length - 1]
      if (latest.characters) {
        party.value = latest.characters
      }
      if (latest.location) {
        location.value = latest.location
      }
      if (latest.encounter) {
        encounter.value = latest.encounter
      }
    }
  },
  { deep: true }
)
</script>

<style scoped>
.state-dashboard {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
  overflow-y: auto;
}

.state-dashboard h2 {
  color: #e94560;
  font-size: 1rem;
  margin-bottom: 1rem;
}

.section {
  margin-bottom: 1.5rem;
}

.section h3 {
  font-size: 0.875rem;
  color: #888;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.empty {
  color: #666;
  font-size: 0.875rem;
  font-style: italic;
}

.location {
  color: #eee;
}

.encounter {
  background: #1a1a2e;
  padding: 0.75rem;
  border-radius: 4px;
}

.enemy {
  padding: 0.25rem 0;
  color: #e94560;
}

.status {
  color: #888;
  font-style: italic;
}
</style>
