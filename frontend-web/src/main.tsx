import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from '@/components/theme-provider'
import { getAdminRoute } from '@/lib/env'
import { AdminLoadingScreen } from './admin/components/brand/AdminTdevLogo'

const AdminApp = lazy(() => import('./admin/App.tsx'))

const adminRoute = getAdminRoute();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <BrowserRouter>
        <Routes>
          {adminRoute ? (
            <Route
              path={`${adminRoute}/*`}
              element={
                <Suspense fallback={<AdminLoadingScreen message="Chargement de l’admin…" />}>
                  <AdminApp />
                </Suspense>
              }
            />
          ) : null}
          <Route path="/" element={<App />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
