/**
 * Tests for wsBus — the shared WebSocket subscription multiplexer.
 *
 * We mock `connectWs` so the bus can be exercised without touching a
 * real socket. Each test resets the module state by re-importing via
 * `vi.resetModules()` so global subscriber sets don't bleed across
 * cases.
 */
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import type { WsClientOptions, WsMessage } from './ws';

interface BusModule {
  wsBus: typeof import('./wsBus').wsBus;
}

let capturedOptions: WsClientOptions | null = null;
const mockClose = vi.fn();

vi.mock('./ws', () => ({
  connectWs: vi.fn((opts: WsClientOptions) => {
    capturedOptions = opts;
    return { close: mockClose, state: () => 'open' as const };
  }),
}));

async function freshBus(): Promise<BusModule> {
  vi.resetModules();
  capturedOptions = null;
  mockClose.mockClear();
  return await import('./wsBus');
}

function emit(msg: WsMessage) {
  capturedOptions?.onMessage?.(msg);
}

describe('wsBus', () => {
  beforeEach(() => { capturedOptions = null; });
  afterEach(()  => { vi.clearAllMocks(); });

  it('opens exactly one underlying socket regardless of subscriber count', async () => {
    const { wsBus } = await freshBus();
    const { connectWs } = await import('./ws');
    const cb = vi.fn();
    wsBus.subscribe(() => true, cb);
    wsBus.subscribe(() => true, cb);
    wsBus.subscribe(() => true, cb);
    expect((connectWs as Mock).mock.calls.length).toBe(1);
  });

  it('routes events to subscribers whose filter matches', async () => {
    const { wsBus } = await freshBus();
    const agentsCb = vi.fn();
    const jobsCb   = vi.fn();
    wsBus.subscribe((e) => e.source === 'snapshot/agents', agentsCb);
    wsBus.subscribe((e) => e.source === 'snapshot/jobs',   jobsCb);

    emit({ type: 'event', data: { source: 'snapshot/agents', msg: 'snapshot' } });
    emit({ type: 'event', data: { source: 'snapshot/jobs',   msg: 'snapshot' } });
    emit({ type: 'event', data: { source: 'snapshot/agents', msg: 'snapshot' } });

    expect(agentsCb).toHaveBeenCalledTimes(2);
    expect(jobsCb).toHaveBeenCalledTimes(1);
  });

  it('does not deliver events to mismatching subscribers', async () => {
    const { wsBus } = await freshBus();
    const cb = vi.fn();
    wsBus.subscribe((e) => e.source === 'snapshot/budget', cb);
    emit({ type: 'event', data: { source: 'snapshot/agents', msg: 'snapshot' } });
    expect(cb).not.toHaveBeenCalled();
  });

  it('replays history on hello frames so late subscribers catch up', async () => {
    const { wsBus } = await freshBus();
    const cb = vi.fn();
    wsBus.subscribe((e) => e.source === 'snapshot/agents', cb);
    emit({
      type: 'hello',
      subscribers: 1,
      history: [
        { source: 'snapshot/agents', msg: 'old', data: { x: 1 } },
        { source: 'snapshot/jobs',   msg: 'old' },          // filtered out
        { source: 'snapshot/agents', msg: 'newer', data: { x: 2 } },
      ],
    });
    expect(cb).toHaveBeenCalledTimes(2);
    expect((cb.mock.calls[0][0] as { data: { x: number } }).data.x).toBe(1);
    expect((cb.mock.calls[1][0] as { data: { x: number } }).data.x).toBe(2);
  });

  it('unsubscribe stops further deliveries', async () => {
    const { wsBus } = await freshBus();
    const cb = vi.fn();
    const unsub = wsBus.subscribe((e) => e.source === 'snapshot/agents', cb);
    emit({ type: 'event', data: { source: 'snapshot/agents', msg: 'first' } });
    unsub();
    emit({ type: 'event', data: { source: 'snapshot/agents', msg: 'second' } });
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it('ignores ping frames and malformed messages without crashing', async () => {
    const { wsBus } = await freshBus();
    const cb = vi.fn();
    wsBus.subscribe(() => true, cb);
    emit({ type: 'ping', ts: Date.now() });
    emit({ type: 'error', msg: 'something broke' });
    expect(cb).not.toHaveBeenCalled();
  });

  it('state listener fires immediately with the current state', async () => {
    const { wsBus } = await freshBus();
    const stateCb = vi.fn();
    wsBus.onState(stateCb);
    // onState fires once on subscription with the cached state.
    expect(stateCb).toHaveBeenCalledTimes(1);
  });
});
