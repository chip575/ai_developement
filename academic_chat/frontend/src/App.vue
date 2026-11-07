<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { ArrowRight, ArrowUp, BookOpen, ChevronRight, CircleHelp, GraduationCap, LogIn, LogOut, Plus, Search, Sparkles, X } from 'lucide-vue-next'
import { request, safeSourceUrl } from './api'
import { renderMarkdown } from './markdown'

const user = ref(null)
const view = ref('loading')
const messages = ref([])
const message = ref('')
const search = ref('')
const busy = ref(false)
const loginOpen = ref(false)
const loggingIn = ref(false)
const loginError = ref('')
const connectionError = ref('')
const username = ref('student')
const password = ref('demo1234')
const chatBottom = ref(null)
const input = ref(null)
let version = 0

const suggestions = [
  { label: '졸업 요건', description: '경영학과 졸업 기준이 궁금해요', question: '경영학과 졸업학점은 몇 학점인가요?' },
  { label: '휴학 · 복학', description: '휴학 절차를 알려주세요', question: '휴학 절차 알려줘' },
  { label: '나의 이수 내역', description: '내가 들은 과목을 확인해요', question: '내 이수 과목과 학점 알려줘' },
  { label: '나의 졸업요건', description: '남은 학점과 과목을 확인해요', question: '내 졸업요건 확인해줘' },
]
const visibleSuggestions = computed(() => {
  const query = search.value.trim().toLowerCase()
  return query ? suggestions.filter(item => `${item.label} ${item.description}`.toLowerCase().includes(query)) : suggestions
})

function clearChat() {
  version += 1
  busy.value = false
  messages.value = []
  message.value = ''
}

function enterChat() {
  clearChat()
  view.value = 'chat'
  nextTick(() => input.value?.focus())
}

function showEntry() {
  clearChat()
  view.value = 'entry'
}

async function checkSession() {
  view.value = 'loading'
  connectionError.value = ''
  try {
    const result = await request('/api/session')
    user.value = result.user
    if (result.user) enterChat()
    else showEntry()
  } catch {
    view.value = 'error'
    connectionError.value = '서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해 주세요.'
  }
}

function openLogin() {
  loginError.value = ''
  loginOpen.value = true
}

async function login() {
  if (loggingIn.value) return
  loggingIn.value = true
  loginError.value = ''
  try {
    const result = await request('/api/login', { username: username.value, password: password.value })
    user.value = result.user
    loginOpen.value = false
    enterChat()
  } catch (error) {
    loginError.value = error.message
  } finally {
    loggingIn.value = false
  }
}

async function logout() {
  try {
    await request('/api/logout', {})
    user.value = null
    showEntry()
  } catch (error) {
    connectionError.value = error.message
  }
}

async function scrollToBottom() {
  await nextTick()
  chatBottom.value?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
}

function addMessage(role, text, extra = {}) {
  messages.value.push({ role, text, ...extra })
  scrollToBottom()
}

async function send(value = message.value) {
  const question = value.trim()
  if (!question || busy.value || view.value !== 'chat') return
  const initialVersion = version
  let activeVersion = initialVersion
  busy.value = true
  connectionError.value = ''
  try {
    const session = await request('/api/session')
    if (initialVersion !== version) return
    if (JSON.stringify(session.user) !== JSON.stringify(user.value)) {
      user.value = session.user
      clearChat()
      addMessage('assistant', '로그인 상태가 변경되어 새 대화를 시작합니다.')
    }
    activeVersion = version
    const previous = messages.value.at(-1)
    const previousQuestion = messages.value.at(-2)
    const apiQuestion = previous?.route === 'weather_location_required' && previousQuestion?.role === 'user' && /^[가-힣A-Za-z\s]{1,20}$/.test(question)
      ? `${previousQuestion.text} ${question}` : question
    addMessage('user', question)
    message.value = ''
    const result = await request('/api/chat', { message: apiQuestion })
    if (activeVersion !== version) return
    if (JSON.stringify(result.user) !== JSON.stringify(user.value)) {
      user.value = result.user
      clearChat()
      addMessage('assistant', '로그인 상태가 변경되었습니다. 질문을 다시 입력해 주세요.')
      return
    }
    addMessage('assistant', result.answer, { sources: result.sources || [], loginRequired: result.login_required, route: result.route, sql: result.sql })
  } catch (error) {
    if (activeVersion === version) addMessage('assistant', `요청을 처리하지 못했어요. ${error.message}`)
  } finally {
    if (activeVersion === version) {
      busy.value = false
      if (view.value === 'chat') nextTick(() => input.value?.focus())
    }
  }
}

function onComposerKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}

onMounted(checkSession)
</script>

<template>
  <div class="app-shell" @keydown.esc="loginOpen = false">
    <aside class="rail" aria-label="주 메뉴">
      <div class="university-mark" aria-label="PNU 도우미">PNU</div>
      <div class="rail-current" aria-current="page"><Sparkles :size="26" /><span>학사 AI</span></div>
    </aside>

    <aside class="sidebar" aria-label="학사 메뉴">
      <div class="sidebar-top">
        <label class="search-box"><Search :size="18" aria-hidden="true" /><span class="sr-only">학사 메뉴 검색</span><input v-model="search" placeholder="학사 메뉴 검색" /></label>
        <div class="sidebar-heading">학사 도우미</div>
        <button class="assistant-active" type="button" @click="view === 'chat' && clearChat()"><span class="avatar mini">✦</span><span>PNU 도우미</span></button>
        <div class="quick-heading"><span>추천 질문</span><button v-if="view === 'chat'" type="button" aria-label="새 대화" @click="clearChat"><Plus :size="16" /></button></div>
        <div class="side-suggestions">
          <button v-for="item in visibleSuggestions" :key="item.label" type="button" :disabled="view !== 'chat' || busy" @click="send(item.question)">{{ item.label }}<ChevronRight :size="14" /></button>
          <p v-if="!visibleSuggestions.length">일치하는 메뉴가 없습니다.</p>
        </div>
      </div>
      <div class="sidebar-bottom">
        <div v-if="user" class="account-info"><span class="account-avatar">{{ user.name?.slice(0, 1) }}</span><span><strong>{{ user.name }}님</strong><small>{{ user.department }} · 데모 계정</small></span></div>
        <div v-else class="account-caption"><CircleHelp :size="16" /><span>로그인하면 내 학사 정보를 볼 수 있어요</span></div>
        <button v-if="user" class="account-button" type="button" @click="logout"><LogOut :size="17" /> 로그아웃</button>
        <button v-else class="account-button" type="button" @click="openLogin"><LogIn :size="17" /> 로그인</button>
      </div>
    </aside>

    <main class="main-area">
      <header class="topbar"><div class="topbar-title"><span class="avatar small">✦</span><span>PNU 도우미</span></div><div class="header-actions"><span class="header-status">{{ user ? `${user.name}님 · 학생` : '일반 학사 안내' }}</span><button class="mobile-account" type="button" @click="user ? logout() : openLogin()">{{ user ? '로그아웃' : '로그인' }}</button></div></header>

      <section v-if="view === 'loading'" class="state-view" aria-live="polite">로그인 상태를 확인하고 있습니다.</section>
      <section v-else-if="view === 'error'" class="state-view"><p role="alert">{{ connectionError }}</p><button class="retry-button" type="button" @click="checkSession">다시 시도</button></section>

      <section v-else-if="view === 'entry'" class="entry-view">
        <div class="entry-card">
          <span class="avatar large">✦</span>
          <p class="eyebrow">PNU 학사 도우미</p>
          <h1>어떻게 시작할까요?</h1>
          <p>로그인 없이 학사 정보를 확인하거나,<br />로그인하고 나에게 맞는 안내를 받아보세요.</p>
          <div class="entry-actions">
            <button type="button" @click="enterChat"><BookOpen :size="21" /><span><strong>일반 학사 안내로 시작</strong><small>로그인 없이 학사 규정과 공지를 확인해요.</small></span><ArrowRight :size="18" /></button>
            <button type="button" @click="openLogin"><GraduationCap :size="22" /><span><strong>로그인하고 시작</strong><small>나의 이수 내역과 졸업요건을 확인해요.</small></span><ArrowRight :size="18" /></button>
          </div>
          <div class="entry-foot">데모 환경입니다. 학생 정보는 가상 데이터입니다.</div>
        </div>
      </section>

      <template v-else>
        <section class="chat-scroll" aria-label="학사 대화">
          <div class="chat-content">
            <div v-if="!messages.length" class="hero">
              <div><span class="hero-tag"><Sparkles :size="14" /> PNU ACADEMIC ASSISTANT</span><h1>PNU 도우미</h1><p>부산대학교에 대해 알고 싶은 게 있으신가요? 무엇이든 물어보세요.</p></div>
              <div class="hero-art" aria-hidden="true"><span>✦</span><span>✧</span></div>
            </div>
            <div class="assistant-intro"><span class="avatar">✦</span><strong>PNU 도우미</strong></div>
            <p class="intro-text">안녕하세요. 부산대학교 학사 정보가 궁금하신가요?</p>
            <div v-if="!messages.length" class="quick-prompts"><button v-for="item in suggestions" :key="item.label" type="button" :disabled="busy" @click="send(item.question)">{{ item.label }} <ArrowRight :size="14" /></button></div>
            <div class="messages" aria-live="polite">
              <article v-for="(item, index) in messages" :key="index" :class="['message', item.role]">
                <span class="message-avatar" :class="{ avatar: item.role === 'assistant' }">{{ item.role === 'assistant' ? '✦' : '나' }}</span>
                <div class="message-content"><strong>{{ item.role === 'assistant' ? 'PNU 도우미' : '나' }}</strong><div v-if="item.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(item.text)"></div><p v-else>{{ item.text }}</p>
                  <details v-if="item.sql" class="sql-details"><summary>생성된 SQL 보기</summary><p>본인 데이터만 담은 읽기 전용 임시 테이블에 실행한 SQLite SQL입니다.</p><pre><code>{{ item.sql }}</code></pre></details>
                  <div v-if="item.sources?.length" class="sources"><span>참고 자료</span><template v-for="(source, sourceIndex) in item.sources" :key="sourceIndex"><a v-if="safeSourceUrl(source.url)" :href="safeSourceUrl(source.url)" target="_blank" rel="noopener noreferrer">{{ source.title }} ↗</a><span v-else>{{ source.title }}</span></template></div>
                  <button v-if="item.loginRequired" class="login-inline" type="button" @click="openLogin">로그인하고 확인하기 <ArrowRight :size="14" /></button>
                </div>
              </article>
              <div v-if="busy" class="typing" role="status"><span class="avatar mini">✦</span> 답변을 확인하고 있어요<span class="dots">···</span></div>
              <div ref="chatBottom"></div>
            </div>
          </div>
        </section>
        <div class="composer-area"><form class="composer" @submit.prevent="send()"><label class="sr-only" for="question">질문 입력</label><textarea id="question" ref="input" v-model="message" rows="1" maxlength="500" placeholder="궁금한 것을 물어보세요" @keydown="onComposerKeydown"></textarea><button type="submit" :disabled="busy || !message.trim()" aria-label="질문 보내기"><ArrowUp :size="21" /></button></form><p>일반 질문은 AI 모델과 외부 검색 서비스에 전송될 수 있습니다. 민감한 정보는 입력하지 마세요.</p></div>
      </template>
      <p v-if="connectionError && view === 'chat'" class="connection-error" role="alert">{{ connectionError }}</p>
    </main>

    <div v-if="loginOpen" class="modal-backdrop" @click.self="loginOpen = false">
      <section class="modal" role="dialog" aria-modal="true" aria-labelledby="login-title">
        <div class="modal-head"><span class="avatar">✦</span><button type="button" aria-label="닫기" @click="loginOpen = false"><X :size="20" /></button></div>
        <h2 id="login-title">학생 로그인</h2><p>데모 계정으로 개인 학사 정보를 확인해요.</p>
        <form @submit.prevent="login"><label for="username">아이디</label><input id="username" v-model="username" autocomplete="username" required /><label for="password">비밀번호</label><input id="password" v-model="password" type="password" autocomplete="current-password" required />
          <div class="demo-box">데모 계정 <strong>student</strong> / <strong>demo1234</strong><br />두 번째 계정 <strong>student2</strong> / <strong>demo1234</strong></div>
          <p v-if="loginError" class="login-error" role="alert">{{ loginError }}</p><button class="submit-login" type="submit" :disabled="loggingIn">{{ loggingIn ? '로그인 중...' : '로그인' }}</button>
        </form><small class="modal-foot">실제 학교 계정이 아닌 체험용 계정입니다.</small>
      </section>
    </div>
  </div>
</template>
