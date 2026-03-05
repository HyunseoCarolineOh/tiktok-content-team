import { useState } from 'react'
import { Save } from 'lucide-react'
import { saveScript } from '../api/client'

interface Props {
  date: string
  filename: string
  initialContent: string
  onSaved?: () => void
}

export default function ScriptEditor({ date, filename, initialContent, onSaved }: Props) {
  const [content, setContent] = useState(initialContent)
  const [saving, setSaving] = useState(false)
  const [savedMsg, setSavedMsg] = useState('')

  const handleSave = async () => {
    setSaving(true)
    try {
      await saveScript(date, filename, content)
      setSavedMsg('저장됨')
      onSaved?.()
      setTimeout(() => setSavedMsg(''), 2000)
    } catch {
      setSavedMsg('저장 실패')
    } finally {
      setSaving(false)
    }
  }

  // 섹션 파싱: ## 후크 A / ## 후크 B / ## 본문 / ## CTA
  const sections = parseSections(content)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400 font-mono">{filename}</span>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-red hover:bg-red-600 disabled:opacity-50 rounded text-sm text-white transition-colors"
        >
          <Save size={14} />
          {saving ? '저장 중...' : savedMsg || '저장'}
        </button>
      </div>

      {/* 섹션별 에디터 */}
      {sections.map((section) => (
        <div key={section.header}>
          <label className="block text-xs font-semibold text-yellow-400 mb-1">{section.header}</label>
          <textarea
            value={section.body}
            onChange={(e) => {
              const updated = updateSection(content, section.header, e.target.value)
              setContent(updated)
            }}
            rows={section.header === '본문' ? 6 : 3}
            className="w-full bg-gray-800 border border-gray-600 rounded p-3 text-sm text-gray-100 font-mono resize-y focus:outline-none focus:border-brand-red"
          />
        </div>
      ))}

      {/* 원본 전체 보기 */}
      <details className="mt-2">
        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">원본 텍스트 편집</summary>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={20}
          className="mt-2 w-full bg-gray-900 border border-gray-700 rounded p-3 text-xs text-gray-300 font-mono resize-y focus:outline-none"
        />
      </details>
    </div>
  )
}

interface Section {
  header: string
  body: string
}

function parseSections(content: string): Section[] {
  const headers = ['후크 A', '후크 B', '본문', 'CTA']
  const sections: Section[] = []

  for (const header of headers) {
    const regex = new RegExp(`##\\s*${header}\\s*\\n([\\s\\S]*?)(?=\\n##|$)`, 'i')
    const match = content.match(regex)
    sections.push({ header, body: match ? match[1].trim() : '' })
  }

  return sections
}

function updateSection(content: string, header: string, newBody: string): string {
  const regex = new RegExp(`(##\\s*${header}\\s*\\n)[\\s\\S]*?(?=\\n##|$)`, 'i')
  if (regex.test(content)) {
    return content.replace(regex, `$1${newBody}\n`)
  }
  // 섹션이 없으면 끝에 추가
  return content + `\n## ${header}\n${newBody}\n`
}
