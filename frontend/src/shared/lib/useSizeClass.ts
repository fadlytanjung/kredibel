import { useEffect, useState } from 'react'

export type SizeClass = 'compact' | 'medium' | 'expanded' | 'large' | 'wide'

export function getSizeClass(width: number): SizeClass {
  if (width < 600) return 'compact'
  if (width < 840) return 'medium'
  if (width < 1200) return 'expanded'
  if (width < 1600) return 'large'
  return 'wide'
}

export function useSizeClass() {
  const [sizeClass, setSizeClass] = useState<SizeClass>(() =>
    typeof window !== 'undefined' ? getSizeClass(window.innerWidth) : 'large'
  )

  useEffect(() => {
    const handleResize = () => {
      setSizeClass(getSizeClass(window.innerWidth))
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return {
    sizeClass,
    isCompact: sizeClass === 'compact',
    isMedium: sizeClass === 'medium',
    isExpanded: sizeClass === 'expanded',
    isLarge: sizeClass === 'large',
    isWide: sizeClass === 'wide',
  }
}
