<template>
  <div class="app">
    <ControlBar
      :ws-connected="wsConnected"
      :game-status="gameStatus"
      @start="startGame"
      @stop="stopGame"
    />

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
        <NarrativeFeed :events="events" />
        <StateDashboard :events="events" />
      </div>

      <EntityInspector v-else />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import ControlBar from './components/ControlBar.vue'
import NarrativeFeed from './components/NarrativeFeed.vue'
import StateDashboard from './components/StateDashboard.vue'
import EntityInspector from './components/EntityInspector.vue'

const activeTab = ref('live')
const wsConnected = ref(false)
const gameStatus = ref('stopped')
const events = ref([])

let ws = null

function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
    ws.send(JSON.stringify({ type: 'ping' }))
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'pong') return

    events.value.push(data)
    if (events.value.length > 100) {
      events.value.shift()
    }

    // Update game status from session events
    if (data.type === 'session_start') {
      gameStatus.value = 'running'
    } else if (data.type === 'session_end') {
      gameStatus.value = 'stopped'
    }
  }

  ws.onclose = () => {
    wsConnected.value = false
    setTimeout(connect, 2000)
  }

  ws.onerror = () => ws.close()
}

async function startGame(campaignId) {
  try {
    const res = await fetch(`/api/campaigns/${campaignId}/start`, {
      method: 'POST',
    })
    if (res.ok) {
      gameStatus.value = 'running'
    }
  } catch (err) {
    console.error('Failed to start game:', err)
  }
}

async function stopGame(mode) {
  try {
    gameStatus.value = 'stopping'
    const res = await fetch(`/api/campaigns/current/stop?mode=${mode}`, {
      method: 'POST',
    })
    if (res.ok) {
      gameStatus.value = 'stopped'
    }
  } catch (err) {
    console.error('Failed to stop game:', err)
    gameStatus.value = 'running'
  }
}

onMounted(connect)
onUnmounted(() => ws?.close())
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  background: #16213e;
}

.tabs button {
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tabs button:hover {
  color: #ccc;
}

.tabs button.active {
  color: #e94560;
  border-bottom-color: #e94560;
}

.content {
  flex: 1;
  padding: 1rem;
  overflow: hidden;
}

.live-view {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  height: calc(100vh - 140px);
}
</style>
