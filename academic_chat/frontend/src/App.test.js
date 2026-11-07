import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from './App.vue'
import { request } from './api'

vi.mock('./api', async (original) => ({ ...(await original()), request: vi.fn() }))

const student = { id: 1, name: '김민준', department: '경영학과' }
let wrapper
function button(text) {
  const found = wrapper.findAll('button').find(item => item.text().includes(text))
  expect(found, `button ${text}`).toBeTruthy()
  return found
}

beforeEach(() => { request.mockReset() })
afterEach(() => wrapper?.unmount())

describe('학사 도우미 사용자 흐름', () => {
  it('조회 결과와 생성된 SQL을 접어서 보여준다', async () => {
    request.mockImplementation(async path => path === '/api/session'
      ? { user: student }
      : { user: student, answer: '| 이름 |\n| --- |\n| 김민준 |', sql: 'SELECT name FROM student_profile' })
    wrapper = mount(App)
    await flushPromises()
    await wrapper.find('#question').setValue('내 개인 정보 알려줘')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.sql-details summary').text()).toContain('SQL')
    expect(wrapper.find('.sql-details code').text()).toBe('SELECT name FROM student_profile')
    expect(wrapper.find('.sql-details').attributes('open')).toBeUndefined()
  })
  it('일반 대화 중 로그인한 뒤 같은 질문을 본인 세션으로 보낸다', async () => {
    let currentUser = null
    request.mockImplementation(async (path, body) => {
      if (path === '/api/session') return { user: currentUser }
      if (path === '/api/login') { currentUser = student; return { user: student } }
      if (body.message === '지금 내가 들은 것은?') return currentUser
        ? { user: student, answer: '김민준님의 이수 내역입니다.' }
        : { user: null, answer: '로그인이 필요합니다.', login_required: true }
      return { user: null, answer: '공개 학사 안내' }
    })
    wrapper = mount(App)
    await flushPromises()
    await button('일반 학사 안내로 시작').trigger('click')
    await wrapper.find('#question').setValue('경영학과 졸업학점은 몇 학점인가요?')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    await wrapper.find('#question').setValue('지금 내가 들은 것은?')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    await button('로그인하고 확인하기').trigger('click')
    await wrapper.find('.modal form').trigger('submit')
    await flushPromises()
    await wrapper.find('#question').setValue('지금 내가 들은 것은?')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('김민준님의 이수 내역입니다.')
    expect(wrapper.text()).not.toContain('로그인이 필요합니다.')
  })

  it('대기 중 로그인한 뒤 이전 요청이 새 질문을 막거나 결과를 덮지 않는다', async () => {
    let currentUser = null
    let resolveOld
    request.mockImplementation((path) => {
      if (path === '/api/session') return Promise.resolve({ user: currentUser })
      if (path === '/api/login') { currentUser = student; return Promise.resolve({ user: student }) }
      if (!currentUser) return new Promise(resolve => { resolveOld = resolve })
      return Promise.resolve({ user: student, answer: '새 계정의 결과' })
    })
    wrapper = mount(App)
    await flushPromises()
    await button('일반 학사 안내로 시작').trigger('click')
    await wrapper.find('#question').setValue('공개 질문')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    await wrapper.find('.sidebar-bottom .account-button').trigger('click')
    await wrapper.find('.modal form').trigger('submit')
    await flushPromises()
    await wrapper.find('#question').setValue('지금 내가 들은 것은?')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    resolveOld({ user: null, answer: '이전 사용자 결과' })
    await flushPromises()
    expect(wrapper.text()).toContain('새 계정의 결과')
    expect(wrapper.text()).not.toContain('이전 사용자 결과')
  })
  it('답변의 Markdown을 읽기 쉽게 표시하고 위험한 HTML은 실행하지 않는다', async () => {
    request.mockImplementation(async path => path === '/api/session'
      ? { user: null }
      : { user: null, answer: '**졸업**\n\n- 학점\n- 과목\n\n| 항목 | 기준 |\n|---|---|\n| 학점 | 126 |\n\n<img src=x onerror=alert(1)>\n[위험](javascript:alert(1))' })
    wrapper = mount(App)
    await flushPromises()
    await button('일반 학사 안내로 시작').trigger('click')
    await wrapper.find('#question').setValue('졸업 기준')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    const answer = wrapper.find('.message.assistant .markdown-body')
    expect(answer.find('strong').text()).toBe('졸업')
    expect(answer.findAll('li')).toHaveLength(2)
    expect(answer.find('table').text()).toContain('126')
    expect(answer.find('img').exists()).toBe(false)
    expect(answer.find('a[href^="javascript:"]').exists()).toBe(false)
  })
  it('날씨의 지역을 답하면 앞선 질문과 함께 검색한다', async () => {
    request.mockImplementation(async (path, body) => {
      if (path === '/api/session') return { user: null }
      if (body.message === '오늘 날씨 알려줘') return { user: null, answer: '어느 지역인가요?', route: 'weather_location_required' }
      return { user: null, answer: '검색 결과', route: 'web_search' }
    })
    wrapper = mount(App)
    await flushPromises()
    await button('일반 학사 안내로 시작').trigger('click')
    await wrapper.find('#question').setValue('오늘 날씨 알려줘')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    await wrapper.find('#question').setValue('부산')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    expect(request).toHaveBeenCalledWith('/api/chat', { message: '오늘 날씨 알려줘 부산' })
    expect(wrapper.text()).toContain('검색 결과')
  })
  it('비로그인 사용자가 일반 안내를 검색하고 출처를 확인한다', async () => {
    request.mockImplementation(async path => path === '/api/session'
      ? { user: null }
      : { user: null, answer: '학사 규정 안내', sources: [{ title: '학칙', url: '/api/sources/regulations.pdf' }, { title: '위험한 주소', url: 'javascript:alert(1)' }] })
    wrapper = mount(App)
    await flushPromises()
    await button('일반 학사 안내로 시작').trigger('click')
    await wrapper.find('#question').setValue('휴학은 어떻게 하나요?')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    expect(request).toHaveBeenCalledWith('/api/chat', { message: '휴학은 어떻게 하나요?' })
    expect(wrapper.text()).toContain('학사 규정 안내')
    expect(wrapper.find('.sources a').attributes('href')).toContain('/api/sources/regulations.pdf')
    expect(wrapper.findAll('.sources a')).toHaveLength(1)
  })

  it('개인 질문에 로그인 안내를 제공하고 로그인 후 이전 대화를 지운다', async () => {
    request.mockImplementation(async path => {
      if (path === '/api/session') return { user: null }
      if (path === '/api/login') return { user: student }
      return { user: null, answer: '로그인이 필요합니다.', login_required: true }
    })
    wrapper = mount(App)
    await flushPromises()
    await button('일반 학사 안내로 시작').trigger('click')
    await wrapper.find('#question').setValue('내 학점 알려줘')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    await button('로그인하고 확인하기').trigger('click')
    await wrapper.find('.modal form').trigger('submit')
    await flushPromises()
    expect(request).toHaveBeenCalledWith('/api/login', { username: 'student', password: 'demo1234' })
    expect(wrapper.text()).toContain('김민준님')
    expect(wrapper.text()).not.toContain('로그인이 필요합니다.')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('기존 로그인 세션으로 시작하고 로그아웃하면 선택 화면으로 돌아간다', async () => {
    request.mockImplementation(async path => path === '/api/session' ? { user: student } : { ok: true })
    wrapper = mount(App)
    await flushPromises()
    expect(wrapper.text()).toContain('김민준님')
    await button('로그아웃').trigger('click')
    await flushPromises()
    expect(request).toHaveBeenCalledWith('/api/logout', {})
    expect(wrapper.text()).toContain('어떻게 시작할까요?')
  })

  it('질문 전 세션이 바뀌면 기존 대화를 지우고 현재 계정으로 요청한다', async () => {
    let sessionCalls = 0
    request.mockImplementation(async path => {
      if (path === '/api/session') return { user: ++sessionCalls === 1 ? student : null }
      return { user: null, answer: '로그인이 필요합니다.', login_required: true }
    })
    wrapper = mount(App)
    await flushPromises()
    await wrapper.find('#question').setValue('내 학점')
    await wrapper.find('.composer').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('로그인 상태가 변경되어 새 대화를 시작합니다.')
    expect(wrapper.text()).toContain('로그인이 필요합니다.')
    expect(wrapper.text()).not.toContain('김민준님')
  })

  it('연결 오류를 안내하고 다시 시도할 수 있다', async () => {
    request.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ user: null })
    wrapper = mount(App)
    await flushPromises()
    expect(wrapper.text()).toContain('서버에 연결할 수 없습니다')
    await button('다시 시도').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('어떻게 시작할까요?')
  })
})
