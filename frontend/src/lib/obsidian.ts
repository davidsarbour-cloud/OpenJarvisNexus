/**
 * Ouvre une note du vault Brain dans Obsidian via le protocole `obsidian://`.
 *
 * Pourquoi une ancre <a>.click() et pas window.open(url, '_self') :
 * Chromium / Brave ignorent SILENCIEUSEMENT window.open vers un schéma non-http
 * (le lien "ne fait rien"). Un clic d'ancre déclenché dans le geste utilisateur
 * lance correctement le handler de protocole externe (Obsidian). Le protocole
 * lui-même est valide (vérifié : `start obsidian://…` ouvre bien la note).
 *
 * Le vault par défaut "BRAIN" correspond au dossier du vault
 * (C:\OpenJarvisNexus\backend\BRAIN\BRAIN -> nom de vault = "BRAIN").
 */
export const BRAIN_VAULT = 'BRAIN';

export function openObsidian(path: string, vault: string = BRAIN_VAULT): void {
  const url = `obsidian://open?vault=${encodeURIComponent(vault)}&file=${encodeURIComponent(path)}`;
  const a = document.createElement('a');
  a.href = url;
  a.rel = 'noopener';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  a.remove();
}
