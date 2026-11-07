export async function request(path, body) {
  const options = body === undefined
    ? { credentials: 'same-origin', cache: 'no-store' }
    : { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
  const response = await fetch(path, options)
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '요청을 처리하지 못했습니다.')
  return data
}

export function safeSourceUrl(value) {
  if (!value) return null
  try {
    const url = new URL(value, window.location.origin)
    return url.origin === window.location.origin || url.protocol === 'https:' ? url.href : null
  } catch {
    return null
  }
}
