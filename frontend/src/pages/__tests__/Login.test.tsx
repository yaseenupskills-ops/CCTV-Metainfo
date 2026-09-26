import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Login from '../Login'

const login = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    login,
    logout: vi.fn(),
  }),
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

describe('Login', () => {
  beforeEach(() => {
    login.mockReset()
  })

  it('renders email and password fields', () => {
    render(<Login />)
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('calls login with credentials and shows no error on success', async () => {
    login.mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(<Login />)

    await user.type(screen.getByLabelText('Email'), 'admin@cctv.local')
    await user.type(screen.getByLabelText('Password'), 'ChangeMe123!')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith('admin@cctv.local', 'ChangeMe123!')
    })
  })

  it('shows an error message when login fails', async () => {
    login.mockRejectedValue(new Error('bad credentials'))
    const user = userEvent.setup()
    render(<Login />)

    await user.type(screen.getByLabelText('Email'), 'admin@cctv.local')
    await user.type(screen.getByLabelText('Password'), 'wrong-pass')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument()
  })
})
