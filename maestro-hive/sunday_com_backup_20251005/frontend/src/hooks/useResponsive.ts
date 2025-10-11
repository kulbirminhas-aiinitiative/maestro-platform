import { useState, useEffect } from 'react'

interface BreakpointConfig {
  sm: number
  md: number
  lg: number
  xl: number
  '2xl': number
}

const defaultBreakpoints: BreakpointConfig = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
}

type Breakpoint = keyof BreakpointConfig

export const useResponsive = (breakpoints: BreakpointConfig = defaultBreakpoints) => {
  const [screenSize, setScreenSize] = useState<{
    width: number
    height: number
  }>({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
  })

  useEffect(() => {
    const handleResize = () => {
      setScreenSize({
        width: window.innerWidth,
        height: window.innerHeight,
      })
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const isBreakpoint = (breakpoint: Breakpoint) => {
    return screenSize.width >= breakpoints[breakpoint]
  }

  const isSmallScreen = screenSize.width < breakpoints.md
  const isMediumScreen = screenSize.width >= breakpoints.md && screenSize.width < breakpoints.lg
  const isLargeScreen = screenSize.width >= breakpoints.lg

  return {
    screenSize,
    isBreakpoint,
    isSmallScreen,
    isMediumScreen,
    isLargeScreen,
    isSm: isBreakpoint('sm'),
    isMd: isBreakpoint('md'),
    isLg: isBreakpoint('lg'),
    isXl: isBreakpoint('xl'),
    is2Xl: isBreakpoint('2xl'),
  }
}

export const useIsMobile = () => {
  const { isSmallScreen } = useResponsive()
  return isSmallScreen
}

export const useBreakpoint = (breakpoint: Breakpoint) => {
  const { isBreakpoint } = useResponsive()
  return isBreakpoint(breakpoint)
}