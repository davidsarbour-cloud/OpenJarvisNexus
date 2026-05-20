html = open('Nexus9.html', encoding='utf-8').read()

NEW_MODULE = r'''<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass}    from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';

/* ═══════════════════════════════════════════════
   NEXUS X9 — IMMERSIVE TOP-DOWN HQ MAP
   Space station command center, game-style
   ═══════════════════════════════════════════════ */

const C   = document.getElementById('cv3d');
const W   = () => C.clientWidth  || C.parentElement?.clientWidth  || 900;
const H   = () => C.clientHeight || C.parentElement?.clientHeight || 600;

/* ── Renderer ── */
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type    = THREE.PCFSoftShadowMap;
renderer.toneMapping       = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;
C.appendChild(renderer.domElement);
requestAnimationFrame(()=>{ renderer.setSize(W(),H()); composer.setSize(W(),H()); });

/* ── Scene & Fog ── */
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x030608);
scene.fog = new THREE.Fog(0x030608, 22, 48);

/* ── Camera — top-down game angle ── */
const camera = new THREE.PerspectiveCamera(52, W()/H(), 0.1, 120);
camera.position.set(0, 20, 9);
camera.lookAt(0, 0, 0);

/* ── Post-processing ── */
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W(),H()), 1.2, 0.5, 0.12);
composer.addPass(bloom);

/* ── Controls ── */
const ctrl = new OrbitControls(camera, renderer.domElement);
ctrl.enableDamping  = true;
ctrl.dampingFactor  = 0.06;
ctrl.minDistance    = 7;
ctrl.maxDistance    = 38;
ctrl.minPolarAngle  = 0.15;
ctrl.maxPolarAngle  = Math.PI / 2.4;
ctrl.target.set(0, 0, 0);

/* ── Global lights ── */
scene.add(new THREE.AmbientLight(0x08101e, 3));
const sun = new THREE.DirectionalLight(0x102030, 0.6);
sun.position.set(5, 18, 8);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 1;
sun.shadow.camera.far  = 60;
sun.shadow.camera.left = sun.shadow.camera.bottom = -25;
sun.shadow.camera.right = sun.shadow.camera.top   = 25;
scene.add(sun);

/* ══════════════════════════════════════════════════
   MATERIAL LIBRARY
══════════════════════════════════════════════════ */
const M = {
  floor:     new THREE.MeshStandardMaterial({color:0x0b1520, roughness:0.8, metalness:0.5}),
  wall:      new THREE.MeshStandardMaterial({color:0x0d1c2a, roughness:0.7, metalness:0.6}),
  metal:     new THREE.MeshStandardMaterial({color:0x1a2a3a, roughness:0.4, metalness:0.9}),
  darkMetal: new THREE.MeshStandardMaterial({color:0x080e16, roughness:0.3, metalness:0.95}),
  corridor:  new THREE.MeshStandardMaterial({color:0x060d18, roughness:0.9, metalness:0.3}),
  grate:     new THREE.MeshStandardMaterial({color:0x0a1520, roughness:0.6, metalness:0.8, wireframe:false}),
  glass:     new THREE.MeshStandardMaterial({color:0x003344, roughness:0.0, metalness:0.1, transparent:true, opacity:0.35}),
};
function neon(hex, ei=2.5) {
  return new THREE.MeshStandardMaterial({color:hex, emissive:hex, emissiveIntensity:ei, roughness:0.3, metalness:0.2});
}
function panel(hex, ei=0.6) {
  return new THREE.MeshStandardMaterial({color:0x0a1828, emissive:hex, emissiveIntensity:ei, roughness:0.5, metalness:0.7});
}

/* ══════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════ */
function box(w,h,d,mat,rx=0,ry=0,rz=0,x=0,y=0,z=0,shadow=true){
  const m = new THREE.Mesh(new THREE.BoxGeometry(w,h,d), mat);
  m.rotation.set(rx,ry,rz); m.position.set(x,y,z);
  if(shadow){m.castShadow=true; m.receiveShadow=true;}
  return m;
}
function cyl(rt,rb,h,seg,mat,x=0,y=0,z=0){
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt,rb,h,seg), mat);
  m.position.set(x,y,z); m.castShadow=true; return m;
}
function ring(r,tube,seg,mat,x=0,y=0,z=0,rx=0){
  const m = new THREE.Mesh(new THREE.TorusGeometry(r,tube,8,seg), mat);
  m.position.set(x,y,z); m.rotation.x=rx; return m;
}
function pLight(hex,intensity,dist,x,y,z,shadows=false){
  const l = new THREE.PointLight(hex, intensity, dist);
  l.position.set(x,y,z);
  if(shadows){ l.castShadow=true; l.shadow.mapSize.set(512,512); }
  return l;
}
function sprite(text, color='#00e8ff', sub=''){
  const cv=document.createElement('canvas'); cv.width=256; cv.height=80;
  const cx=cv.getContext('2d');
  cx.font='bold 20px Courier New'; cx.fillStyle=color; cx.textAlign='center';
  cx.shadowColor=color; cx.shadowBlur=10;
  cx.fillText(text.toUpperCase(), 128, 28);
  if(sub){ cx.font='10px Courier New'; cx.fillStyle='rgba(160,220,255,0.7)'; cx.shadowBlur=0; cx.fillText(sub,128,50); }
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(cv),transparent:true,depthWrite:false,sizeAttenuation:true}));
  sp.scale.set(2.8,1.0,1); return sp;
}

/* ══════════════════════════════════════════════════
   GRID CONFIG  3×3
══════════════════════════════════════════════════ */
const STEP = 5.6;   // center-to-center
const RS   = 4.0;   // room inner size
const WH   = 1.2;   // wall height
const CW   = STEP - RS; // corridor width = 1.6
const CWH  = 0.7;   // corridor wall height (lower than rooms)

function roomCenter(row,col){ return [(col-1)*STEP, (row-1)*STEP]; }

/* ══════════════════════════════════════════════════
   ROOM BUILDER
══════════════════════════════════════════════════ */
function buildRoom(row, col, agent, theme){
  const [cx,cz] = roomCenter(row,col);
  const G = new THREE.Group(); G.position.set(cx,0,cz);
  scene.add(G);

  const col3 = new THREE.Color(agent.color);
  const hex  = parseInt(agent.color.replace('#',''),16);

  /* -- Floor panel grid ── */
  const floorMat = new THREE.MeshStandardMaterial({
    color:0x0b1824, roughness:0.85, metalness:0.6,
    emissive: col3, emissiveIntensity: 0.03
  });
  const floor = box(RS,0.14,RS,floorMat,0,0,0,0,-0.07,0);
  G.add(floor);

  /* -- Floor panel lines (raised strips) ── */
  const lineM = new THREE.MeshStandardMaterial({color:0x0e1f2f, roughness:0.5, metalness:0.9});
  for(let i=-1;i<=1;i++){
    G.add(box(RS,0.02,0.05,lineM,0,0,0,0,0,i*1.2));
    G.add(box(0.05,0.02,RS,lineM,0,0,0,i*1.2,0,0));
  }

  /* -- Walls (4 sides, partial for visibility) ── */
  const wallM = M.wall.clone(); wallM.emissive = col3; wallM.emissiveIntensity = 0.04;
  const wallTop = WH/2 + 0.0;
  const hs = RS/2;
  [ [RS+0.12, WH, 0.12, 0, wallTop, hs],
    [RS+0.12, WH, 0.12, 0, wallTop,-hs],
    [0.12, WH, RS, hs, wallTop, 0],
    [0.12, WH, RS,-hs, wallTop, 0],
  ].forEach(([w,h,d,x,y,z])=>G.add(box(w,h,d,wallM,0,0,0,x,y,z)));

  /* -- Wall trim (neon strip at top of wall) ── */
  const trimM = neon(hex, agent.on ? 1.4 : 0.3);
  [ [RS+0.12,0.04,0.06,0,WH+0.02, hs],
    [RS+0.12,0.04,0.06,0,WH+0.02,-hs],
    [0.06,0.04,RS, hs,WH+0.02,0],
    [0.06,0.04,RS,-hs,WH+0.02,0],
  ].forEach(([w,h,d,x,y,z])=>G.add(box(w,h,d,trimM,0,0,0,x,y,z)));

  /* -- Corner pillars ── */
  const pillarM = M.darkMetal.clone();
  [[-hs,-hs],[hs,-hs],[hs,hs],[-hs,hs]].forEach(([px,pz])=>{
    const p = box(0.2,WH+0.1,0.2,pillarM,0,0,0,px,WH/2,pz);
    G.add(p);
    // Corner light accents
    const cl = box(0.06,0.06,0.06,neon(hex,agent.on?2:0.4),0,0,0,px,WH,pz);
    G.add(cl);
  });

  /* -- Point light ── */
  const light = pLight(hex, agent.on?2.5:0.2, 8, 0, 2.5, 0, false);
  G.add(light);

  /* -- Overhead panel light ── */
  const overheadM = new THREE.MeshStandardMaterial({
    color:0xffffff, emissive:col3, emissiveIntensity: agent.on?0.8:0.1
  });
  G.add(box(1.4,0.06,0.6, overheadM, 0,0,0, 0, WH+0.06, 0));

  /* ─── THEME-SPECIFIC INTERIOR DETAILS ─── */
  theme(G, agent, hex, col3);

  /* -- Label sprite ── */
  const lbl = sprite(agent.name, agent.color, agent.state);
  lbl.position.set(0, WH+1.1, 0);
  G.add(lbl);

  return {group:G, light, trimM, agent};
}

/* ══════════════════════════════════════════════════
   ROOM THEMES
══════════════════════════════════════════════════ */
// Holographic orb (spinning ring stack)
function holoOrb(G, x, y, z, hex, size=0.3){
  const g = new THREE.Group(); g.position.set(x,y,z);
  [size, size*0.7, size*0.4].forEach((r,i)=>{
    const t = ring(r,0.018,32,neon(hex,2.5),0,0,0, i*Math.PI/3);
    g.add(t);
  });
  const core = cyl(size*0.15,size*0.15,size*0.05,8,neon(hex,4));
  g.add(core);
  scene.add(g); G.userData.orbs = G.userData.orbs||[]; G.userData.orbs.push(g);
  return g;
}
// Console desk
function console_(G,x,z,w,hex,ry=0){
  const g = new THREE.Group(); g.position.set(x,0,z); g.rotation.y=ry;
  g.add(box(w,0.55,0.7,M.darkMetal,0,0,0,0,0.275,0));         // body
  g.add(box(w,0.06,0.75,M.metal,0,0,0,0,0.58,0.04));            // desk surface
  g.add(box(w*0.85,0.28,0.5,panel(hex,0.7),0,0,0,0,0.82,0.05)); // screen
  g.add(box(w*0.85,0.02,0.5,neon(hex,1.8),0,0,0,0,0.97,0.05));  // screen glow strip
  G.add(g);
  return g;
}
// Data tower / server rack
function serverRack(G,x,z,hex,ry=0){
  const g=new THREE.Group(); g.position.set(x,0,z); g.rotation.y=ry;
  g.add(box(0.4,1.4,0.3,M.darkMetal,0,0,0,0,0.7,0));
  for(let i=0;i<5;i++){
    g.add(box(0.36,0.12,0.26,panel(hex,0.4+i*0.1),0,0,0,0,0.2+i*0.24,0));
    g.add(box(0.3,0.025,0.02,neon(hex,1.5),0,0,0,0,0.2+i*0.24,0.16));
  }
  G.add(g);
}
// Holographic table display
function holoTable(G,x,z,hex){
  const g=new THREE.Group(); g.position.set(x,0,z);
  g.add(box(1.0,0.08,0.6,M.metal,0,0,0,0,0.44,0));
  g.add(cyl(0.06,0.06,0.44,6,M.darkMetal,0,0.22,0));
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.9,0.55),
    new THREE.MeshBasicMaterial({color:hex,transparent:true,opacity:0.18,side:THREE.DoubleSide}));
  screen.rotation.x=-Math.PI/2; screen.position.set(0,0.5,0);
  g.add(screen);
  const border = ring(0.52,0.02,32,neon(hex,2),0,0.5,0,-Math.PI/2);
  border.scale.set(1.0,0.6,1); g.add(border);
  G.add(g);
}

// ROOM 0: Claude — AI Core
function theme_claude(G,a,hex){
  console_(G,-1.1,0.3,0.9,hex);
  console_(G,1.1,-0.3,0.9,hex,Math.PI);
  holoOrb(G,0,1.0,0,hex,0.5);
  holoTable(G,0,0.7,hex);
  serverRack(G,-1.3,-1.1,hex);
  serverRack(G,1.3,-1.1,hex);
  // Data stream particles
  const pts=[]; for(let i=0;i<80;i++) pts.push((Math.random()-.5)*3,(Math.random()-.5)*2+0.5,(Math.random()-.5)*3);
  const pg=new THREE.BufferGeometry(); pg.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));
  G.add(new THREE.Points(pg,new THREE.PointsMaterial({color:hex,size:0.05,transparent:true,opacity:0.6})));
}

// ROOM 1: Architecte — Planning
function theme_arch(G,a,hex){
  holoTable(G,-0.4,0.3,hex);
  console_(G,1.2,0,0.7,hex,-Math.PI/2);
  // Blueprint grid on floor
  const bpM=new THREE.MeshBasicMaterial({color:hex,transparent:true,opacity:0.06,side:THREE.DoubleSide});
  for(let i=-1;i<=1;i++) for(let j=-1;j<=1;j++){
    const line=new THREE.Mesh(new THREE.PlaneGeometry(RS*0.8,0.015),bpM.clone());
    line.rotation.x=-Math.PI/2; line.position.set(0,0.08,i*0.9); G.add(line);
    const line2=new THREE.Mesh(new THREE.PlaneGeometry(0.015,RS*0.8),bpM.clone());
    line2.rotation.x=-Math.PI/2; line2.position.set(j*0.9,0.08,0); G.add(line2);
  }
  holoOrb(G,0,1.2,0,hex,0.38);
  serverRack(G,-1.3,1.0,hex,Math.PI/4);
}

// ROOM 2: Laboratoire — Research
function theme_lab(G,a,hex){
  console_(G,0,1.0,1.6,hex);
  // Test cylinders
  [[-0.9,0.6],[0,0.6],[0.9,0.6]].forEach(([x,z])=>{
    G.add(cyl(0.08,0.08,0.45,8,neon(hex,1.2),x,0.23,z));
    G.add(cyl(0.09,0.09,0.02,8,neon(hex,2.5),x,0.47,z));
  });
  holoOrb(G,0,1.0,-0.5,hex,0.42);
  serverRack(G,1.3,0.5,hex);
}

// ROOM 3: Surveillance — Security
function theme_surv(G,a,hex){
  // Monitor wall
  for(let i=0;i<3;i++){
    G.add(box(0.55,0.38,0.06,panel(hex,0.8),0,0,0,-0.7+i*0.7,WH-0.2,-RS/2+0.1));
    G.add(box(0.53,0.02,0.02,neon(hex,2),0,0,0,-0.7+i*0.7,WH-0.02,-RS/2+0.1));
  }
  console_(G,0,-0.5,1.4,hex);
  holoOrb(G,0,0.9,0.5,hex,0.35);
  // Alert strip (red warning)
  G.add(box(RS,0.03,0.03,neon(hex,1.5),0,0,0,0,0.02,RS/2-0.08));
}

// ROOM 4: Mémoire — Storage
function theme_mem(G,a,hex){
  // Storage towers
  [[-1.2,-0.8],[-1.2,0.4],[1.2,-0.8],[1.2,0.4]].forEach(([x,z])=>serverRack(G,x,z,hex));
  holoTable(G,0,0,hex);
  holoOrb(G,0,1.2,0,hex,0.45);
}

// ROOM 5: Opérateur — Comms
function theme_ops(G,a,hex){
  console_(G,-0.8,-0.2,0.8,hex,Math.PI/6);
  console_(G,0.8,-0.2,0.8,hex,-Math.PI/6);
  holoOrb(G,0,1.1,0.4,hex,0.4);
  // Comms dish (torus)
  G.add(ring(0.6,0.06,24,neon(hex,2),0,1.5,-0.8,-Math.PI/3));
  G.add(cyl(0.04,0.04,0.8,6,M.darkMetal,0,0.9,-0.8));
}

// ROOM 6: Zone Locale — Ollama
function theme_ollama(G,a,hex){
  // Central processing column
  G.add(cyl(0.35,0.35,1.4,6,M.darkMetal,0,0.7,0));
  G.add(ring(0.5,0.04,24,neon(hex,2.2),0,0.9,0,-Math.PI/2));
  G.add(ring(0.5,0.04,24,neon(hex,1.5),0,1.2,0,-Math.PI/2));
  serverRack(G,-1.1,0.8,hex);
  serverRack(G,1.1,0.8,hex);
  holoOrb(G,0,1.6,0,hex,0.52);
}

// ROOM 7: Recherche
function theme_research(G,a,hex){
  holoTable(G,-0.4,-0.2,hex);
  console_(G,1.1,0.5,0.8,hex,-Math.PI/4);
  serverRack(G,-1.2,0.8,hex);
  holoOrb(G,0.3,1.0,-0.6,hex,0.38);
  const pts2=[]; for(let i=0;i<50;i++) pts2.push((Math.random()-.5)*2.5,Math.random()*1.5,(Math.random()-.5)*2.5);
  const pg2=new THREE.BufferGeometry(); pg2.setAttribute('position',new THREE.Float32BufferAttribute(pts2,3));
  G.add(new THREE.Points(pg2,new THREE.PointsMaterial({color:hex,size:0.07,transparent:true,opacity:0.5})));
}

// ROOM 8: Extra / inactive
function theme_idle(G,a,hex){
  console_(G,0,0,1.2,hex);
  serverRack(G,1.1,-0.8,hex);
}

const THEMES=[theme_claude,theme_arch,theme_lab,theme_surv,theme_mem,theme_ops,theme_ollama,theme_research,theme_idle];

/* ══════════════════════════════════════════════════
   CORRIDOR BUILDER
══════════════════════════════════════════════════ */
function buildCorridor(x,z,dir){
  const G=new THREE.Group(); G.position.set(x,0,z); scene.add(G);
  const [cLen,cWid] = dir==='x'?[CW,RS*0.38]:[RS*0.38,CW];
  // Floor
  const floorC=box(cLen,0.1,cWid,M.corridor,0,0,0,0,-0.05,0); G.add(floorC);
  // Warning stripes on floor
  const stripeM=new THREE.MeshStandardMaterial({color:0x1a1200,emissive:0xffaa00,emissiveIntensity:0.15});
  for(let i=0;i<3;i++){
    const sx=dir==='x'?CW*(-0.3+i*0.3):0, sz=dir==='z'?CW*(-0.3+i*0.3):0;
    const sw=dir==='x'?0.12:cLen*0.8, sd=dir==='x'?cWid*0.7:0.12;
    G.add(box(sw,0.02,sd,stripeM,0,0,0,sx,0.01,sz));
  }
  // Walls on corridor sides
  const wallH=CWH, wM=M.wall.clone();
  if(dir==='x'){
    G.add(box(cLen,wallH,0.1,wM,0,0,0, 0,wallH/2,cWid/2));
    G.add(box(cLen,wallH,0.1,wM,0,0,0, 0,wallH/2,-cWid/2));
    // Wall trim strips
    G.add(box(cLen,0.03,0.05,neon(0x003355,0.8),0,0,0,0,wallH-0.01,cWid/2));
    G.add(box(cLen,0.03,0.05,neon(0x003355,0.8),0,0,0,0,wallH-0.01,-cWid/2));
    // Floor edge strips
    G.add(box(cLen,0.03,0.04,neon(0x001122,0.5),0,0,0,0,0.02,cWid/2-0.05));
    G.add(box(cLen,0.03,0.04,neon(0x001122,0.5),0,0,0,0,0.02,-cWid/2+0.05));
  } else {
    G.add(box(0.1,wallH,cWid,wM,0,0,0, cLen/2,wallH/2,0));
    G.add(box(0.1,wallH,cWid,wM,0,0,0,-cLen/2,wallH/2,0));
    G.add(box(0.05,0.03,cWid,neon(0x003355,0.8),0,0,0, cLen/2-0.02,wallH-0.01,0));
    G.add(box(0.05,0.03,cWid,neon(0x003355,0.8),0,0,0,-cLen/2+0.02,wallH-0.01,0));
    G.add(box(0.04,0.03,cWid,neon(0x001122,0.5),0,0,0, cLen/2-0.06,0.02,0));
    G.add(box(0.04,0.03,cWid,neon(0x001122,0.5),0,0,0,-cLen/2+0.06,0.02,0));
  }
  // Emergency light (amber blink)
  const eLight=pLight(0xff6600,0.4,2.5,0,0.5,0);
  G.add(eLight);
  G.userData.eLight=eLight;
  return G;
}

/* ══════════════════════════════════════════════════
   BASE PLATE + OUTER WALLS
══════════════════════════════════════════════════ */
const BASE_S = STEP*3+1.0;
const baseMat=new THREE.MeshStandardMaterial({color:0x040810,roughness:0.95,metalness:0.3});
const baseFloor=box(BASE_S,0.08,BASE_S,baseMat,0,0,0,0,-0.14,0);
baseFloor.receiveShadow=true; scene.add(baseFloor);

// Outer border glow
const outerTrimM=neon(0x001e3a,0.6);
[ [BASE_S+0.12,0.05,0.1,0,0,BASE_S/2],
  [BASE_S+0.12,0.05,0.1,0,0,-BASE_S/2],
  [0.1,0.05,BASE_S, BASE_S/2,0,0],
  [0.1,0.05,BASE_S,-BASE_S/2,0,0],
].forEach(([w,h,d,x,y,z])=>scene.add(box(w,h,d,outerTrimM,0,0,0,x,y,z)));

// Outer walls
const outerWallM=new THREE.MeshStandardMaterial({color:0x060d18,roughness:0.7,metalness:0.6});
[ [BASE_S+0.12,1.8,0.25,0,0.9, BASE_S/2],
  [BASE_S+0.12,1.8,0.25,0,0.9,-BASE_S/2],
  [0.25,1.8,BASE_S, BASE_S/2,0.9,0],
  [0.25,1.8,BASE_S,-BASE_S/2,0.9,0],
].forEach(([w,h,d,x,y,z])=>scene.add(box(w,h,d,outerWallM,0,0,0,x,y,z)));

/* ══════════════════════════════════════════════════
   BUILD EVERYTHING
══════════════════════════════════════════════════ */

// Build Jarvis center room
function buildJarvisCenter(){
  const G=new THREE.Group(); G.position.set(0,0,0); scene.add(G);
  const floorJ=new THREE.MeshStandardMaterial({color:0x061420,roughness:0.8,metalness:0.6,emissive:0x003366,emissiveIntensity:0.12});
  G.add(box(RS,0.14,RS,floorJ,0,0,0,0,-0.07,0));
  // Hex floor pattern
  for(let r=0;r<6;r++){
    const a=r*Math.PI/3;
    const hx=Math.cos(a)*1.3, hz=Math.sin(a)*1.3;
    G.add(box(0.06,0.02,1.0,neon(0x00aaff,1.0),0,0,0,hx,0,hz));
  }
  // Walls
  const wJ=M.wall.clone(); wJ.emissive=new THREE.Color(0x002244); wJ.emissiveIntensity=0.12;
  const hs=RS/2;
  [[RS+0.12,WH,0.12,0,WH/2,hs],[RS+0.12,WH,0.12,0,WH/2,-hs],
   [0.12,WH,RS,hs,WH/2,0],[0.12,WH,RS,-hs,WH/2,0]].forEach(([w,h,d,x,y,z])=>G.add(box(w,h,d,wJ,0,0,0,x,y,z)));
  // Wall trims
  [[RS+0.12,0.05,0.07,0,WH+0.025,hs],[RS+0.12,0.05,0.07,0,WH+0.025,-hs],
   [0.07,0.05,RS,hs,WH+0.025,0],[0.07,0.05,RS,-hs,WH+0.025,0]].forEach(([w,h,d,x,y,z])=>G.add(box(w,h,d,neon(0x00ccff,1.6),0,0,0,x,y,z)));
  // Central holographic core
  G.add(cyl(0.22,0.22,1.8,6,new THREE.MeshStandardMaterial({color:0x001833,metalness:0.9,roughness:0.2}),0,0.9,0));
  G.add(ring(0.32,0.04,32,neon(0x00e8ff,3),0,1.0,0,-Math.PI/2));
  G.add(ring(0.4,0.03,32,neon(0x0066ff,2),0,1.3,0,-Math.PI/6));
  G.add(ring(0.28,0.03,32,neon(0x00ffcc,2.5),0,0.7,0,Math.PI/3));
  // Core light
  const coreLight=pLight(0x00ccff,5,10,0,2,0,true);
  G.add(coreLight);
  // Label
  const lbl=sprite('JARVIS','#00e8ff','NEXUS CORE');
  lbl.position.set(0,WH+1.2,0); G.add(lbl);
  // Corner pillars
  [[-hs,-hs],[hs,-hs],[hs,hs],[-hs,hs]].forEach(([px,pz])=>{
    G.add(box(0.2,WH+0.15,0.2,M.darkMetal,0,0,0,px,WH/2,pz));
    G.add(box(0.07,0.07,0.07,neon(0x00e8ff,2.5),0,0,0,px,WH+0.04,pz));
  });
  return {group:G, coreLight, rings:G.children.filter(c=>c.type==='Mesh'&&c.geometry.type==='TorusGeometry')};
}
const jarvis=buildJarvisCenter();

// Build corridor network
const corridors=[];
// Horizontal corridors
for(let r=0;r<3;r++) for(let c=0;c<2;c++){
  const [x1,z1]=roomCenter(r,c), [x2,z2]=roomCenter(r,c+1);
  corridors.push(buildCorridor((x1+x2)/2,(z1+z2)/2,'x'));
}
// Vertical corridors
for(let r=0;r<2;r++) for(let c=0;c<3;c++){
  const [x1,z1]=roomCenter(r,c), [x2,z2]=roomCenter(r+1,c);
  corridors.push(buildCorridor((x1+x2)/2,(z1+z2)/2,'z'));
}

// Build agent rooms
const CELL_MAP=[[0,0],[0,1],[0,2],[1,0],[1,2],[2,0],[2,1],[2,2]];
const ROOMS=[];
function buildRooms(){
  if(!window.AGENTS?.length){ setTimeout(buildRooms,200); return; }
  CELL_MAP.forEach(([r,c],i)=>{
    const agent=window.AGENTS[i]||{id:`empty${i}`,name:'OFFLINE',color:'#0a1828',on:false,state:'OFFLINE',acts:0,role:'Offline'};
    const theme=THEMES[i]||theme_idle;
    ROOMS.push(buildRoom(r,c,agent,theme));
  });
}
buildRooms();

/* ══════════════════════════════════════════════════
   AMBIENT PARTICLES (dust / atmosphere)
══════════════════════════════════════════════════ */
const dustPts=new Float32Array(600*3);
for(let i=0;i<600*3;i+=3){dustPts[i]=(Math.random()-.5)*BASE_S;dustPts[i+1]=Math.random()*4;dustPts[i+2]=(Math.random()-.5)*BASE_S;}
const dustGeo=new THREE.BufferGeometry(); dustGeo.setAttribute('position',new THREE.Float32BufferAttribute(dustPts,3));
const dustMesh=new THREE.Points(dustGeo,new THREE.PointsMaterial({color:0x224466,size:0.04,transparent:true,opacity:0.35,sizeAttenuation:true}));
scene.add(dustMesh);

/* ══════════════════════════════════════════════════
   RAYCASTER
══════════════════════════════════════════════════ */
const raycaster=new THREE.Raycaster();
const mouse=new THREE.Vector2(-9,-9);
renderer.domElement.addEventListener('mousemove',e=>{
  const rc=renderer.domElement.getBoundingClientRect();
  mouse.x=((e.clientX-rc.left)/rc.width)*2-1;
  mouse.y=-((e.clientY-rc.top)/rc.height)*2+1;
});
renderer.domElement.addEventListener('click',()=>{ if(window.hovered&&window.focusCard) window.focusCard(window.hovered.id); });

/* ══════════════════════════════════════════════════
   RESIZE
══════════════════════════════════════════════════ */
function onResize(){
  const w=W(),h=H();
  camera.aspect=w/h; camera.updateProjectionMatrix();
  renderer.setSize(w,h); composer.setSize(w,h);
}
window._nx9resize=onResize;
new ResizeObserver(onResize).observe(C);

/* ══════════════════════════════════════════════════
   ANIMATION LOOP
══════════════════════════════════════════════════ */
const clock=new THREE.Clock();
let blinkT=0;

(function loop(){
  requestAnimationFrame(loop);
  const t=clock.getElapsedTime();
  const dt=clock.getDelta();
  blinkT+=dt;

  /* Jarvis core rings spin */
  jarvis.coreLight.intensity=4+1.5*Math.sin(t*2.8);
  jarvis.group.children.forEach(c=>{
    if(c.geometry?.type==='TorusGeometry'){ c.rotation.x+=0.008; c.rotation.z+=0.005; }
  });

  /* Corridor emergency lights blink */
  corridors.forEach((cg,i)=>{
    if(cg.userData.eLight){
      cg.userData.eLight.intensity = (Math.sin(t*2.1+i*0.7)>0.6) ? 0.6 : 0.05;
    }
  });

  /* Agent rooms */
  const hoverable=[];
  ROOMS.forEach(({group,light,trimM,agent})=>{
    const on=agent?.on&&agent.state!=='OFFLINE';
    const st=agent?.state||'OFFLINE';
    const pulse=st==='EXECUTING'?0.7+Math.sin(t*5)*0.3:st==='THINKING'?0.5+Math.sin(t*3)*0.2:on?0.3:0.05;
    light.intensity=on?2.5*pulse:0.1;
    trimM.emissiveIntensity=on?1.4*pulse:0.15;
    // Holographic orbs rotate
    (group.userData.orbs||[]).forEach((orb,i)=>{
      orb.rotation.y=t*0.8+i; orb.rotation.x=t*0.3+i*0.5;
      orb.position.y=1.0+0.12*Math.sin(t*1.5+i);
    });
    // Labels face camera
    group.children.forEach(c=>{ if(c.isSprite) c.quaternion.copy(camera.quaternion); });
    hoverable.push(group);
  });
  jarvis.group.children.forEach(c=>{ if(c.isSprite) c.quaternion.copy(camera.quaternion); });

  /* Dust drift */
  const dp=dustGeo.attributes.position;
  for(let i=1;i<dp.count*3;i+=3){ dp.array[i]=((dp.array[i]-0.001)+4)%4; }
  dp.needsUpdate=true;

  /* Hover */
  raycaster.setFromCamera(mouse,camera);
  const hits=raycaster.intersectObjects(hoverable,true);
  const hlo=document.getElementById('holo');
  window.hovered=null;
  if(hits.length){
    let obj=hits[0].object;
    while(obj.parent&&!ROOMS.find(r=>r.group===obj)) obj=obj.parent;
    const found=ROOMS.find(r=>r.group===obj);
    if(found&&found.agent?.id&&!found.agent.id.startsWith('empty')){
      window.hovered=found.agent;
      renderer.domElement.style.cursor='pointer';
      const p3=found.group.position.clone().project(camera);
      const rc=renderer.domElement.getBoundingClientRect();
      hlo.style.left=(((p3.x+1)/2)*rc.width+rc.left+18)+'px';
      hlo.style.top=(((-p3.y+1)/2)*rc.height+rc.top-18)+'px';
      const m=window.ST_META?.[found.agent.state]||{lbl:'IDLE',cls:'idle'};
      document.getElementById('hNm').textContent=found.agent.name.toUpperCase();
      document.getElementById('hNm').style.color=found.agent.color;
      document.getElementById('hRole').textContent=found.agent.role||'';
      document.getElementById('hSt').textContent=m.lbl;
      document.getElementById('hSt').className='h-st '+m.cls;
      document.getElementById('hActs').textContent=(found.agent.acts||0).toLocaleString();
      hlo.classList.add('show');
    }
  } else {
    renderer.domElement.style.cursor='default';
    hlo.classList.remove('show');
  }

  ctrl.update();
  composer.render();
})();
</script>'''

# Replace module
tag = '<script type="module">'
idx = html.find(tag, html.find('</script>'))  # skip importmap
end = html.find('</script>', idx) + len('</script>')
new_html = html[:idx] + NEW_MODULE + html[end:]
open('Nexus9.html', 'w', encoding='utf-8').write(new_html)
print('Module replaced. Lines:', new_html.count('\n'))
