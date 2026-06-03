import { useCallback, useRef } from 'react';
import { useAppStore, generateId } from '../lib/store';
import { streamChat } from '../lib/sse';
import { fetchSavings } from '../lib/api';
import type { ChatMessage, ToolCallInfo, TokenUsage, MessageTelemetry } from '../types';

/**
 * useSendMessage — programmatic chat send (text only), reusing the exact SSE +
 * store pipeline as InputArea. Used by the hands-free voice conversation loop so
 * a transcribed utterance goes through the same path (and triggers JarvisChatPage's
 * existing auto-TTS on stream end). Returns the final assistant text.
 *
 * NOTE: intentionally standalone (not a refactor of InputArea) to avoid touching
 * the working manual chat input.
 */
export function useSendMessage() {
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const send = useCallback(async (rawText: string, opts?: { maxTokens?: number }): Promise<string> => {
    const content = rawText.trim();
    const store = useAppStore.getState();
    if (!content || store.streamState.isStreaming) return '';

    const selectedModel = store.selectedModel;
    const { temperature } = store.settings;
    const maxTokens = opts?.maxTokens ?? store.settings.maxTokens;

    let convId = store.activeId;
    if (!convId) convId = store.createConversation(selectedModel);

    const userMsg: ChatMessage = {
      id: generateId(), role: 'user', content, timestamp: Date.now(),
    };
    store.addMessage(convId, userMsg);

    const apiMessages = useAppStore.getState().messages.map((m) => ({
      role: m.role,
      content: m.content,
      ...(m.images && m.images.length > 0 ? { images: m.images } : {}),
    }));

    const assistantMsg: ChatMessage = {
      id: generateId(), role: 'assistant', content: '', timestamp: Date.now(),
    };
    store.addMessage(convId, assistantMsg);

    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      useAppStore.getState().setStreamState({ elapsedMs: Date.now() - startTime });
    }, 100);

    const controller = new AbortController();
    abortRef.current = controller;

    let accumulated = '';
    let usage: TokenUsage | undefined;
    let complexity: { score: number; tier: string; suggested_max_tokens: number } | undefined;
    const toolCalls: ToolCallInfo[] = [];
    let lastFlush = 0;
    let ttftMs: number | undefined;

    useAppStore.getState().setStreamState({
      isStreaming: true, phase: 'Generating...', elapsedMs: 0, activeToolCalls: [], content: '',
    });

    try {
      for await (const sseEvent of streamChat(
        { model: selectedModel, messages: apiMessages, stream: true, temperature, max_tokens: maxTokens },
        controller.signal,
      )) {
        const eventName = sseEvent.event;
        if (eventName === 'agent_turn_start') {
          useAppStore.getState().setStreamState({ phase: 'Agent thinking...' });
        } else if (eventName === 'inference_start') {
          useAppStore.getState().setStreamState({ phase: 'Generating...' });
        } else if (eventName === 'tool_call_start') {
          try {
            const data = JSON.parse(sseEvent.data);
            toolCalls.push({ id: generateId(), tool: data.tool, arguments: data.arguments || '', status: 'running' });
            useAppStore.getState().setStreamState({ phase: `Calling ${data.tool}...`, activeToolCalls: [...toolCalls] });
            useAppStore.getState().updateLastAssistant(convId, accumulated, [...toolCalls]);
          } catch { /* ignore */ }
        } else if (eventName === 'tool_call_end') {
          try {
            const data = JSON.parse(sseEvent.data);
            const tc = toolCalls.find((t) => t.tool === data.tool && t.status === 'running');
            if (tc) { tc.status = data.success ? 'success' : 'error'; tc.latency = data.latency; tc.result = data.result; }
            useAppStore.getState().setStreamState({ phase: 'Generating...', activeToolCalls: [...toolCalls] });
            useAppStore.getState().updateLastAssistant(convId, accumulated, [...toolCalls]);
          } catch { /* ignore */ }
        } else {
          try {
            const data = JSON.parse(sseEvent.data);
            const delta = data.choices?.[0]?.delta;
            if (data.usage) usage = data.usage;
            if (data.complexity) complexity = data.complexity;
            if (delta?.content) {
              if (!ttftMs) ttftMs = Date.now() - startTime;
              accumulated += delta.content;
              useAppStore.getState().setStreamState({ content: accumulated, phase: '' });
              const now = Date.now();
              if (now - lastFlush >= 80) {
                useAppStore.getState().updateLastAssistant(convId, accumulated, toolCalls.length > 0 ? [...toolCalls] : undefined);
                lastFlush = now;
              }
            }
            if (data.choices?.[0]?.finish_reason === 'stop') break;
          } catch { /* ignore */ }
        }
      }
    } catch (err) {
      const e = err as { name?: string; message?: string };
      if (e.name === 'AbortError') {
        if (!accumulated) accumulated = '(Generation stopped)';
      } else {
        accumulated = accumulated || `Error: ${e?.message || String(err)}`;
      }
    } finally {
      if (!accumulated) accumulated = 'No response was generated. Please try again.';
      const totalMs = Date.now() - startTime;
      const CLOUD = ['gpt-', 'o1-', 'o3-', 'o4-', 'claude-', 'gemini-', 'openrouter/', 'MiniMax-', 'chatgpt-'];
      const telemetry: MessageTelemetry = {
        engine: CLOUD.some((p) => selectedModel.startsWith(p)) ? 'cloud' : 'ollama',
        model_id: selectedModel,
        total_ms: totalMs,
        ttft_ms: ttftMs,
        tokens_per_sec: usage?.completion_tokens ? usage.completion_tokens / (totalMs / 1000) : undefined,
        complexity_score: complexity?.score,
        complexity_tier: complexity?.tier,
        suggested_max_tokens: complexity?.suggested_max_tokens,
      };
      useAppStore.getState().updateLastAssistant(
        convId, accumulated, toolCalls.length > 0 ? toolCalls : undefined, usage, telemetry,
      );
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
      useAppStore.getState().resetStream();
      abortRef.current = null;
      fetchSavings().then((d) => useAppStore.getState().setSavings(d)).catch(() => {});
    }
    return accumulated;
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    useAppStore.getState().resetStream();
  }, []);

  return { send, stop };
}
