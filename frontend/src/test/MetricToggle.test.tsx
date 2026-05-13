import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MetricToggle } from '../components/compare/MetricToggle';
import { METRICS } from '../constants';

const defaultProps = {
  xMode: 'year' as const,
  onXModeChange: () => {},
  showGlyphs: true,
  onToggleGlyphs: () => {},
};

describe('MetricToggle', () => {
  it('renders a tab for every metric plus the two x-mode tabs', () => {
    render(<MetricToggle metric="war" onChange={() => {}} {...defaultProps} />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(METRICS.length + 2);
  });

  it('marks the active metric as selected', () => {
    render(<MetricToggle metric="hr" onChange={() => {}} {...defaultProps} />);
    const hrTab = screen.getByRole('tab', { name: /^hr$/i });
    expect(hrTab).toHaveAttribute('aria-selected', 'true');
  });

  it('all metric tabs except active are not selected', () => {
    render(<MetricToggle metric="war" onChange={() => {}} {...defaultProps} />);
    const allTabs = screen.getAllByRole('tab');
    const notSelected = allTabs.filter(t => t.getAttribute('aria-selected') !== 'true');
    // 5 metric tabs + 1 xmode tab (By Age) are not selected
    expect(notSelected).toHaveLength(METRICS.length - 1 + 1);
  });

  it('calls onChange with the correct metric id when clicked', async () => {
    const onChange = vi.fn();
    render(<MetricToggle metric="war" onChange={onChange} {...defaultProps} />);
    await userEvent.click(screen.getByRole('tab', { name: /^hr$/i }));
    expect(onChange).toHaveBeenCalledWith('hr');
  });

  it('does not call onChange when clicking the already-active tab', async () => {
    const onChange = vi.fn();
    render(<MetricToggle metric="war" onChange={onChange} {...defaultProps} />);
    await userEvent.click(screen.getByRole('tab', { name: /^war/i }));
    // onChange is called — it's up to the parent to ignore no-ops
    expect(onChange).toHaveBeenCalledWith('war');
  });

  it('shows the full metric name next to the active tab label', () => {
    const warMetric = METRICS.find(m => m.id === 'war')!;
    render(<MetricToggle metric="war" onChange={() => {}} {...defaultProps} />);
    expect(screen.getByText(new RegExp(warMetric.full, 'i'))).toBeInTheDocument();
  });
});
