import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import Login from '../pages/Login'
import * as api from '../api/client'

// Mock the API
vi.mock('../api/client', () => ({
  authApi: {
    login: vi.fn(),
  },
}))

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )
    expect(screen.getByText(/登录/i)).toBeDefined()
  })

  it('shows error on invalid credentials', async () => {
    vi.mocked(api.authApi.login).mockRejectedValueOnce(new Error('Invalid credentials'))
    
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )
    
    const emailInput = screen.getByPlaceholderText(/邮箱/i)
    const passwordInput = screen.getByPlaceholderText(/密码/i)
    const submitButton = screen.getByRole('button', { name: /登录/i })
    
    await userEvent.type(emailInput, 'test@example.com')
    await userEvent.type(passwordInput, 'wrongpassword')
    await userEvent.click(submitButton)
    
    await waitFor(() => {
      expect(api.authApi.login).toHaveBeenCalled()
    })
  })
})
