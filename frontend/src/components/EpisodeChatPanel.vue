<template>
  <div v-if="show" class="overlay" @click="$emit('close')" />
  <div class="panel" :class="{ open: show }">
    <div class="panel-header">
      <span>剧情 AI 修改助手</span>
      <button class="close-btn" @click="$emit('close')">✕</button>
    </div>

    <div v-if="episode" class="episode-info">
      <div class="ep-num">第 {{ episode.episode }} 集</div>
      <div class="ep-title">{{ episode.title }}</div>
    </div>

    <div class="chat-history" ref="historyEl">
      <div v-if="messages.length === 0" class="empty-hint">
        告诉我你想怎么修改这一集，比如：<br>「加入一个意外转折」
      </div>
      <div v-for="(msg, i) in messages" :key="i" :class="['bubble', msg.role]">
        <div class="bubble-text">{{ msg.text }}</div>
      </div>
      <div v-if="streaming" class="bubble ai">
        <div class="bubble-text streaming">{{ streamingDisplayText }}<span class="cursor">|</span></div>
      </div>
    </div>

    <div class="input-area">
      <textarea
        v-model="input"
        placeholder="描述你想修改的内容..."
        rows="3"
        @keydown.enter.exact.prevent="send"
      />
      <button class="send-btn" :disabled="!input.trim() || streaming || applying" @click="send">
        {{ streaming ? '思考中...' : '发送' }}
      </button>
      <button
        class="confirm-btn"
        :disabled="!hasAiReply || streaming || applying"
        @click="confirmApply"
      >
        {{ applying ? '应用中...' : '确认应用' }}
      </button>
    </div>
    <div v-if="error" class="error-tip">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { useStoryStore } from '../stores/story.js'
import { streamChat, applyChatChanges, refineStory } from '../api/story.js'
import { normalizeChatText } from '../utils/storyChat.js'

const props = defineProps({ show: Boolean, episode: Object })
const emit = defineEmits(['close'])

const store = useStoryStore()
const messages = ref([])
const input = ref('')
const streaming = ref(false)
const streamingText = ref('')
const applying = ref(false)
const error = ref('')
const historyEl = ref(null)

const hasAiReply = computed(() => messages.value.some(m => m.role === 'ai'))
const streamingDisplayText = computed(() => normalizeChatText(streamingText.value))

async function scrollToBottom() {
  await nextTick()
  if (historyEl.value) historyEl.value.scrollTop = historyEl.value.scrollHeight
}

watch(() => messages.value.length, scrollToBottom)
watch(streamingText, scrollToBottom)

watch(() => props.episode?.episode, () => {
  messages.value = []
  input.value = ''
  error.value = ''
})

async function send() {
  const text = input.value.trim()
  if (!text || streaming.value || applying.value || !props.episode) return
  input.value = ''
  error.value = ''
  messages.value = [...messages.value, { role: 'user', text }]

  streaming.value = true
  streamingText.value = ''

  await streamChat(
    store.storyId,
    {
      message: text,
      mode: 'episode',
      context: {
        episode: {
          episode: props.episode.episode,
          title: props.episode.title,
          summary: props.episode.summary,
        },
        outline: store.outline,
      },
    },
    (chunk) => { streamingText.value += chunk },
    () => {
      streaming.value = false
      messages.value = [...messages.value, { role: 'ai', text: normalizeChatText(streamingText.value) }]
      streamingText.value = ''
    },
    (msg) => {
      streaming.value = false
      streamingText.value = ''
      error.value = msg || 'AI 响应失败，请重试'
    }
  )
}

async function confirmApply() {
  if (!props.episode || applying.value) return
  applying.value = true
  error.value = ''
  try {
    // 从 store 取最新数据，避免 props 陈旧
    const currentEp = store.outline.find(e => e.episode === props.episode.episode) || props.episode
    const res = await applyChatChanges(
      store.storyId,
      'episode',
      messages.value,
      { episode: currentEp.episode, title: currentEp.title, summary: currentEp.summary },
      null,
      store.outline
    )
    if (!res || (!res.title && !res.summary)) {
      error.value = '未能获取修改结果，请重试'
      return
    }
    const previousTitle = currentEp.title
    const previousSummary = currentEp.summary
    const nextTitle = res.title ?? currentEp.title
    const nextSummary = res.summary ?? currentEp.summary
    store.updateOutlineEpisode(
      currentEp.episode,
      nextTitle,
      nextSummary
    )
    if (nextTitle !== previousTitle || nextSummary !== previousSummary) {
      const refineRes = await refineStory(
        store.storyId,
        'episode',
        `第${currentEp.episode}集标题从「${previousTitle}」改为「${nextTitle}」，剧情从「${previousSummary}」改为「${nextSummary}」`
      )
      if (refineRes) {
        store.applyRefine(refineRes)
      }
    }
    messages.value = []
    input.value = ''
    emit('close')
  } catch {
    error.value = '应用失败，请重试'
  } finally {
    applying.value = false
  }
}
</script>

<style scoped src="../style/components/episodechatpanel.css"></style>
