import { useState } from 'react'
import { Save, Plus, X } from 'lucide-react'
import { saveMetadata } from '../api/client'

interface MetadataShape {
  caption?: string
  hashtags?: string[]
  publish_at?: string
  thumbnail_text?: string
  [key: string]: unknown
}

interface Props {
  date: string
  filename: string
  initialData: MetadataShape
  onSaved?: () => void
}

export default function MetadataEditor({ date, filename, initialData, onSaved }: Props) {
  const [data, setData] = useState<MetadataShape>({ ...initialData })
  const [saving, setSaving] = useState(false)
  const [savedMsg, setSavedMsg] = useState('')
  const [newTag, setNewTag] = useState('')

  const handleSave = async () => {
    setSaving(true)
    try {
      await saveMetadata(date, filename, data as Record<string, unknown>)
      setSavedMsg('저장됨')
      onSaved?.()
      setTimeout(() => setSavedMsg(''), 2000)
    } catch {
      setSavedMsg('저장 실패')
    } finally {
      setSaving(false)
    }
  }

  const addHashtag = () => {
    if (!newTag.trim()) return
    const tag = newTag.startsWith('#') ? newTag.trim() : `#${newTag.trim()}`
    setData((prev) => ({ ...prev, hashtags: [...(prev.hashtags ?? []), tag] }))
    setNewTag('')
  }

  const removeHashtag = (index: number) => {
    setData((prev) => ({
      ...prev,
      hashtags: prev.hashtags?.filter((_, i) => i !== index),
    }))
  }

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

      {/* 캡션 */}
      <div>
        <label className="block text-xs font-semibold text-yellow-400 mb-1">캡션</label>
        <textarea
          value={data.caption ?? ''}
          onChange={(e) => setData((p) => ({ ...p, caption: e.target.value }))}
          rows={4}
          className="w-full bg-gray-800 border border-gray-600 rounded p-3 text-sm text-gray-100 resize-y focus:outline-none focus:border-brand-red"
        />
      </div>

      {/* 썸네일 텍스트 */}
      <div>
        <label className="block text-xs font-semibold text-yellow-400 mb-1">썸네일 텍스트</label>
        <input
          type="text"
          value={data.thumbnail_text ?? ''}
          onChange={(e) => setData((p) => ({ ...p, thumbnail_text: e.target.value }))}
          className="w-full bg-gray-800 border border-gray-600 rounded p-3 text-sm text-gray-100 focus:outline-none focus:border-brand-red"
        />
      </div>

      {/* 발행 시간 */}
      <div>
        <label className="block text-xs font-semibold text-yellow-400 mb-1">발행 시간</label>
        <input
          type="datetime-local"
          value={data.publish_at ? data.publish_at.slice(0, 16) : ''}
          onChange={(e) =>
            setData((p) => ({ ...p, publish_at: e.target.value + ':00+09:00' }))
          }
          className="w-full bg-gray-800 border border-gray-600 rounded p-3 text-sm text-gray-100 focus:outline-none focus:border-brand-red"
        />
      </div>

      {/* 해시태그 */}
      <div>
        <label className="block text-xs font-semibold text-yellow-400 mb-2">
          해시태그 ({data.hashtags?.length ?? 0}/30)
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {(data.hashtags ?? []).map((tag, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 px-2 py-1 bg-gray-700 rounded-full text-xs text-gray-200"
            >
              {tag}
              <button
                onClick={() => removeHashtag(i)}
                className="text-gray-400 hover:text-red-400"
              >
                <X size={10} />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addHashtag()}
            placeholder="#해시태그 입력"
            className="flex-1 bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-red"
          />
          <button
            onClick={addHashtag}
            className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-gray-200"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
