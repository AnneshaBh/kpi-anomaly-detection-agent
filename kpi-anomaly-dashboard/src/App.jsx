import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { DataProvider } from './hooks/useCSVData'
import { FilterProvider } from './hooks/useFilters'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import LoginPage from './pages/LoginPage'
import ExecutiveOverview from './pages/ExecutiveOverview'
import AnomalyTimeline from './pages/AnomalyTimeline'
import RootCauseAnalysis from './pages/RootCauseAnalysis'
import BusinessImpact from './pages/BusinessImpact'
import RecommendationsActions from './pages/RecommendationsActions'

function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function DashboardLayout() {
  return (
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
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <PrivateRoute>
                <DashboardLayout />
              </PrivateRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}