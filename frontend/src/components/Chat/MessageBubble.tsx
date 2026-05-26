import React, { useState, useMemo, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import 'katex/dist/katex.min.css';
import { Copy, Check, Volume2, VolumeX } from 'lucide-react';
import { AudioPlayer } from './AudioPlayer';
import { ToolCallCard } from './ToolCallCard';
import { XRayFooter } from './XRayFooter';
import type { ChatMessage } from '../../types';
import { getBase } from '../../lib/api';

function stripThinkTags(text: string): string {
  let cleaned = text.replace(/<think>[\s\S]*?<\/think>\s*/gi, '');
  cleaned = cleaned.replace(/^[\s\S]*?<\/think>\s*/i, '');
  return cleaned.trim();
}

interface Props {
  message: ChatMessage;
}

// React-markdown passes nested nodes whose shape is essentially unknown
// (string | number | ReactElement | array of these). `unknown` keeps us
// honest at the property-access boundary below.
function getTextContent(node: unknown): string {
  if (typeof node === 'string' || typeof node === 'number') {
    return String(node);
  }
  if (Array.isArray(node)) {
    return node.map(getTextContent).join('');
  }
  if (node && typeof node === 'object' && 'props' in node) {
    const props = (node as { props?: { children?: unknown } }).props;
    if (props?.children !== undefined) return getTextContent(props.children);
  }
  return '';
}

function CodeBlockPre({ children, ...props }: React.HTMLAttributes<HTMLPreElement>) {
  const [copied, setCopied] = useState(false);
  const codeElement = Array.isArray(children) ? children[0] : children;
  const className = codeElement?.props?.className || '';
  const match = /language-([\w-]+)/.exec(className);
  const lang = match ? match[1] : '';
  const code = getTextContent(codeElement?.props?.children).replace(/\n$/, '');

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="code-block-wrapper relative my-3"
      style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden' }}
    >
      <div
        className="flex items-center justify-between px-4 py-1.5 text-xs"
        style={{ background: 'var(--color-bg-tertiary)', color: 'var(--color-text-tertiary)' }}
      >
        <span className="font-mono">{lang || 'code'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-0.5 rounded transition-colors cursor-pointer"
          style={{ color: 'var(--color-text-tertiary)' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-text-secondary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-text-tertiary)')}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre {...props} style={{ margin: 0, borderRadius: 0 }}>
        {children}
      </pre>
    </div>
  );
}

function CopyMessageButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
      style={{ color: 'var(--color-text-tertiary)' }}
      title="Copy message"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

/** Retire le markdown avant d'envoyer au TTS (évite de lire "dièse dièse", "astérisque"…) */
function stripMarkdownForTTS(text: string): string {
  return text
    .replace(/#{1,6}\s+/g, '')                    // titres
    .replace(/\*\*(.*?)\*\*/gs, '$1')             // gras
    .replace(/\*(.*?)\*/gs, '$1')                 // italique
    .replace(/`{3}[\s\S]*?`{3}/g, '')            // blocs de code — supprimés (pas utile à lire)
    .replace(/`([^`]+)`/g, '$1')                  // code inline
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')      // liens → texte seul
    .replace(/^[-*+]\s/gm, '')                    // listes à puces
    .replace(/^\d+\.\s/gm, '')                    // listes numérotées
    .replace(/^\s*>\s/gm, '')                     // citations
    .replace(/^[-*_]{3,}$/gm, '')                 // séparateurs horizontaux
    .replace(/\|[^\n]+\|/g, '')                   // tableaux
    .replace(/\n{3,}/g, '\n\n')                   // espaces multiples
    .trim();
}

function SpeakButton({ content }: { content: string }) {
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  const handleSpeak = useCallback(async () => {
    // Stop si déjà en train de parler
    if (speaking) {
      audioRef.current?.pause();
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      audioRef.current = null;
      setSpeaking(false);
      return;
    }

    // Bug fix: strip markdown avant TTS + truncate à 4000 chars
    const clean = stripMarkdownForTTS(content).slice(0, 4000);
    if (!clean) return;

    try {
      setSpeaking(true);
      // Bug fix: utilise le backend TTS (Edge ou Kokoro) au lieu de speechSynthesis navigateur
      const res = await fetch(`${getBase()}/v1/tts?text=${encodeURIComponent(clean)}`);
      if (!res.ok) throw new Error(`TTS ${res.status}`);

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      blobUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        URL.revokeObjectURL(url);
        blobUrlRef.current = null;
        audioRef.current = null;
        setSpeaking(false);
      };
      audio.onerror = () => {
        if (blobUrlRef.current) { URL.revokeObjectURL(blobUrlRef.current); blobUrlRef.current = null; }
        audioRef.current = null;
        setSpeaking(false);
      };

      await audio.play();
    } catch {
      setSpeaking(false);
    }
  }, [content, speaking]);

  return (
    <button
      onClick={handleSpeak}
      className="p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
      style={{ color: speaking ? 'var(--color-accent)' : 'var(--color-text-tertiary)' }}
      title={speaking ? 'Arrêter' : 'Écouter JARVIS'}
    >
      {speaking ? <VolumeX size={14} /> : <Volume2 size={14} />}
    </button>
  );
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const cleanContent = useMemo(() => stripThinkTags(message.content), [message.content]);

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div
          className="max-w-[85%] px-4 py-2.5 text-sm leading-relaxed"
          style={{
            background: 'var(--color-user-bubble)',
            color: 'var(--color-user-bubble-text)',
            borderRadius: 'var(--radius-xl) var(--radius-xl) var(--radius-sm) var(--radius-xl)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="group mb-6">
      {/* Tool calls */}
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="mb-3 flex flex-col gap-2">
          {message.toolCalls.map((tc) => (
            <ToolCallCard key={tc.id} toolCall={tc} />
          ))}
        </div>
      )}

      {/* Audio player (e.g. morning digest) */}
      {message.audio?.url && <AudioPlayer src={message.audio.url} />}

      {/* Assistant message */}
      {cleanContent && (
        <div className="prose max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[[rehypeHighlight, { detect: true }], rehypeKatex]}
            components={{
              pre: CodeBlockPre,
            }}
          >
            {cleanContent}
          </ReactMarkdown>
        </div>
      )}

      {/* Footer: copy + speak + x-ray */}
      <div className="flex items-center gap-2 mt-1.5">
        <CopyMessageButton content={cleanContent} />
        <SpeakButton content={cleanContent} />
      </div>
      <XRayFooter usage={message.usage} telemetry={message.telemetry} />
    </div>
  );
}
