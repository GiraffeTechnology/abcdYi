import { readFileSync } from 'node:fs'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const RESERVED_PORT = 443

function usablePort(value: unknown): number | null {
  const port = Number(String(value ?? '').trim())
  return Number.isInteger(port) && port > 0 && port < 65536 && port !== RESERVED_PORT ? port : null
}

// No fixed dev port: VITE_DEV_PORT is optional, and 0 lets the OS pick a free
// port. 443 is owned by SSH on CTYun hosts and is never used.
const devPort = usablePort(process.env.VITE_DEV_PORT) ?? 0

// MyAivan picks its own port at startup and writes it to AIVAN_PORT_FILE. When
// VITE_MYAIVAN_URL is not given, build the entry from that file so no port has
// to be typed in by hand.
function derivedMyAivanUrl(): string | undefined {
  const host = process.env.MYAIVAN_PUBLIC_HOST?.trim()
  const portFile = process.env.MYAIVAN_PORT_FILE?.trim()
  if (!host || !portFile) return undefined
  let port: number | null = null
  try {
    port = usablePort(readFileSync(portFile, 'utf-8'))
  } catch {
    return undefined
  }
  if (!port) return undefined
  const scheme = process.env.MYAIVAN_PUBLIC_SCHEME?.trim() || 'http'
  return `${scheme}://${host}:${port}/app`
}

const myAivanUrl = process.env.VITE_MYAIVAN_URL?.trim() || derivedMyAivanUrl()

export default defineConfig({
  plugins: [react()],
  define: myAivanUrl ? { 'import.meta.env.VITE_MYAIVAN_URL': JSON.stringify(myAivanUrl) } : {},
  server: {
    host: true,
    port: devPort,
    strictPort: false,
  },
})
