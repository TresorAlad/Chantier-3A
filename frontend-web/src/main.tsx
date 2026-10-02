import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from '@/components/theme-provider'
import { getAdminRoute } from '@/lib/env'

const AdminApp = lazy(() => import('./admin/App.tsx'))

const adminRoute = getAdminRoute();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          {adminRoute ? (
            <Route
              path={`${adminRoute}/*`}
              element={
                <Suspense
                  fallback={
                    <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC]">
                      <div className="w-8 h-8 border-4 border-green-800 border-t-transparent rounded-full animate-spin" />
                    </div>
                  }
                >
                  <AdminApp />
                </Suspense>
              }
            />
          ) : null}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
