import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Play, FileEdit, Calendar } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import PipelineControl from './pages/PipelineControl'
import ContentReview from './pages/ContentReview'
import ScheduleManager from './pages/ScheduleManager'

const NAV_ITEMS = [
  { to: '/', label: '대시보드', icon: LayoutDashboard },
  { to: '/pipeline', label: '파이프라인', icon: Play },
  { to: '/content', label: '콘텐츠 검토', icon: FileEdit },
  { to: '/schedule', label: '스케줄', icon: Calendar },
]

function Sidebar() {
  return (
    <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* 로고 */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-brand-red rounded-md flex items-center justify-center text-white text-xs font-bold">TK</div>
          <div>
            <div className="text-sm font-bold text-white leading-tight">콘텐츠 어드민</div>
            <div className="text-xs text-gray-500">비즈니스 인사이트</div>
          </div>
        </div>
      </div>

      {/* 네비게이션 */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-brand-red/20 text-brand-red font-medium'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`
            }
          >
            <item.icon size={16} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* 하단 정보 */}
      <div className="px-5 py-4 border-t border-gray-800">
        <p className="text-xs text-gray-600">TikTok Content Pipeline</p>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/pipeline" element={<PipelineControl />} />
            <Route path="/content" element={<ContentReview />} />
            <Route path="/schedule" element={<ScheduleManager />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
