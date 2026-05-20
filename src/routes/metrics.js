// ============================================================
// C:\OpenJarvisNexus\src\routes\metrics.js
// Route API pour les métriques système en temps réel
// ============================================================

const express = require('express');
const router  = express.Router();
const si      = require('systeminformation');

// GET /api/metrics
// Retourne CPU, RAM, GPU, et infos Ollama
router.get('/', async (req, res) => {
  try {
    // Lire CPU et RAM en parallèle (plus rapide)
    const [cpuLoad, memInfo, gpuInfo] = await Promise.all([
      si.currentLoad(),       // charge CPU en %
      si.mem(),               // mémoire RAM
      si.graphics()           // infos GPU
    ]);

    // Calculer les valeurs
    const cpuPct    = Math.round(cpuLoad.currentLoad);
    const memTotal  = Math.round(memInfo.total  / (1024 ** 3) * 10) / 10; // GB
    const memUsed   = Math.round(memInfo.active / (1024 ** 3) * 10) / 10; // GB
    const memPct    = Math.round((memInfo.active / memInfo.total) * 100);

    // GPU info (cherche NVIDIA en premier)
    const gpus = gpuInfo.controllers || [];
    const nvidiaGPU = gpus.find(g => g.vendor?.toLowerCase().includes('nvidia'));
    const activeGPU = nvidiaGPU || gpus[0];

    // Récupérer les modèles Ollama actifs
    let ollamaModels = [];
    let ollamaStatus = 'offline';
    try {
      const ollamaRes = await fetch('http://localhost:11434/api/ps');
      const ollamaData = await ollamaRes.json();
      ollamaModels = ollamaData.models || [];
      ollamaStatus = 'online';
    } catch (e) {
      ollamaStatus = 'offline';
    }

    // Réponse JSON
    res.json({
      success: true,
      timestamp: new Date().toISOString(),
      cpu: {
        percent: cpuPct,
        status: cpuPct > 80 ? 'critical' : cpuPct > 60 ? 'warning' : 'normal'
      },
      memory: {
        percent: memPct,
        usedGB:  memUsed,
        totalGB: memTotal,
        status: memPct > 85 ? 'critical' : memPct > 70 ? 'warning' : 'normal'
      },
      gpu: {
        name:      activeGPU?.name    || 'N/A',
        vendor:    activeGPU?.vendor  || 'N/A',
        vramGB:    activeGPU?.vram ? Math.round(activeGPU.vram / 1024 * 10) / 10 : 'N/A',
        tempC:     activeGPU?.temperatureGpu || 'N/A'
      },
      ollama: {
        status: ollamaStatus,
        modelsLoaded: ollamaModels.length,
        models: ollamaModels.map(m => ({
          name: m.name,
          sizeGB: Math.round((m.size || 0) / (1024**3) * 10) / 10
        }))
      }
    });

  } catch (error) {
    console.error('[Metrics] Erreur:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

module.exports = router;