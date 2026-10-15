import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { StepEvent, ToolEvent } from '../../entities/assistant/stream'
import { ActivityTrail } from './ActivityTrail'

describe('ActivityTrail', () => {
  it('returns null when there are no steps or tools', () => {
    const { container } = render(
      <ActivityTrail steps={[]} tools={[]} running={false} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders running state with steps and in-flight tool', () => {
    const steps: StepEvent[] = [
      { node: 'plan', label: 'Analyzing question and period' },
    ]
    const tools: ToolEvent[] = [
      { name: 'get_period_summary', args_summary: '2026-03', ok: true },
    ]

    render(<ActivityTrail steps={steps} tools={tools} running={true} />)

    const trail = screen.getByTestId('activity-trail')
    expect(trail).toBeInTheDocument()
    expect(trail).toHaveAttribute('data-running', 'true')

    expect(screen.getAllByText('Analyzing question and period').length).toBeGreaterThan(0)
    expect(screen.getByText(/get_period_summary/)).toBeInTheDocument()
  })

  it('groups multiple tool calls and expands/collapses when finished', () => {
    const steps: StepEvent[] = [
      { node: 'plan', label: 'Analyzing question' },
    ]
    const tools: ToolEvent[] = [
      { name: 'list_findings', args_summary: 'severity=HIGH', ok: true },
      { name: 'list_findings', args_summary: 'severity=CRITICAL', ok: true },
      { name: 'list_findings', args_summary: 'all', ok: true },
    ]

    render(<ActivityTrail steps={steps} tools={tools} running={false} />)

    const trail = screen.getByTestId('activity-trail')
    expect(trail).toBeInTheDocument()
    expect(trail).not.toHaveAttribute('data-running')

    // Collapsed initially when running is false
    const toggleButton = screen.getByRole('button')
    expect(screen.queryByTestId('trail-tool')).toBeNull()

    // Expand
    fireEvent.click(toggleButton)
    const toolItems = screen.getAllByTestId('trail-tool')
    expect(toolItems).toHaveLength(1)
    expect(toolItems[0]).toHaveAttribute('data-calls', '3')
    expect(screen.getByText('×3')).toBeInTheDocument()
    expect(screen.getByText(/list_findings/)).toBeInTheDocument()

    // Collapse again
    fireEvent.click(toggleButton)
    expect(screen.queryByTestId('trail-tool')).toBeNull()
  })

  it('renders tool failure correctly', () => {
    const tools: ToolEvent[] = [
      { name: 'bad_tool', args_summary: 'err', ok: false },
    ]

    render(<ActivityTrail steps={[]} tools={tools} running={true} />)
    expect(screen.getAllByText(/bad_tool/).length).toBeGreaterThan(0)
  })
})
