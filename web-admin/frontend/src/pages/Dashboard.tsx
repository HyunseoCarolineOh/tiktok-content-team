import { useEffect, useState } from 'react'
import { BarChart3, FileText, Film, Calendar, TrendingUp } from 'lucide-react'
import { getDates, getDateSummary } from '../api/client'

interface Summary {
  date: string
  has_topics: boolean
  has_schedule: boolean
  scripts_count: number
  metadata_count: number
  raw_videos_count: number
  final_videos_count: number
  has_report: boolean
}

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${ok ? 'bg-green-900/50 text-green-300' : 'bg-gray-800 text-gray-500'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-green-400' : 'bg-gray-600'}`} />
      {label}
    </span>
  )
}

function SummaryCard({ summary }: { summary: Summary }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">{summary.date}</h3>
        <div className="flex gap-1">
          <StatusBadge ok={summary.has_topics} label="리서치" />
          <StatusBadge ok={summary.has_schedule} label="기획" />
          <StatusBadge ok={summary.scripts_count > 0} label="스크립트" />
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-center">
        <div className="bg-gray-900 rounded p-2">
          <div className="text-lg font-bold text-white">{summary.scripts_count}</div>
          <div className="text-xs text-gray-400">스크립트</div>
        </div>
        <div className="bg-gray-900 rounded p-2">
          <div className="text-lg font-bold text-white">{summary.raw_videos_count}</div>
          <div className="text-xs text-gray-400">raw 영상</div>
        </div>
        <div className="bg-gray-900 rounded p-2">
          <div className="text-lg font-bold text-white">{summary.final_videos_count}</div>
          <div className="text-xs text-gray-400">편집 완료</div>
        </div>
        <div className="bg-gray-900 rounded p-2">
          <StatusBadge ok={summary.has_report} label="리포트" />
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [summaries, setSummaries] = useState<Summary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDates().then(async (r) => {
      const dates = r.data.dates.slice(0, 5)
      const results = await Promise.allSettled(dates.map((d) => getDateSummary(d)))
      const data = results
        .filter((r): r is PromiseFulfilledResult<{ data: Summary }> => r.status === 'fulfilled')
        .map((r) => r.value.data)
      setSummaries(data)
    }).finally(() => setLoading(false))
  }, [])

  const stats = summaries.reduce(
    (acc, s) => ({
      totalScripts: acc.totalScripts + s.scripts_count,
      totalFinal: acc.totalFinal + s.final_videos_count,
      totalRaw: acc.totalRaw + s.raw_videos_count,
    }),
    { totalScripts: 0, totalFinal: 0, totalRaw: 0 }
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">대시보드</h1>
        <p className="text-gray-400 mt-1 text-sm">콘텐츠 파이프라인 현황 요약</p>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: Calendar, label: '총 날짜', value: summaries.length, color: 'text-blue-400' },
          { icon: FileText, label: '총 스크립트', value: stats.totalScripts, color: 'text-purple-400' },
          { icon: Film, label: 'raw 영상', value: stats.totalRaw, color: 'text-orange-400' },
          { icon: TrendingUp, label: '편집 완료', value: stats.totalFinal, color: 'text-green-400' },
        ].map((card) => (
          <div key={card.label} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <card.icon size={18} className={card.color} />
              <span className="text-xs text-gray-400">{card.label}</span>
            </div>
            <div className="text-3xl font-bold text-white">{card.value}</div>
          </div>
        ))}
      </div>

      {/* 날짜별 현황 */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 size={16} className="text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-300">최근 작업 현황</h2>
        </div>
        {loading ? (
          <div className="text-gray-400 animate-pulse text-sm">불러오는 중...</div>
        ) : summaries.length === 0 ? (
          <div className="text-gray-500 text-sm">아직 생성된 콘텐츠가 없습니다. 파이프라인을 실행하세요.</div>
        ) : (
          <div className="space-y-3">
            {summaries.map((s) => <SummaryCard key={s.date} summary={s} />)}
          </div>
        )}
      </div>
    </div>
  )
}
