<template>
  <div class="page">
    <StepIndicator :current="4" />
    <div class="content">
      <h1>预览 & 导出</h1>
      <p class="subtitle">你的短剧剧本已生成完毕</p>

      <div v-if="store.meta" class="summary-card">
        <div class="summary-title">{{ store.meta.title }}</div>
        <div class="summary-stats">
          <span>{{ store.meta.episodes }} 集</span>
          <span>{{ store.characters.length }} 个角色</span>
          <span>{{ totalScenes }} 个场景</span>
        </div>
      </div>

      <SceneStream :scenes="store.scenes" :streaming="false" />

      <div class="export-section">
        <ExportPanel />
        <button class="video-btn" @click="generateVideo" :disabled="videoLoading">
          {{ videoLoading ? `生成中 ${videoProgress}%` : '生成视频' }}
        </button>
        <button class="restart-btn" @click="restart">重新创作</button>
      </div>

      <div v-if="videoStatus" class="video-status">
        <div class="status-bar">
          <div class="status-fill" :style="{ width: videoProgress + '%' }"></div>
        </div>
        <p class="status-text">{{ videoStatus }}</p>
        <p v-if="videoError" class="status-error">{{ videoError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import StepIndicator from '../components/StepIndicator.vue'
import SceneStream from '../components/SceneStream.vue'
import ExportPanel from '../components/ExportPanel.vue'
import { useStoryStore } from '../stores/story.js'
import { useSettingsStore } from '../stores/settings.js'
import { finalizeScript, startStoryboard, getPipelineStatus } from '../api/story.js'

const router = useRouter()
const store = useStoryStore()
const settings = useSettingsStore()

const videoLoading = ref(false)
const videoProgress = ref(0)
const videoStatus = ref('')
const videoError = ref('')
let pollTimer = null

onMounted(() => {
  if (!store.meta || !store.scenes.length) router.replace('/step1')
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const totalScenes = computed(() =>
  store.scenes.reduce((sum, s) => sum + s.scenes.length, 0)
)

async function generateVideo() {
  videoLoading.value = true
  videoError.value = ''
  videoStatus.value = '正在序列化剧本...'
  videoProgress.value = 5

  try {
    const { script } = await finalizeScript(store.storyId)
    videoStatus.value = '正在解析分镜...'
    videoProgress.value = 10
    await startStoryboard(store.storyId, script, settings.provider || 'qwen')
    videoStatus.value = '分镜解析完成，等待后续处理...'
    videoProgress.value = 30

    pollTimer = setInterval(async () => {
      try {
        const s = await getPipelineStatus(store.storyId)
        videoProgress.value = s.progress
        videoStatus.value = s.current_step
        if (s.status === 'complete') {
          clearInterval(pollTimer)
          videoLoading.value = false
        } else if (s.status === 'failed') {
          clearInterval(pollTimer)
          videoLoading.value = false
          videoError.value = s.error || '生成失败'
        }
      } catch (e) {
        clearInterval(pollTimer)
        videoLoading.value = false
        videoError.value = e.message
      }
    }, 2000)
  } catch (e) {
    videoLoading.value = false
    videoError.value = e.message
    videoStatus.value = ''
  }
}

function restart() {
  store.$reset()
  router.push('/step1')
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f5f5f7; padding: 32px 16px; }
.content { max-width: 600px; margin: 32px auto 0; }
h1 { font-size: 26px; font-weight: 700; margin-bottom: 6px; }
.subtitle { color: #888; margin-bottom: 24px; }
.summary-card {
  background: linear-gradient(135deg, #6c63ff, #a78bfa);
  color: #fff;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
}
.summary-title { font-size: 20px; font-weight: 700; margin-bottom: 12px; }
.summary-stats { display: flex; gap: 16px; }
.summary-stats span {
  background: rgba(255,255,255,0.2);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
}
.export-section {
  display: flex;
  gap: 12px;
  margin-top: 28px;
  align-items: center;
}
.video-btn {
  padding: 12px 20px;
  background: #6c63ff;
  color: #fff;
  border-radius: 10px;
  font-size: 14px;
  border: none;
  cursor: pointer;
}
.video-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.video-btn:not(:disabled):hover { background: #5a52e0; }
.restart-btn {
  padding: 12px 20px;
  background: #fff;
  color: #555;
  border-radius: 10px;
  font-size: 14px;
  border: 2px solid #e0e0e0;
}
.restart-btn:hover { border-color: #6c63ff; color: #6c63ff; }
.video-status { margin-top: 20px; }
.status-bar {
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}
.status-fill {
  height: 100%;
  background: #6c63ff;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.status-text { font-size: 13px; color: #666; }
.status-error { font-size: 13px; color: #e53935; margin-top: 4px; }
</style>
