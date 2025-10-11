import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginPage } from '../LoginPage'
import {
  renderWithProviders,
  ApiMockUtils,
  FrontendTestFactory,
  TestHelpers,
} from '@/test/testUtils'

// Mock the useNavigate hook
const mockNavigate = jest.fn()
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}))

// Mock the auth hook
const mockLogin = jest.fn()
jest.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    isLoading: false,
    error: null,
  }),
}))

describe('LoginPage', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
    mockLogin.mockClear()
    ApiMockUtils.clearFetchMocks()
  })

  describe('Rendering', () => {
    it('should render login form with all required fields', () => {
      renderWithProviders(<LoginPage />)

      expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument()
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('should render additional login options', () => {
      renderWithProviders(<LoginPage />)

      expect(screen.getByText(/don't have an account/i)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /forgot password/i })).toBeInTheDocument()
    })

    it('should render SSO options if enabled', () => {
      // Mock SSO configuration
      Object.defineProperty(window, '__APP_CONFIG__', {
        value: { ssoEnabled: true },
        writable: true,
      })

      renderWithProviders(<LoginPage />)

      expect(screen.getByRole('button', { name: /sign in with sso/i })).toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('should show validation errors for empty fields', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LoginPage />)

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      })
    })

    it('should show validation error for invalid email format', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LoginPage />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument()
      })
    })

    it('should show validation error for short password', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LoginPage />)

      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(passwordInput, '123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument()
      })
    })

    it('should clear validation errors when user starts typing', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LoginPage />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      // Trigger validation error
      await user.click(submitButton)
      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      })

      // Start typing to clear error
      await user.type(emailInput, 'test@example.com')
      await waitFor(() => {
        expect(screen.queryByText(/email is required/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Form Submission', () => {
    it('should submit form with valid credentials', async () => {
      const user = userEvent.setup()
      const mockUser = FrontendTestFactory.createMockUser({
        email: 'test@example.com',
      })

      // Mock successful login response
      ApiMockUtils.mockFetch({
        user: mockUser,
        tokens: {
          accessToken: 'mock-access-token',
          refreshToken: 'mock-refresh-token',
          expiresIn: 3600,
        },
      })

      renderWithProviders(<LoginPage />)

      await TestHelpers.fillAndSubmitForm({
        email: 'test@example.com',
        password: 'password123',
      }, 'Sign In')

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
        })
      })
    })

    it('should show loading state during form submission', async () => {
      const user = userEvent.setup()

      // Mock slow API response
      ApiMockUtils.mockFetch({}, 200)

      renderWithProviders(<LoginPage />)

      await TestHelpers.fillAndSubmitForm({
        email: 'test@example.com',
        password: 'password123',
      }, 'Sign In')

      // Should show loading state
      expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    })

    it('should handle login errors gracefully', async () => {
      const user = userEvent.setup()

      // Mock login error
      ApiMockUtils.mockFetchError('Invalid email or password', 401)

      renderWithProviders(<LoginPage />)

      await TestHelpers.fillAndSubmitForm({
        email: 'wrong@example.com',
        password: 'wrongpassword',
      }, 'Sign In')

      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
      })

      // Form should be re-enabled
      expect(screen.getByRole('button', { name: /sign in/i })).not.toBeDisabled()
    })

    it('should handle network errors', async () => {
      const user = userEvent.setup()

      // Mock network error
      ApiMockUtils.mockFetchReject(new Error('Network error'))

      renderWithProviders(<LoginPage />)

      await TestHelpers.fillAndSubmitForm({
        email: 'test@example.com',
        password: 'password123',
      }, 'Sign In')

      await waitFor(() => {
        expect(screen.getByText(/something went wrong. please try again/i)).toBeInTheDocument()
      })
    })

    it('should redirect to dashboard on successful login', async () => {
      const user = userEvent.setup()
      const mockUser = FrontendTestFactory.createMockUser()

      // Mock successful login
      ApiMockUtils.mockFetch({ user: mockUser })
      mockLogin.mockResolvedValue({ user: mockUser })

      renderWithProviders(<LoginPage />)

      await TestHelpers.fillAndSubmitForm({
        email: 'test@example.com',
        password: 'password123',
      }, 'Sign In')

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
      })
    })
  })

  describe('SSO Authentication', () => {
    beforeEach(() => {
      // Enable SSO for these tests
      Object.defineProperty(window, '__APP_CONFIG__', {
        value: { ssoEnabled: true },
        writable: true,
      })
    })

    it('should handle SSO login button click', async () => {
      const user = userEvent.setup()

      // Mock SSO redirect
      Object.defineProperty(window, 'location', {
        value: { href: '' },
        writable: true,
      })

      renderWithProviders(<LoginPage />)

      const ssoButton = screen.getByRole('button', { name: /sign in with sso/i })
      await user.click(ssoButton)

      // Should redirect to SSO provider
      expect(window.location.href).toContain('/auth/sso')
    })

    it('should disable SSO button when loading', async () => {
      const user = userEvent.setup()

      renderWithProviders(<LoginPage />)

      const ssoButton = screen.getByRole('button', { name: /sign in with sso/i })
      await user.click(ssoButton)

      // Button should be disabled during redirect
      expect(ssoButton).toBeDisabled()
    })
  })

  describe('Remember Me Functionality', () => {
    it('should save credentials when remember me is checked', async () => {
      const user = userEvent.setup()
      const mockUser = FrontendTestFactory.createMockUser()

      ApiMockUtils.mockFetch({ user: mockUser })
      mockLogin.mockResolvedValue({ user: mockUser })

      renderWithProviders(<LoginPage />)

      const rememberCheckbox = screen.getByLabelText(/remember me/i)
      await user.click(rememberCheckbox)

      await TestHelpers.fillAndSubmitForm({
        email: 'test@example.com',
        password: 'password123',
      }, 'Sign In')

      await waitFor(() => {
        expect(localStorage.setItem).toHaveBeenCalledWith(
          'rememberedEmail',
          'test@example.com'
        )
      })
    })

    it('should pre-fill email if previously remembered', () => {
      // Mock localStorage with remembered email
      const localStorageMock = global.localStorage as jest.Mocked<typeof localStorage>
      localStorageMock.getItem.mockReturnValue('remembered@example.com')

      renderWithProviders(<LoginPage />)

      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement
      expect(emailInput.value).toBe('remembered@example.com')
    })
  })

  describe('Password Visibility Toggle', () => {
    it('should toggle password visibility', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LoginPage />)

      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement
      const toggleButton = screen.getByRole('button', { name: /show password/i })

      // Initially hidden
      expect(passwordInput.type).toBe('password')

      // Click to show
      await user.click(toggleButton)
      expect(passwordInput.type).toBe('text')
      expect(screen.getByRole('button', { name: /hide password/i })).toBeInTheDocument()

      // Click to hide again
      await user.click(toggleButton)
      expect(passwordInput.type).toBe('password')
    })
  })

  describe('Keyboard Navigation', () => {
    it('should support keyboard navigation', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LoginPage />)

      // Tab through form elements
      await user.tab()
      expect(screen.getByLabelText(/email/i)).toHaveFocus()

      await user.tab()
      expect(screen.getByLabelText(/password/i)).toHaveFocus()

      await user.tab()
      expect(screen.getByLabelText(/remember me/i)).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('button', { name: /sign in/i })).toHaveFocus()
    })

    it('should submit form on Enter key', async () => {
      const user = userEvent.setup()
      const mockUser = FrontendTestFactory.createMockUser()

      ApiMockUtils.mockFetch({ user: mockUser })
      mockLogin.mockResolvedValue({ user: mockUser })

      renderWithProviders(<LoginPage />)

      const passwordInput = screen.getByLabelText(/password/i)

      await user.type(screen.getByLabelText(/email/i), 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(passwordInput, '{enter}')

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalled()
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      renderWithProviders(<LoginPage />)

      // Form should have proper labeling
      expect(screen.getByRole('form')).toBeInTheDocument()

      // Inputs should have proper labels
      expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-required', 'true')
      expect(screen.getByLabelText(/password/i)).toHaveAttribute('aria-required', 'true')

      // Error messages should be associated with inputs
      const emailInput = screen.getByLabelText(/email/i)
      expect(emailInput).toHaveAttribute('aria-describedby')
    })

    it('should announce errors to screen readers', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LoginPage />)

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await user.click(submitButton)

      await waitFor(() => {
        const errorMessage = screen.getByText(/email is required/i)
        expect(errorMessage).toHaveAttribute('role', 'alert')
      })
    })

    it('should have sufficient color contrast', () => {
      renderWithProviders(<LoginPage />)

      // This is a basic check - in real tests you'd use tools like jest-axe
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      const computedStyle = window.getComputedStyle(submitButton)

      // Button should have visible text
      expect(computedStyle.color).toBeDefined()
      expect(computedStyle.backgroundColor).toBeDefined()
    })
  })

  describe('Performance', () => {
    it('should render quickly', () => {
      const { time } = TestHelpers.measureRenderTime(() => {
        renderWithProviders(<LoginPage />)
      })

      // Login page should render within 100ms
      expect(time).toBeLessThan(100)
    })

    it('should handle rapid form submissions gracefully', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LoginPage />)

      const submitButton = screen.getByRole('button', { name: /sign in/i })

      // Fill form
      await user.type(screen.getByLabelText(/email/i), 'test@example.com')
      await user.type(screen.getByLabelText(/password/i), 'password123')

      // Rapid clicks should not cause multiple submissions
      await user.click(submitButton)
      await user.click(submitButton)
      await user.click(submitButton)

      // Should only call login once
      expect(mockLogin).toHaveBeenCalledTimes(1)
    })
  })

  describe('Responsive Design', () => {
    it('should adapt to mobile viewport', () => {
      // Set mobile viewport
      Object.defineProperty(window, 'innerWidth', { value: 375 })
      Object.defineProperty(window, 'innerHeight', { value: 667 })

      renderWithProviders(<LoginPage />)

      const container = screen.getByRole('main')
      expect(container).toHaveClass('mobile-layout')
    })

    it('should adapt to tablet viewport', () => {
      // Set tablet viewport
      Object.defineProperty(window, 'innerWidth', { value: 768 })
      Object.defineProperty(window, 'innerHeight', { value: 1024 })

      renderWithProviders(<LoginPage />)

      const container = screen.getByRole('main')
      expect(container).toHaveClass('tablet-layout')
    })
  })

  describe('Error Recovery', () => {
    it('should allow retry after network error', async () => {
      const user = userEvent.setup()

      // First attempt fails
      ApiMockUtils.mockFetchReject(new Error('Network error'))

      renderWithProviders(<LoginPage />)

      await TestHelpers.fillAndSubmitForm({
        email: 'test@example.com',
        password: 'password123',
      }, 'Sign In')

      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      })

      // Second attempt succeeds
      const mockUser = FrontendTestFactory.createMockUser()
      ApiMockUtils.mockFetch({ user: mockUser })
      mockLogin.mockResolvedValue({ user: mockUser })

      const retryButton = screen.getByRole('button', { name: /try again/i })
      await user.click(retryButton)

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
      })
    })
  })
})