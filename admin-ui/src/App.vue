<template>
  <div class="app">
    <header class="control-bar">
      <h1>DnDBots Admin</h1>
      <div class="status">
        <span :class="['indicator', { connected: wsConnected }]"></span>
        {{ wsConnected ? 'Connected' : 'Disconnected' }}
      </div>
    </header>

    <nav class="tabs">
      <button
        :class="{ active: activeTab === 'live' }"
        @click="activeTab = 'live'"
      >
        Live View
      </button>
      <button
        :class="{ active: activeTab === 'inspector' }"
        @click="activeTab = 'inspector'"
      >
        Entity Inspector
      </button>
    </nav>

    <main class="content">
      <div v-if="activeTab === 'live'" class="live-view">
        <section class="narrative-feed">
          <h2>Narrative Feed</h2>
          <div class="feed">
            <div
              v-for="(event, index) in events"
              :key="index"
              :class="['event', event.type]"
            >
              <span class="source">[{{ event.source }}]</span>
              <span class="content">{{ event.content }}</span>
            </div>
            <div v-if="events.length === 0" class="empty">
              Waiting for events...
            </div>
          </div>
        </section>

        <section class="state-dashboard">
          <h2>State Dashboard</h2>
          <p>Coming soon...</p>
        </section>
      </div>

      <div v-else class="entity-inspector">
        <h2>Entity Inspector</h2>
        <p>Coming soon...</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const activeTab = ref('live')
const wsConnected = ref(false)
const events = ref([])

let ws = null

function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
    // Send ping to test connection
    ws.send(JSON.stringify({ type: 'ping' }))
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type !== 'pong') {
      events.value.push(data)
      // Keep last 100 events
      if (events.value.length > 100) {
        events.value.shift()
      }
    }
  }

  ws.onclose = () => {
    wsConnected.value = false
    // Reconnect after 2 seconds
    setTimeout(connect, 2000)
  }

  ws.onerror = () => {
    ws.close()
  }
}

onMounted(() => {
  connect()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.control-bar h1 {
  font-size: 1.5rem;
  color: #e94560;
}

.status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #666;
}

.indicator.connected {
  background: #4caf50;
}

.tabs {
  display: flex;
  gap: 0;
  background: #16213e;
}

.tabs button {
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tabs button.active {
  color: #e94560;
  border-bottom-color: #e94560;
}

.content {
  flex: 1;
  padding: 1rem;
}

.live-view {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  height: calc(100vh - 120px);
}

.narrative-feed,
.state-dashboard {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.narrative-feed h2,
.state-dashboard h2 {
  margin-bottom: 1rem;
  color: #e94560;
}

.feed {
  flex: 1;
  overflow-y: auto;
}

.event {
  padding: 0.5rem;
  border-bottom: 1px solid #0f3460;
}

.event .source {
  color: #e94560;
  font-weight: bold;
  margin-right: 0.5rem;
}

.event.narration .source {
  color: #4caf50;
}

.event.player_action .source {
  color: #2196f3;
}

.empty {
  color: #666;
  font-style: italic;
}

.entity-inspector {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
}

.entity-inspector h2 {
  color: #e94560;
}
</style>
