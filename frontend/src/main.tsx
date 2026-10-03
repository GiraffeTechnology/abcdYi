import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App myAivanUrl={import.meta.env.VITE_MYAIVAN_URL} />
  </React.StrictMode>,
)
