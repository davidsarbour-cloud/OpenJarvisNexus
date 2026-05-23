/**
 * Nexus9 — server.js (vault_graph sidecar)
 *
 * Watcher chokidar sur VAULT_PATH + serveur WebSocket sur VAULT_GRAPH_PORT.
 *
 * Protocole :
 *   server -> client : { type: 'vault:graph',      payload: { nodes, links, stats } }
 *                      { type: 'vault:refreshing', payload: boolean }
 *                      { type: 'vault:syncing',    payload: boolean }
 *                      { type: 'vault:synced',     payload: { ...stats } }
 *   client -> server : { type: 'vault:refresh' }  (rescan graph)
 *                      { type: 'vault:sync' }     (sync backend/vault -> BRAIN)
 */

import { WebSocketServer } from 'ws';
import chokidar from 'chokidar';
import path from 'node:path';
import { parseVault } from './vaultParser.js';
import { syncAll } from './sync-brain.js';
import { routeImports } from './route-imports.js';

const VAULT_PATH = process.env.VAULT_PATH
  ? path.resolve(process.env.VAULT_PATH)
  : 'C:\\OpenJarvisNexus\\backend\\BRAIN\\BRAIN';
const PORT = Number(process.env.VAULT_GRAPH_PORT ?? 8084);
const DEBOUNCE_MS = Number(process.env.VAULT_DEBOUNCE_MS ?? 250);
const REFRESH_INTERVAL_MS = Number(process.env.VAULT_REFRESH_INTERVAL_MS ?? 60 * 60 * 1000);
const BRAIN_SYNC_INTERVAL_MS = Number(process.env.BRAIN_SYNC_INTERVAL_MS ?? 24 * 60 * 60 * 1000);

console.log('[vault_graph] starting');
console.log('[vault_graph] vault:', VAULT_PATH);
console.log('[vault_graph] port:', PORT);
console.log('[vault_graph] hourly refresh:', REFRESH_INTERVAL_MS, 'ms');
console.log('[vault_graph] daily brain sync:', BRAIN_SYNC_INTERVAL_MS, 'ms');

let cache = null;
let scanning = false;
let syncing = false;

const wss = new WebSocketServer({ port: PORT });

function broadcast(msg) {
  const data = JSON.stringify(msg);
  for (const client of wss.clients) {
    if (client.readyState === 1) {
      try { client.send(data); } catch (err) {
        console.warn('[vault_graph] send failed', err);
      }
    }
  }
}

function doRefresh(reason) {
  if (scanning) {
    console.log(`[vault_graph] skip refresh (${reason}) — already scanning`);
    return;
  }
  scanning = true;
  broadcast({ type: 'vault:refreshing', payload: true });
  try {
    cache = parseVault(VAULT_PATH);
    broadcast({ type: 'vault:graph', payload: cache });
    console.log(
      `[vault_graph] (${reason}) ${cache.stats.files} files / ${cache.stats.links} links / ${cache.stats.tags} tags / ${cache.stats.orphans} orphans`,
    );
  } catch (err) {
    console.error('[vault_graph] scan failed', err);
  } finally {
    scanning = false;
    broadcast({ type: 'vault:refreshing', payload: false });
  }
}

function doSync(reason) {
  if (syncing) {
    console.log(`[vault_graph] skip sync (${reason}) — already syncing`);
    return;
  }
  syncing = true;
  broadcast({ type: 'vault:syncing', payload: true });
  try {
    console.log(`[vault_graph] starting brain sync (${reason}) ...`);
    const result = syncAll();
    let routed = null;
    try {
      console.log(`[vault_graph] routing imports (${reason}) ...`);
      routed = routeImports({ dryRun: false });
    } catch (err) {
      console.error('[vault_graph] route-imports failed', err);
    }
    broadcast({ type: 'vault:synced', payload: { ...result, routed } });
    doRefresh(`post-sync ${reason}`);
  } catch (err) {
    console.error('[vault_graph] sync failed', err);
  } finally {
    syncing = false;
    broadcast({ type: 'vault:syncing', payload: false });
  }
}

doRefresh('initial');

wss.on('listening', () => {
  console.log(`[vault_graph] ws listening on ws://localhost:${PORT}`);
});

wss.on('connection', (socket, req) => {
  console.log('[vault_graph] client connected', req.socket.remoteAddress);
  if (cache) {
    try {
      socket.send(JSON.stringify({ type: 'vault:graph', payload: cache }));
    } catch (err) {
      console.warn('[vault_graph] initial send failed', err);
    }
  }
  socket.on('message', (raw) => {
    let msg;
    try { msg = JSON.parse(raw.toString()); } catch { return; }
    if (!msg) return;
    if (msg.type === 'vault:refresh') {
      doRefresh('manual');
    } else if (msg.type === 'vault:sync') {
      doSync('manual');
    }
  });
});

let debounceTimer = null;
function scheduleReparse(reason) {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    doRefresh(reason);
  }, DEBOUNCE_MS);
}

const watcher = chokidar.watch(VAULT_PATH, {
  ignored: (p) => /(^|[/\\])(\.git|\.obsidian|\.trash|node_modules)([/\\]|$)/.test(p),
  persistent: true,
  ignoreInitial: true,
  awaitWriteFinish: { stabilityThreshold: 150, pollInterval: 50 },
});

watcher
  .on('add',    (p) => p.endsWith('.md') && scheduleReparse(`add ${path.basename(p)}`))
  .on('change', (p) => p.endsWith('.md') && scheduleReparse(`change ${path.basename(p)}`))
  .on('unlink', (p) => p.endsWith('.md') && scheduleReparse(`unlink ${path.basename(p)}`))
  .on('error',  (err) => console.error('[vault_graph] watcher error', err))
  .on('ready',  () => console.log('[vault_graph] watcher ready'));

const hourly    = setInterval(() => doRefresh('hourly'), REFRESH_INTERVAL_MS);
const dailySync = setInterval(() => doSync('daily'),     BRAIN_SYNC_INTERVAL_MS);

async function shutdown(signal) {
  console.log(`[vault_graph] ${signal} received, shutting down`);
  clearInterval(hourly);
  clearInterval(dailySync);
  try { await watcher.close(); } catch { /* noop */ }
  for (const client of wss.clients) {
    try { client.close(); } catch { /* noop */ }
  }
  wss.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 1500).unref();
}

process.on('SIGINT',  () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
