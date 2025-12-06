<template>
  <section class="narrative-feed">
    <div class="header">
      <h2>Narrative Feed</h2>
      <label class="auto-scroll">
        <input type="checkbox" v-model="autoScroll" />
        Auto-scroll
      </label>
    </div>

    <div ref="feedContainer" class="feed">
      <div
        v-for="(event, index) in events"
        :key="index"
        :class="['event', event.type]"
      >
        <div class="event-header">
          <span class="source">{{ formatSource(event.source) }}</span>
          <span class="timestamp">{{ formatTime(event.timestamp) }}</span>
        </div>
        <div class="content">{{ event.content }}</div>
        <div v-if="event.metadata && Object.keys(event.metadata).length" class="metadata">
          {{ JSON.stringify(event.metadata) }}
        </div>
      </div>

      <div v-if="events.length === 0" class="empty">
        <p>Waiting for events...</p>
        <p class="hint">Start a campaign to see the narrative unfold.</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

const autoScroll = ref(true)
const feedContainer = ref(null)

function formatSource(source) {
  if (source === 'dm') return 'DM'
  if (source === 'system') return 'System'
  // Capitalize first letter of player names
  return source.charAt(0).toUpperCase() + source.slice(1)
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

watch(
  () => props.events.length,
  async () => {
    if (autoScroll.value && feedContainer.value) {
      await nextTick()
      feedContainer.value.scrollTop = feedContainer.value.scrollHeight
    }
  }
)
</script>

<style scoped>
.narrative-feed {
  background: #16213e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #0f3460;
}

.header h2 {
  color: #e94560;
  font-size: 1rem;
}

.auto-scroll {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #888;
  cursor: pointer;
}

.feed {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.event {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: #1a1a2e;
  border-radius: 4px;
  border-left: 3px solid #666;
}

.event.narration {
  border-left-color: #4caf50;
}

.event.player_action {
  border-left-color: #2196f3;
}

.event.dice_roll {
  border-left-color: #ff9800;
}

.event.combat {
  border-left-color: #e94560;
}

.event.system,
.event.session_start,
.event.session_end {
  border-left-color: #9c27b0;
  font-style: italic;
}

.event-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.source {
  font-weight: bold;
  color: #e94560;
}

.event.narration .source {
  color: #4caf50;
}

.event.player_action .source {
  color: #2196f3;
}

.timestamp {
  font-size: 0.75rem;
  color: #666;
}

.content {
  line-height: 1.5;
}

.metadata {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #0f3460;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.75rem;
  color: #888;
}

.empty {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.5rem;
}
</style>
