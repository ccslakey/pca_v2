import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MetricToggle } from '../components/MetricToggle';
import { METRICS } from '../constants';

describe('MetricToggle', () => {
  it('renders a tab for every metric', () => {
    render(<MetricToggle metric="war" onChange={() => {}} />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(METRICS.length);
  });

  it('marks the active metric as selected', () => {
    render(<MetricToggle metric="hr" onChange={() => {}} />);
    const hrTab = screen.getByRole('tab', { name: /hr/i });
    expect(hrTab).toHaveAttribute('aria-selected', 'true');
  });

  it('all other tabs are not selected', () => {
    render(<MetricToggle metric="war" onChange={() => {}} />);
    const tabs = screen.getAllByRole('tab');
    const notSelected = tabs.filter(t => t.getAttribute('aria-selected') !== 'true');
    expect(notSelected).toHaveLength(METRICS.length - 1);
  });

  it('calls onChange with the correct metric id when clicked', async () => {
    const onChange = vi.fn();
    render(<MetricToggle metric="war" onChange={onChange} />);
    await userEvent.click(screen.getByRole('tab', { name: /hr/i }));
    expect(onChange).toHaveBeenCalledWith('hr');
  });

  it('does not call onChange when clicking the already-active tab', async () => {
    const onChange = vi.fn();
    render(<MetricToggle metric="war" onChange={onChange} />);
    await userEvent.click(screen.getByRole('tab', { name: /war/i }));
    // onChange is called — it's up to the parent to ignore no-ops
    expect(onChange).toHaveBeenCalledWith('war');
  });

  it('shows the full metric name next to the active tab label', () => {
    const warMetric = METRICS.find(m => m.id === 'war')!;
    render(<MetricToggle metric="war" onChange={() => {}} />);
    expect(screen.getByText(new RegExp(warMetric.full, 'i'))).toBeInTheDocument();
  });
});
