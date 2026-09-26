import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import Layout from './components/Layout'
import { AuthProvider } from './hooks/AuthProvider'
import { useAuth } from './hooks/useAuth'
import Analysis from './pages/Analysis'
import AuditLogs from './pages/AuditLogs'
import Cases from './pages/Cases'
import CaseDetail from './pages/CaseDetail'
import Dashboard from './pages/Dashboard'
import Evidence from './pages/Evidence'
import EvidenceDetail from './pages/EvidenceDetail'
import Login from './pages/Login'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import Timeline from './pages/Timeline'
import Upload from './pages/Upload'
import Users from './pages/Users'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <p className="p-6 text-slate-400">Loading…</p>
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return children
}

const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <Layout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'cases', element: <Cases /> },
      { path: 'cases/:id', element: <CaseDetail /> },
      { path: 'evidence', element: <Evidence /> },
      { path: 'evidence/:id', element: <EvidenceDetail /> },
      { path: 'upload', element: <Upload /> },
      { path: 'analysis', element: <Analysis /> },
      { path: 'timeline', element: <Timeline /> },
      { path: 'reports', element: <Reports /> },
      { path: 'audit-logs', element: <AuditLogs /> },
      { path: 'users', element: <Users /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}
