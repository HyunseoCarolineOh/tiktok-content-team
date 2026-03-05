import { useEffect, useState } from 'react'
import { FileText, Tag } from 'lucide-react'
import ScriptEditor from '../components/ScriptEditor'
import MetadataEditor from '../components/MetadataEditor'
import { getDates, getScripts, getScript, getMetadataList, getMetadata } from '../api/client'

type Tab = 'script' | 'metadata'

export default function ContentReview() {
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [scripts, setScripts] = useState<{ name: string }[]>([])
  const [metadataList, setMetadataList] = useState<{ name: string }[]>([])
  const [selectedFile, setSelectedFile] = useState('')
  const [tab, setTab] = useState<Tab>('script')
  const [scriptContent, setScriptContent] = useState<string | null>(null)
  const [metaContent, setMetaContent] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  // 날짜 목록 로드
  useEffect(() => {
    getDates().then((r) => {
      setDates(r.data.dates)
      if (r.data.dates.length > 0) setSelectedDate(r.data.dates[0])
    })
  }, [])

  // 날짜 변경 시 파일 목록 갱신
  useEffect(() => {
    if (!selectedDate) return
    setSelectedFile('')
    setScriptContent(null)
    setMetaContent(null)

    Promise.all([
      getScripts(selectedDate),
      getMetadataList(selectedDate),
    ]).then(([s, m]) => {
      setScripts(s.data.scripts)
      setMetadataList(m.data.metadata)
    })
  }, [selectedDate])

  // 파일 선택 시 내용 로드
  useEffect(() => {
    if (!selectedFile || !selectedDate) return
    setLoading(true)
    setScriptContent(null)
    setMetaContent(null)

    const scriptName = selectedFile.endsWith('.txt') ? selectedFile : selectedFile.replace('.json', '.txt')
    const metaName = selectedFile.endsWith('.json') ? selectedFile : selectedFile.replace('.txt', '.json')

    Promise.allSettled([
      getScript(selectedDate, scriptName),
      getMetadata(selectedDate, metaName),
    ]).then(([sr, mr]) => {
      if (sr.status === 'fulfilled') setScriptContent(sr.value.data.content)
      if (mr.status === 'fulfilled') setMetaContent(mr.value.data.data)
    }).finally(() => setLoading(false))
  }, [selectedFile, selectedDate])

  const fileBase = selectedFile.replace(/\.(txt|json)$/, '')
  const allFiles = [...new Set([
    ...scripts.map((s) => s.name.replace('.txt', '')),
    ...metadataList.map((m) => m.name.replace('.json', '')),
  ])]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">콘텐츠 검토 & 편집</h1>
        <p className="text-gray-400 mt-1 text-sm">스크립트와 메타데이터를 검토하고 수정하세요.</p>
      </div>

      {/* 날짜 + 파일 선택 */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">날짜</label>
          <select
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none"
          >
            {dates.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">영상</label>
          <select
            value={fileBase}
            onChange={(e) => setSelectedFile(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none"
          >
            <option value="">— 선택 —</option>
            {allFiles.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      </div>

      {/* 탭 */}
      {fileBase && (
        <div>
          <div className="flex gap-2 border-b border-gray-700 mb-4">
            <button
              onClick={() => setTab('script')}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm transition-colors ${tab === 'script' ? 'border-b-2 border-brand-red text-white' : 'text-gray-400 hover:text-gray-200'}`}
            >
              <FileText size={14} />
              스크립트
            </button>
            <button
              onClick={() => setTab('metadata')}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm transition-colors ${tab === 'metadata' ? 'border-b-2 border-brand-red text-white' : 'text-gray-400 hover:text-gray-200'}`}
            >
              <Tag size={14} />
              메타데이터
            </button>
          </div>

          {loading ? (
            <div className="text-gray-400 text-sm animate-pulse">불러오는 중...</div>
          ) : tab === 'script' && scriptContent !== null ? (
            <ScriptEditor
              date={selectedDate}
              filename={`${fileBase}.txt`}
              initialContent={scriptContent}
            />
          ) : tab === 'metadata' && metaContent !== null ? (
            <MetadataEditor
              date={selectedDate}
              filename={`${fileBase}.json`}
              initialData={metaContent}
            />
          ) : (
            <div className="text-gray-500 text-sm italic">파일을 찾을 수 없습니다.</div>
          )}
        </div>
      )}
    </div>
  )
}
