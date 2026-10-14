import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App component', () => {
  it('renders the landing page for a visitor', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: /Every number has a source/i })).toBeInTheDocument()
  })
})
