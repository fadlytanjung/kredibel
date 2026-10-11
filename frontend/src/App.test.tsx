import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App component', () => {
  it('renders login page when unauthenticated', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: /Sign in to Kredibel/i })).toBeInTheDocument()
  })
})
