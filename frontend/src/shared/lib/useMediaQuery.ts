import { useEffect, useState } from 'react'

/** True while the media query matches; false where `matchMedia` does not exist (tests, SSR). */
export function useMediaQuery(media: string): boolean {
  const [matches, setMatches] = useState(() => listMedia(media)?.matches ?? false)

  useEffect(() => {
    const mql = listMedia(media)
    if (!mql) return
    const onChange = () => setMatches(mql.matches)
    onChange()
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [media])

  return matches
}

function listMedia(media: string): MediaQueryList | null {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia(media)
    : null
}
