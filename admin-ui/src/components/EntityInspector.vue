<template>
  <section class="entity-inspector">
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Enter UID (e.g., pc_throk_001)"
        @keyup.enter="searchEntity"
      />
      <button @click="searchEntity" :disabled="!searchQuery">Search</button>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="entity" class="results">
      <div class="panel document">
        <h3>Document (SQLite)</h3>
        <pre>{{ JSON.stringify(entity, null, 2) }}</pre>
      </div>

      <div class="panel relationships">
        <h3>Relationships (Neo4j)</h3>
        <div v-if="relationships.length" class="rel-list">
          <div
            v-for="rel in relationships"
            :key="rel.target"
            class="relationship"
            @click="loadEntity(rel.target)"
          >
            <span class="rel-type">{{ rel.type }}</span>
            <span class="rel-arrow">→</span>
            <span class="rel-target">{{ rel.target }}</span>
          </div>
        </div>
        <p v-else class="empty">No relationships found</p>
      </div>
    </div>

    <div v-else class="placeholder">
      <p>Enter a UID to inspect an entity</p>
      <p class="hint">Examples: pc_throk_001, npc_goblin_003, loc_caves_room_02</p>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const searchQuery = ref('')
const entity = ref(null)
const relationships = ref([])
const loading = ref(false)
const error = ref('')

async function searchEntity() {
  if (!searchQuery.value) return
  await loadEntity(searchQuery.value)
}

async function loadEntity(uid) {
  loading.value = true
  error.value = ''
  entity.value = null
  relationships.value = []
  searchQuery.value = uid

  try {
    // Fetch entity document
    const entityRes = await fetch(`/api/entity/${uid}`)
    if (!entityRes.ok) {
      if (entityRes.status === 404) {
        error.value = `Entity "${uid}" not found`
      } else {
        error.value = `Failed to load entity: ${entityRes.statusText}`
      }
      return
    }
    entity.value = await entityRes.json()

    // Fetch relationships
    try {
      const relRes = await fetch(`/api/entity/${uid}/relationships`)
      if (relRes.ok) {
        const relData = await relRes.json()
        relationships.value = relData.relationships || []
      }
    } catch {
      // Relationships are optional (Neo4j might not be configured)
    }
  } catch (err) {
    error.value = `Error: ${err.message}`
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.entity-inspector {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.search-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.search-bar input {
  flex: 1;
  padding: 0.75rem 1rem;
  background: #1a1a2e;
  border: 1px solid #0f3460;
  border-radius: 4px;
  color: #eee;
  font-family: monospace;
}

.search-bar input:focus {
  outline: none;
  border-color: #e94560;
}

.search-bar button {
  padding: 0.75rem 1.5rem;
  background: #e94560;
  border: none;
  border-radius: 4px;
  color: white;
  font-weight: bold;
  cursor: pointer;
}

.search-bar button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #888;
}

.error {
  padding: 1rem;
  background: #b71c1c;
  border-radius: 4px;
  color: white;
}

.results {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  flex: 1;
  overflow: hidden;
}

.panel {
  background: #1a1a2e;
  border-radius: 4px;
  padding: 1rem;
  overflow: auto;
}

.panel h3 {
  color: #888;
  font-size: 0.75rem;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.panel pre {
  font-family: monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.rel-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.relationship {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #0f3460;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.relationship:hover {
  background: #1a4a7a;
}

.rel-type {
  color: #e94560;
  font-weight: bold;
}

.rel-arrow {
  color: #666;
}

.rel-target {
  color: #2196f3;
  font-family: monospace;
}

.placeholder {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.5rem;
  font-family: monospace;
}

.empty {
  color: #666;
  font-style: italic;
}
</style>
