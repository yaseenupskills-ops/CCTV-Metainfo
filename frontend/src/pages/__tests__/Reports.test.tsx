import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Reports from '../Reports'

// Only the network layer is mocked; the real hooks and QueryClient run.
const listCases = vi.fn()
const listEvidence = vi.fn()
const listReports = vi.fn()
const generateReport = vi.fn()

vi.mock('../../api/client', () => ({
  listCases: (...args: unknown[]) => listCases(...args),
  listEvidence: (...args: unknown[]) => listEvidence(...args),
  listReports: (...args: unknown[]) => listReports(...args),
  generateReport: (...args: unknown[]) => generateReport(...args),
  downloadReport: vi.fn(),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <Reports />
    </QueryClientProvider>,
  )
}

// Matched on role and type rather than label, since the label changes to
// "Generating…" while the request is in flight.
const submitButton = () => screen.getByRole('button', { name: /generat/i })

/** The page renders "Loading…" until the three list queries settle. */
async function renderLoaded() {
  const result = renderPage()
  await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
  return result
}

describe('Reports page', () => {
  beforeEach(() => {
    listCases.mockReset()
    listEvidence.mockReset()
    listReports.mockReset()
    generateReport.mockReset()

    listCases.mockResolvedValue({
      items: [{ id: 'c1', case_number: 'CASE-0001' }],
    })
    listEvidence.mockResolvedValue({
      items: [{ id: 'e1', evidence_number: 'EVD-001', case_id: 'c1' }],
    })
    listReports.mockResolvedValue({ items: [] })
    generateReport.mockResolvedValue({ id: 'r1' })
  })

  // The defect: the page held its own `generating` flag, set true on submit and
  // never reset, so the button stayed disabled and read "Generating…" for the
  // rest of the session. One report per page load, no second attempt.

  it('enables the button again after a report is generated', async () => {
    const user = userEvent.setup()
    await renderLoaded()

    await user.selectOptions(screen.getByLabelText('Case'), 'c1')
    await user.click(submitButton())

    await waitFor(() =>
      expect(screen.getByText('Report generation started.')).toBeInTheDocument(),
    )
    expect(submitButton()).toBeEnabled()
    expect(submitButton()).toHaveTextContent('Generate Report')
  })

  it('generates two reports back to back', async () => {
    const user = userEvent.setup()
    await renderLoaded()

    await user.selectOptions(screen.getByLabelText('Case'), 'c1')

    await user.click(submitButton())
    await waitFor(() => expect(generateReport).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(submitButton()).toBeEnabled())

    // The second submission is the one the old code made impossible.
    await user.click(submitButton())
    await waitFor(() => expect(generateReport).toHaveBeenCalledTimes(2))
  })

  it('shows progress only while the request is in flight', async () => {
    const user = userEvent.setup()
    let release: (value: unknown) => void = () => {}
    generateReport.mockReturnValue(
      new Promise((resolve) => {
        release = resolve
      }),
    )

    await renderLoaded()
    await user.selectOptions(screen.getByLabelText('Case'), 'c1')
    await user.click(submitButton())

    await waitFor(() => expect(submitButton()).toBeDisabled())
    expect(submitButton()).toHaveTextContent('Generating')

    release({ id: 'r1' })

    await waitFor(() => expect(submitButton()).toBeEnabled())
    expect(submitButton()).toHaveTextContent('Generate Report')
  })

  it('re-enables the button after a failed generation', async () => {
    const user = userEvent.setup()
    generateReport.mockRejectedValue({
      response: { data: { detail: 'Evidence has no metadata.' } },
    })

    await renderLoaded()
    await user.selectOptions(screen.getByLabelText('Case'), 'c1')
    await user.click(submitButton())

    await waitFor(() =>
      expect(screen.getByText('Evidence has no metadata.')).toBeInTheDocument(),
    )
    expect(submitButton()).toBeEnabled()
  })

  it('recovers so a retry succeeds after an error', async () => {
    const user = userEvent.setup()
    generateReport.mockRejectedValueOnce({ response: { data: { detail: 'boom' } } })

    await renderLoaded()
    await user.selectOptions(screen.getByLabelText('Case'), 'c1')

    await user.click(submitButton())
    await waitFor(() => expect(screen.getByText('boom')).toBeInTheDocument())

    await user.click(submitButton())
    await waitFor(() => expect(generateReport).toHaveBeenCalledTimes(2))
    await waitFor(() =>
      expect(screen.getByText('Report generation started.')).toBeInTheDocument(),
    )
  })

  it('does not submit without a case selected', async () => {
    const user = userEvent.setup()
    await renderLoaded()

    await user.click(submitButton())

    expect(generateReport).not.toHaveBeenCalled()
  })
})
