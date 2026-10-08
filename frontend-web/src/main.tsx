import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import InscriptionPage from './pages/InscriptionPage.tsx'
import { StorefrontTheme } from '@/components/storefront/StorefrontTheme'
import { ThemeProvider } from '@/components/theme-provider'
import { getAdminRoute } from '@/lib/env'
import { AdminLoadingScreen } from './admin/components/brand/AdminTdevLogo'

const AdminApp = lazy(() => import('./admin/App.tsx'))

const adminRoute = getAdminRoute();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
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
          <Route
            path="/"
            element={
              <StorefrontTheme>
                <App />
              </StorefrontTheme>
            }
          />
          <Route
            path="/billetterie"
            element={
              <StorefrontTheme>
                <App />
              </StorefrontTheme>
            }
          />
          <Route
            path="/inscription/:passSlug"
            element={
              <StorefrontTheme>
                <InscriptionPage />
              </StorefrontTheme>
            }
          />
          <Route
            path="/inscription"
            element={
              <StorefrontTheme>
                <InscriptionPage />
              </StorefrontTheme>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
