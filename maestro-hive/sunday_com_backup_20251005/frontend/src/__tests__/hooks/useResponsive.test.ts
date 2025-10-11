import { renderHook, act } from '@testing-library/react'
import { useResponsive, useIsMobile, useBreakpoint } from '@/hooks/useResponsive'

// Mock window object
const mockWindow = (width: number, height: number = 800) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  })
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: height,
  })
}

describe('useResponsive', () => {
  beforeEach(() => {
    // Reset to default desktop size
    mockWindow(1200, 800)
  })

  afterEach(() => {
    // Clean up event listeners
    window.removeEventListener('resize', jest.fn())
  })

  it('returns correct screen size on mount', () => {
    mockWindow(1024, 768)

    const { result } = renderHook(() => useResponsive())

    expect(result.current.screenSize.width).toBe(1024)
    expect(result.current.screenSize.height).toBe(768)
  })

  it('detects small screen correctly', () => {
    mockWindow(600) // Below md breakpoint (768)

    const { result } = renderHook(() => useResponsive())

    expect(result.current.isSmallScreen).toBe(true)
    expect(result.current.isMediumScreen).toBe(false)
    expect(result.current.isLargeScreen).toBe(false)
  })

  it('detects medium screen correctly', () => {
    mockWindow(800) // Between md (768) and lg (1024)

    const { result } = renderHook(() => useResponsive())

    expect(result.current.isSmallScreen).toBe(false)
    expect(result.current.isMediumScreen).toBe(true)
    expect(result.current.isLargeScreen).toBe(false)
  })

  it('detects large screen correctly', () => {
    mockWindow(1200) // Above lg breakpoint (1024)

    const { result } = renderHook(() => useResponsive())

    expect(result.current.isSmallScreen).toBe(false)
    expect(result.current.isMediumScreen).toBe(false)
    expect(result.current.isLargeScreen).toBe(true)
  })

  it('detects breakpoints correctly', () => {
    mockWindow(1300)

    const { result } = renderHook(() => useResponsive())

    expect(result.current.isSm).toBe(true) // 1300 >= 640
    expect(result.current.isMd).toBe(true) // 1300 >= 768
    expect(result.current.isLg).toBe(true) // 1300 >= 1024
    expect(result.current.isXl).toBe(true) // 1300 >= 1280
    expect(result.current.is2Xl).toBe(false) // 1300 < 1536
  })

  it('updates screen size on window resize', () => {
    mockWindow(1200)

    const { result } = renderHook(() => useResponsive())

    expect(result.current.screenSize.width).toBe(1200)
    expect(result.current.isLargeScreen).toBe(true)

    // Simulate window resize
    act(() => {
      mockWindow(600)
      window.dispatchEvent(new Event('resize'))
    })

    expect(result.current.screenSize.width).toBe(600)
    expect(result.current.isSmallScreen).toBe(true)
  })

  it('works with custom breakpoints', () => {
    const customBreakpoints = {
      sm: 500,
      md: 700,
      lg: 900,
      xl: 1100,
      '2xl': 1300,
    }

    mockWindow(800)

    const { result } = renderHook(() => useResponsive(customBreakpoints))

    expect(result.current.isBreakpoint('sm')).toBe(true) // 800 >= 500
    expect(result.current.isBreakpoint('md')).toBe(true) // 800 >= 700
    expect(result.current.isBreakpoint('lg')).toBe(false) // 800 < 900
  })
})

describe('useIsMobile', () => {
  it('returns true for small screens', () => {
    mockWindow(600) // Below md breakpoint

    const { result } = renderHook(() => useIsMobile())

    expect(result.current).toBe(true)
  })

  it('returns false for larger screens', () => {
    mockWindow(800) // Above md breakpoint

    const { result } = renderHook(() => useIsMobile())

    expect(result.current).toBe(false)
  })

  it('updates when screen size changes', () => {
    mockWindow(600)

    const { result } = renderHook(() => useIsMobile())

    expect(result.current).toBe(true)

    act(() => {
      mockWindow(1000)
      window.dispatchEvent(new Event('resize'))
    })

    expect(result.current).toBe(false)
  })
})

describe('useBreakpoint', () => {
  it('returns true when screen meets breakpoint', () => {
    mockWindow(1000)

    const { result } = renderHook(() => useBreakpoint('md'))

    expect(result.current).toBe(true) // 1000 >= 768
  })

  it('returns false when screen does not meet breakpoint', () => {
    mockWindow(600)

    const { result } = renderHook(() => useBreakpoint('lg'))

    expect(result.current).toBe(false) // 600 < 1024
  })

  it('updates when breakpoint changes', () => {
    mockWindow(600)

    const { result } = renderHook(() => useBreakpoint('md'))

    expect(result.current).toBe(false) // 600 < 768

    act(() => {
      mockWindow(800)
      window.dispatchEvent(new Event('resize'))
    })

    expect(result.current).toBe(true) // 800 >= 768
  })
})