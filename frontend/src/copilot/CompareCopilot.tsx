// Prototype: CopilotKit chat on the Compare page. Throwaway code.
import { Component, useMemo, useRef, useState, type ReactNode } from 'react';
import { HttpAgent } from '@ag-ui/client';
import {
  CopilotKit,
  CopilotSidebar,
  useAgentContext,
  useFrontendTool,
} from '@copilotkit/react-core/v2';
import '@copilotkit/react-core/v2/styles.css';
import { z } from 'zod';
import { MAX_PLAYERS, METRICS } from '../constants';
import { useTheme } from '../themes/ThemeContext';
import type { MetricId, XMode } from '../types';
import './CompareCopilot.scss';

export type CopilotVariant = 'sidecar' | 'agui';

export interface CompareCopilotProps {
  variant: CopilotVariant;
  playerIds: string[];
  playerNames: Record<string, string>;
  metric: MetricId;
  xMode: XMode;
  addPlayer: (id: string) => void;
  removePlayer: (id: string) => void;
  setPlayers: (ids: string[]) => void;
  changeMetric: (m: MetricId) => void;
  changeXMode: (x: XMode) => void;
}

const METRIC_IDS = METRICS.map(m => m.id) as [MetricId, ...MetricId[]];
const BBREF_ID = /^[a-z][a-z'.]{1,7}\d{2}$/;

function badIds(ids: unknown): string | null {
  if (!Array.isArray(ids) || ids.length > MAX_PLAYERS) return `ids must be a list of at most ${MAX_PLAYERS}`;
  const bad = ids.filter(id => typeof id !== 'string' || !BBREF_ID.test(id));
  return bad.length ? `not Baseball Reference ids: ${bad.join(', ')}. Use find_player.` : null;
}

function Bindings(props: CompareCopilotProps) {
  // Tools register once; handlers read the latest page state through this ref.
  const ref = useRef(props);
  ref.current = props;
  const p = props;
  useAgentContext({
    description:
      'Current compare page state, already including any page tools you called. ' +
      'players: who is on the chart (Baseball Reference id and name, max 10). ' +
      `metric: the plotted stat, one of ${METRIC_IDS.join(', ')}. xMode: x-axis, "year" or "age".`,
    value: {
      players: p.playerIds.map(id => ({ id, name: p.playerNames[id] ?? '(loading)' })),
      metric: p.metric,
      xMode: p.xMode,
    },
  });

  useFrontendTool({
    name: 'setPlayers',
    description: 'Replace the whole compare list with these player ids (max 10).',
    parameters: z.object({ ids: z.array(z.string()) }),
    handler: async ({ ids }) => {
      const err = badIds(ids);
      if (err) return `Error: ${err}`;
      ref.current.setPlayers(ids);
      return `Compare list is now: ${ids.join(', ') || '(empty)'}`;
    },
  }, []);

  useFrontendTool({
    name: 'addPlayer',
    description: 'Add one player id to the compare list.',
    parameters: z.object({ id: z.string() }),
    handler: async ({ id }) => {
      const err = badIds([id]);
      if (err) return `Error: ${err}`;
      if (ref.current.playerIds.length >= MAX_PLAYERS) return `Error: already ${MAX_PLAYERS} players`;
      ref.current.addPlayer(id);
      return `Added ${id}`;
    },
  }, []);

  useFrontendTool({
    name: 'removePlayer',
    description: 'Remove one player id from the compare list.',
    parameters: z.object({ id: z.string() }),
    handler: async ({ id }) => {
      ref.current.removePlayer(id);
      return `Removed ${id}`;
    },
  }, []);

  useFrontendTool({
    name: 'changeMetric',
    description: `Change the plotted stat. One of: ${METRICS.map(m => `${m.id} (${m.label})`).join(', ')}.`,
    parameters: z.object({ metric: z.enum(METRIC_IDS) }),
    handler: async ({ metric }) => {
      if (!METRIC_IDS.includes(metric)) return `Error: unknown metric ${metric}`;
      ref.current.changeMetric(metric);
      return `Metric is now ${metric}`;
    },
  }, []);

  useFrontendTool({
    name: 'changeXMode',
    description: 'Change the x-axis: "year" (calendar season) or "age" (player age).',
    parameters: z.object({ xMode: z.enum(['year', 'age']) }),
    handler: async ({ xMode }) => {
      if (xMode !== 'year' && xMode !== 'age') return `Error: unknown xMode ${xMode}`;
      ref.current.changeXMode(xMode);
      return `X-axis is now ${xMode}`;
    },
  }, []);

  return null;
}

class ChatBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed
      ? <div className="pca-copilot-down">Chat failed to load. The rest of the page still works.</div>
      : this.props.children;
  }
}

export default function CompareCopilot(props: CompareCopilotProps) {
  const [error, setError] = useState<string | null>(null);
  const { theme } = useTheme();
  const agents = useMemo(
    () => (props.variant === 'agui' ? { default: new HttpAgent({ url: '/api/copilot/agui/' }) } : undefined),
    [props.variant],
  );
  const transport = props.variant === 'agui'
    ? { agents__unsafe_dev_only: agents }
    : { runtimeUrl: '/api/copilotkit' };

  return (
    <ChatBoundary>
      {/* CopilotKit keys its dark styles off a .dark ancestor. */}
      <div className={`pca-copilot ${theme.mode === 'dark' ? 'dark' : ''}`} data-variant={props.variant}>
        <CopilotKit
          {...transport}
          enableInspector={false}
          showIntelligenceIndicator={false}
          onError={e => setError(e.type)}
        >
          <Bindings {...props} />
          <CopilotSidebar
            defaultOpen
            labels={{
              modalHeaderTitle: `Chat (${props.variant}) - unverified`,
              chatInputPlaceholder: 'Ask about these players, or change the chart',
              chatDisclaimerText:
                'Prototype. Numbers in chat replies are not verified against the data' +
                (props.variant === 'agui' ? ' unless the server check passed.' : '.'),
              welcomeMessageText: 'Try: "compare Babe Ruth and Barry Bonds"',
            }}
          />
          {error && <div className="pca-copilot-down">Chat error: {error}</div>}
        </CopilotKit>
      </div>
    </ChatBoundary>
  );
}
