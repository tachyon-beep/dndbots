<template>
  <header class="control-bar">
    <div class="left">
      <h1>DnDBots Admin</h1>
      <select v-model="selectedCampaign" class="campaign-select">
        <option value="">Select Campaign...</option>
        <option
          v-for="campaign in campaigns"
          :key="campaign.id"
          :value="campaign.id"
        >
          {{ campaign.name }}
        </option>
      </select>
    </div>

    <div class="center">
      <span :class="['status-badge', gameStatus]">
        {{ statusText }}
      </span>
    </div>

    <div class="right">
      <span :class="['ws-indicator', { connected: wsConnected }]"></span>
      <button
        v-if="gameStatus === 'stopped'"
        class="btn btn-start"
        :disabled="!selectedCampaign"
        @click="$emit('start', selectedCampaign)"
      >
        Start
      </button>
      <button
        v-else
        class="btn btn-stop"
        @click="$emit('stop', 'clean')"
      >
        Stop
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  wsConnected: Boolean,
  gameStatus: {
    type: String,
    default: 'stopped', // stopped, running, stopping
  },
})

defineEmits(['start', 'stop'])

const campaigns = ref([])
const selectedCampaign = ref('')

const statusText = computed(() => {
  switch (props.gameStatus) {
    case 'running':
      return '● Running'
    case 'stopping':
      return '◐ Stopping...'
    default:
      return '○ Stopped'
  }
})

async function loadCampaigns() {
  try {
    const response = await fetch('/api/campaigns')
    const data = await response.json()
    campaigns.value = data.campaigns
  } catch (error) {
    console.error('Failed to load campaigns:', error)
  }
}

onMounted(() => {
  loadCampaigns()
})
</script>

<style scoped>
.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.left h1 {
  font-size: 1.25rem;
  color: #e94560;
}

.campaign-select {
  padding: 0.5rem 1rem;
  background: #0f3460;
  border: 1px solid #1a1a2e;
  border-radius: 4px;
  color: #eee;
  cursor: pointer;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: bold;
}

.status-badge.stopped {
  background: #333;
  color: #888;
}

.status-badge.running {
  background: #1b5e20;
  color: #4caf50;
}

.status-badge.stopping {
  background: #e65100;
  color: #ff9800;
}

.ws-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}

.ws-indicator.connected {
  background: #4caf50;
}

.btn {
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-start {
  background: #4caf50;
  color: white;
}

.btn-stop {
  background: #e94560;
  color: white;
}
</style>
