import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL,
  timeout: 20000,
  headers: {
    // Avoid stale tab-filtered lists on iOS PWA / standalone (Safari HTTP cache).
    'Cache-Control': 'no-cache',
    Pragma: 'no-cache',
  },
})

export default client
