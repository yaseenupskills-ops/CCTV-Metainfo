import { useEffect, useState, type ReactNode } from 'react'

import {
  clearStoredToken,
  getMe,
  getStoredToken,
  login as loginRequest,
  storeToken,
} from '../api/client'
import type { User } from '../types'
import { AuthContext } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    if (!getStoredToken()) {
      setLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => {
        clearStoredToken()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string): Promise<void> {
    const response = await loginRequest(email, password)
    storeToken(response.access_token)
    setUser(response.user)
  }

  function logout(): void {
    clearStoredToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
