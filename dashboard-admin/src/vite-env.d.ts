/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_USE_MOCKS: string;
  readonly VITE_APP_NAME: string;
  readonly VITE_DEFAULT_EVENT_SLUG: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
