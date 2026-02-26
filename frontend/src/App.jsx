import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import ChatPage from './pages/ChatPage'
import Layout from './components/Layout'

export default function App() {
    const [user, setUser] = useState(() => {
        try {
            return JSON.parse(sessionStorage.getItem('hire_ai_user')) || null
        } catch { return null }
    })

    const login = (u) => { setUser(u); sessionStorage.setItem('hire_ai_user', JSON.stringify(u)) }
    const logout = () => { setUser(null); sessionStorage.removeItem('hire_ai_user') }

    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage onLogin={login} />} />
                <Route element={user ? <Layout user={user} onLogout={logout} /> : <Navigate to="/login" />}>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/upload" element={<UploadPage />} />
                    <Route path="/chat" element={<ChatPage />} />
                </Route>
                <Route path="*" element={<Navigate to="/" />} />
            </Routes>
        </BrowserRouter>
    )
}
