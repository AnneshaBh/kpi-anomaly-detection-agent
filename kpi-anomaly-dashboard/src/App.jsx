import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { DataProvider } from './hooks/useCSVData'
import { FilterProvider } from './hooks/useFilters'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import ExecutiveOverview from './pages/ExecutiveOverview'
import AnomalyTimeline from './pages/AnomalyTimeline'
import RootCauseAnalysis from './pages/RootCauseAnalysis'
import BusinessImpact from './pages/BusinessImpact'
import RecommendationsActions from './pages/RecommendationsActions'

export default function App() {
  return (
    <BrowserRouter>
      <DataProvider>
        <FilterProvider>
          <div className="flex h-screen bg-page overflow-hidden font-sans">
            <Sidebar />
            <div className="flex flex-col flex-1 overflow-hidden min-w-0">
              <TopBar />
              <main className="flex-1 overflow-auto">
                <Routes>
                  <Route path="/"                element={<Navigate to="/overview" replace />} />
                  <Route path="/overview"        element={<ExecutiveOverview />} />
                  <Route path="/timeline"        element={<AnomalyTimeline />} />
                  <Route path="/root-cause"      element={<RootCauseAnalysis />} />
                  <Route path="/impact"          element={<BusinessImpact />} />
                  <Route path="/recommendations" element={<RecommendationsActions />} />
                </Routes>
              </main>
            </div>
          </div>
        </FilterProvider>
      </DataProvider>
    </BrowserRouter>
  )
}
