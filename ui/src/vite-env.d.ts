/// <reference types="vite/client" />

declare interface ImportMetaEnv {
  readonly VITE_NEXT_PUBLIC_API_URL?: string;
  readonly VITE_API_URL?: string;
  readonly NEXT_PUBLIC_API_URL?: string;
  readonly VITE_MAPS_API_KEY?: string;
}

declare interface ImportMeta {
  readonly env: ImportMetaEnv;
}
