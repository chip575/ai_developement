import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const parser = new MarkdownIt({ html: false, linkify: true, breaks: true })

export function renderMarkdown(text) {
  return DOMPurify.sanitize(parser.render(String(text || '')))
}
