import { useCallback, useMemo, useRef, useEffect, useState } from 'react'

/**
 * Hook for debouncing values to improve performance
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

/**
 * Hook for throttling function calls
 */
export function useThrottle<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): T {
  const lastRun = useRef(Date.now())

  return useCallback(
    ((...args) => {
      if (Date.now() - lastRun.current >= delay) {
        func(...args)
        lastRun.current = Date.now()
      }
    }) as T,
    [func, delay]
  )
}

/**
 * Hook for memoizing expensive calculations
 */
export function useMemoizedValue<T>(
  factory: () => T,
  deps: React.DependencyList
): T {
  return useMemo(factory, deps)
}

/**
 * Hook for memoizing callback functions
 */
export function useMemoizedCallback<T extends (...args: any[]) => any>(
  callback: T,
  deps: React.DependencyList
): T {
  return useCallback(callback, deps)
}

/**
 * Hook for lazy loading images
 */
export function useLazyImage(src: string, placeholder?: string) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [isInView, setIsInView] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true)
          observer.disconnect()
        }
      },
      { threshold: 0.1 }
    )

    if (imgRef.current) {
      observer.observe(imgRef.current)
    }

    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (isInView && src) {
      const img = new Image()
      img.onload = () => setIsLoaded(true)
      img.src = src
    }
  }, [isInView, src])

  return {
    ref: imgRef,
    src: isLoaded ? src : placeholder,
    isLoaded,
    isInView,
  }
}

/**
 * Hook for virtual scrolling large lists
 */
export function useVirtualList<T>({
  items,
  itemHeight,
  containerHeight,
  overscan = 5,
}: {
  items: T[]
  itemHeight: number
  containerHeight: number
  overscan?: number
}) {
  const [scrollTop, setScrollTop] = useState(0)

  const visibleStart = Math.floor(scrollTop / itemHeight)
  const visibleEnd = Math.min(
    visibleStart + Math.ceil(containerHeight / itemHeight),
    items.length - 1
  )

  const paddingTop = visibleStart * itemHeight
  const paddingBottom = (items.length - visibleEnd - 1) * itemHeight

  const visibleItems = items.slice(
    Math.max(0, visibleStart - overscan),
    Math.min(items.length, visibleEnd + 1 + overscan)
  )

  return {
    visibleItems,
    paddingTop,
    paddingBottom,
    setScrollTop,
  }
}

/**
 * Hook for tracking component render performance
 */
export function useRenderPerformance(componentName: string, enabled = false) {
  const renderStart = useRef<number>()
  const renderCount = useRef(0)

  useEffect(() => {
    if (enabled) {
      renderStart.current = performance.now()
      renderCount.current += 1
    }
  })

  useEffect(() => {
    if (enabled && renderStart.current) {
      const renderTime = performance.now() - renderStart.current
      console.log(`${componentName} render #${renderCount.current}: ${renderTime.toFixed(2)}ms`)
    }
  })

  return {
    renderCount: renderCount.current,
  }
}

/**
 * Hook for optimizing expensive computations with Web Workers
 */
export function useWebWorker<TInput, TOutput>(
  workerScript: string,
  onResult?: (result: TOutput) => void,
  onError?: (error: Error) => void
) {
  const workerRef = useRef<Worker>()
  const [isProcessing, setIsProcessing] = useState(false)

  useEffect(() => {
    workerRef.current = new Worker(workerScript)

    workerRef.current.onmessage = (event) => {
      setIsProcessing(false)
      onResult?.(event.data)
    }

    workerRef.current.onerror = (error) => {
      setIsProcessing(false)
      onError?.(new Error(error.message))
    }

    return () => {
      workerRef.current?.terminate()
    }
  }, [workerScript, onResult, onError])

  const postMessage = useCallback((data: TInput) => {
    if (workerRef.current) {
      setIsProcessing(true)
      workerRef.current.postMessage(data)
    }
  }, [])

  return {
    postMessage,
    isProcessing,
  }
}

/**
 * Hook for batch updating to reduce re-renders
 */
export function useBatchUpdate<T>(initialState: T) {
  const [state, setState] = useState(initialState)
  const batchedUpdates = useRef<Partial<T>[]>([])
  const timeoutRef = useRef<NodeJS.Timeout>()

  const batchUpdate = useCallback((update: Partial<T>) => {
    batchedUpdates.current.push(update)

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    timeoutRef.current = setTimeout(() => {
      setState((prevState) => {
        const newState = { ...prevState }
        batchedUpdates.current.forEach((update) => {
          Object.assign(newState, update)
        })
        batchedUpdates.current = []
        return newState
      })
    }, 0)
  }, [])

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return [state, batchUpdate] as const
}

/**
 * Hook for optimizing component updates with shouldComponentUpdate logic
 */
export function useShallowCompare<T extends Record<string, any>>(value: T): T {
  const ref = useRef<T>(value)

  const isEqual = useMemo(() => {
    const keys = Object.keys(value)
    const refKeys = Object.keys(ref.current)

    if (keys.length !== refKeys.length) {
      return false
    }

    for (const key of keys) {
      if (value[key] !== ref.current[key]) {
        return false
      }
    }

    return true
  }, [value])

  if (!isEqual) {
    ref.current = value
  }

  return ref.current
}

/**
 * Hook for preloading resources
 */
export function usePreloader() {
  const preloadedResources = useRef<Set<string>>(new Set())

  const preloadImage = useCallback((src: string): Promise<void> => {
    if (preloadedResources.current.has(src)) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => {
        preloadedResources.current.add(src)
        resolve()
      }
      img.onerror = reject
      img.src = src
    })
  }, [])

  const preloadScript = useCallback((src: string): Promise<void> => {
    if (preloadedResources.current.has(src)) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.onload = () => {
        preloadedResources.current.add(src)
        resolve()
      }
      script.onerror = reject
      script.src = src
      document.head.appendChild(script)
    })
  }, [])

  const preloadCSS = useCallback((href: string): Promise<void> => {
    if (preloadedResources.current.has(href)) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.onload = () => {
        preloadedResources.current.add(href)
        resolve()
      }
      link.onerror = reject
      link.href = href
      document.head.appendChild(link)
    })
  }, [])

  return {
    preloadImage,
    preloadScript,
    preloadCSS,
    preloadedResources: preloadedResources.current,
  }
}