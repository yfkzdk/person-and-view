'use client'

import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/* ================================================================
   Texture generators
   ================================================================ */

function createGlowTexture(color: string, size = 128): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = size; canvas.height = size
  const ctx = canvas.getContext('2d')!
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  g.addColorStop(0, 'rgba(255,255,255,0.95)')
  g.addColorStop(0.03, color)
  g.addColorStop(0.15, color.replace('1)', '0.6)'))
  g.addColorStop(0.4, color.replace('1)', '0.12)'))
  g.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g; ctx.fillRect(0, 0, size, size)
  return new THREE.CanvasTexture(canvas)
}

function createRingTexture(size = 256): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = size; canvas.height = size
  const ctx = canvas.getContext('2d')!
  const cx = size / 2, cy = size / 2
  const g = ctx.createRadialGradient(cx, cy, size * 0.28, cx, cy, size * 0.5)
  g.addColorStop(0, 'rgba(0,0,0,0)')
  g.addColorStop(0.35, 'rgba(255,255,255,0)')
  g.addColorStop(0.5, 'rgba(255,255,255,0.85)')
  g.addColorStop(0.65, 'rgba(255,255,255,0)')
  g.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g; ctx.fillRect(0, 0, size, size)
  return new THREE.CanvasTexture(canvas)
}

function createStarTexture(color: string, size = 128): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = size; canvas.height = size
  const ctx = canvas.getContext('2d')!
  const cx = size / 2, cy = size / 2
  // Draw star shape
  const spikes = 6; const outerR = size * 0.45; const innerR = size * 0.18
  ctx.beginPath()
  for (let i = 0; i < spikes * 2; i++) {
    const r = i % 2 === 0 ? outerR : innerR
    const angle = (i * Math.PI) / spikes - Math.PI / 2
    const x = cx + Math.cos(angle) * r; const y = cy + Math.sin(angle) * r
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  }
  ctx.closePath()
  const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, outerR)
  g.addColorStop(0, 'rgba(255,255,255,0.9)')
  g.addColorStop(0.15, color)
  g.addColorStop(0.5, color.replace('1)', '0.15)'))
  g.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g; ctx.fill()
  return new THREE.CanvasTexture(canvas)
}

/* ================================================================
   Emotion palettes
   ================================================================ */

type Emotion = 'neutral' | 'happy' | 'sad' | 'angry' | 'excited' | 'calm'

const PALETTES: Record<Emotion, { primary: string; secondary: string; accent: string; core: string; dim: string }> = {
  neutral:  { primary: '#00ffc8', secondary: '#9b5de5', accent: '#ff6b9d', core: '#ffffff', dim: '#005a44' },
  happy:    { primary: '#00ffc8', secondary: '#ffdd57', accent: '#ff9944', core: '#fffbe6', dim: '#006644' },
  sad:      { primary: '#5b7fff', secondary: '#6b5ce5', accent: '#3d5a99', core: '#c8d8ff', dim: '#1a2a55' },
  angry:    { primary: '#ff4466', secondary: '#ff6b9d', accent: '#cc3355', core: '#ffcccc', dim: '#550011' },
  excited:  { primary: '#ffdd57', secondary: '#ff6b9d', accent: '#00ffc8', core: '#ffffff', dim: '#553300' },
  calm:     { primary: '#00c8a0', secondary: '#7b9ec7', accent: '#9b5de5', core: '#e0ffe8', dim: '#004433' },
}

/* ================================================================
   1. Neuron Somas — large central cell bodies with dendrite branches
   ================================================================ */

const SOMA_COUNT = 8
const SPINES_PER_SOMA = 80

function NeuronSomas({
  palette,
  beat,
  breath,
  audioEnergy,
}: {
  palette: ReturnType<typeof getPalette>
  beat: { current: number }
  breath: { current: number }
  audioEnergy: { current: number }
}) {
  const somaRef = useRef<THREE.Points>(null)
  const spineRef = useRef<THREE.Points>(null)

  const { somaData, spineData } = useMemo(() => {
    const somas: { pos: THREE.Vector3; size: number; phase: number }[] = []
    const spines = new Float32Array(SOMA_COUNT * SPINES_PER_SOMA * 3)
    const spineSizes = new Float32Array(SOMA_COUNT * SPINES_PER_SOMA)

    for (let s = 0; s < SOMA_COUNT; s++) {
      const phi = Math.acos(2 * Math.random() - 1)
      const theta = Math.random() * Math.PI * 2
      const r = 0.5 + Math.random() * 0.8
      somas.push({
        pos: new THREE.Vector3(r * Math.sin(phi) * Math.cos(theta), r * Math.sin(phi) * Math.sin(theta), r * Math.cos(phi) * 0.6),
        size: 0.28 + Math.random() * 0.22,
        phase: Math.random() * Math.PI * 2,
      })
      // Dendrite spines around each soma
      for (let sp = 0; sp < SPINES_PER_SOMA; sp++) {
        const sphi = Math.acos(2 * Math.random() - 1)
        const stheta = Math.random() * Math.PI * 2
        const sr = somas[s].size * 2.5 * (0.6 + Math.random() * 0.4)
        const idx = s * SPINES_PER_SOMA + sp
        spines[idx * 3] = somas[s].pos.x + sr * Math.sin(sphi) * Math.cos(stheta)
        spines[idx * 3 + 1] = somas[s].pos.y + sr * Math.sin(sphi) * Math.sin(stheta)
        spines[idx * 3 + 2] = somas[s].pos.z + sr * Math.cos(sphi) * 0.6
        spineSizes[idx] = 0.02 + Math.random() * 0.04
      }
    }
    return { somaData: somas, spineData: { positions: spines, sizes: spineSizes } }
  }, [])

  const somaPositions = useMemo(() => {
    const arr = new Float32Array(SOMA_COUNT * 3)
    somaData.forEach((s, i) => { arr[i * 3] = s.pos.x; arr[i * 3 + 1] = s.pos.y; arr[i * 3 + 2] = s.pos.z })
    return arr
  }, [somaData])

  const somaColors = useMemo(() => {
    const arr = new Float32Array(SOMA_COUNT * 3)
    const c = new THREE.Color(palette.core)
    somaData.forEach((_, i) => { arr[i * 3] = c.r; arr[i * 3 + 1] = c.g; arr[i * 3 + 2] = c.b })
    return arr
  }, [somaData, palette.core])

  const texSoma = useMemo(() => createGlowTexture('rgba(255,255,255,1)', 256), [])
  const texSpine = useMemo(() => createGlowTexture('rgba(0,255,200,1)', 32), [])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    if (somaRef.current) {
      const sizeArr = somaRef.current.geometry.attributes.size?.array as Float32Array
      const posArr = somaRef.current.geometry.attributes.position.array as Float32Array
      for (let s = 0; s < SOMA_COUNT; s++) {
        const sd = somaData[s]
        const pulse = 1 + Math.sin(t * 0.63 + sd.phase) * 0.08 + beat.current * 0.18 + audioEnergy.current * 0.12
        if (sizeArr) sizeArr[s] = sd.size * pulse
        posArr[s * 3 + 1] = sd.pos.y + breath.current * 0.8
      }
      somaRef.current.geometry.attributes.size.needsUpdate = true
      somaRef.current.geometry.attributes.position.needsUpdate = true
    }
    if (spineRef.current) {
      const sizeArr = spineRef.current.geometry.attributes.size?.array as Float32Array
      if (sizeArr) {
        for (let i = 0; i < SOMA_COUNT * SPINES_PER_SOMA; i++) {
          sizeArr[i] = (0.008 + Math.random() * 0.004) * (1 + beat.current * 0.5)
        }
        spineRef.current.geometry.attributes.size.needsUpdate = true
      }
    }
  })

  return (
    <>
      <points ref={somaRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[somaPositions, 3]} />
          <bufferAttribute attach="attributes-color" args={[somaColors, 3]} />
          <bufferAttribute attach="attributes-size" args={[new Float32Array(somaData.map(d => d.size)), 1]} />
        </bufferGeometry>
        <pointsMaterial map={texSoma} size={0.9} vertexColors transparent opacity={0.85} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
      </points>
      <points ref={spineRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[spineData.positions, 3]} />
          <bufferAttribute attach="attributes-size" args={[spineData.sizes, 1]} />
        </bufferGeometry>
        <pointsMaterial map={texSpine} size={0.14} color={palette.primary} transparent opacity={0.65} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
      </points>
    </>
  )
}

/* ================================================================
   2. Microtubule Network — structural skeleton + transport paths
   ================================================================ */

const MT_NODES = 80
const MT_LINKS = 200

function MicrotubuleNetwork({
  palette,
  beat,
  audioEnergy,
}: {
  palette: ReturnType<typeof getPalette>
  beat: { current: number }
  audioEnergy: { current: number }
}) {
  const linkRef = useRef<THREE.LineSegments>(null)
  const nodeRef = useRef<THREE.Points>(null)

  const { nodeData, linkData } = useMemo(() => {
    const nodes: THREE.Vector3[] = []
    for (let i = 0; i < MT_NODES; i++) {
      const phi = Math.acos(2 * Math.random() - 1)
      const theta = Math.random() * Math.PI * 2
      const r = 1.2 + Math.random() * 1.4
      nodes.push(new THREE.Vector3(r * Math.sin(phi) * Math.cos(theta), r * Math.sin(phi) * Math.sin(theta), r * Math.cos(phi) * 0.55))
    }
    const links: [number, number][] = []
    for (let i = 0; i < nodes.length; i++) {
      const dists: { idx: number; dist: number }[] = []
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue
        const d = nodes[i].distanceTo(nodes[j])
        if (d < 1.8) dists.push({ idx: j, dist: d })
      }
      dists.sort((a, b) => a.dist - b.dist)
      for (let k = 0; k < Math.min(2, dists.length); k++) {
        if (links.length >= MT_LINKS) break
        const j = dists[k].idx
        if (!links.some(l => (l[0] === i && l[1] === j) || (l[0] === j && l[1] === i))) links.push([i, j])
      }
      if (links.length >= MT_LINKS) break
    }
    return { nodeData: nodes, linkData: links }
  }, [])

  const nodePositions = useMemo(() => {
    const arr = new Float32Array(MT_NODES * 3)
    nodeData.forEach((n, i) => { arr[i * 3] = n.x; arr[i * 3 + 1] = n.y; arr[i * 3 + 2] = n.z })
    return arr
  }, [nodeData])

  const linkPositions = useMemo(() => {
    const arr = new Float32Array(linkData.length * 6)
    linkData.forEach(([a, b], i) => {
      arr[i * 6] = nodeData[a].x; arr[i * 6 + 1] = nodeData[a].y; arr[i * 6 + 2] = nodeData[a].z
      arr[i * 6 + 3] = nodeData[b].x; arr[i * 6 + 4] = nodeData[b].y; arr[i * 6 + 5] = nodeData[b].z
    })
    return arr
  }, [nodeData, linkData])

  const texNode = useMemo(() => createGlowTexture('rgba(0,200,180,1)', 16), [])

  useFrame(() => {
    if (linkRef.current) {
      const mat = linkRef.current.material as THREE.LineBasicMaterial
      mat.opacity = 0.06 + beat.current * 0.08 + audioEnergy.current * 0.06
    }
  })

  return (
    <>
      <lineSegments ref={linkRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linkPositions, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={palette.dim} transparent opacity={0.18} depthWrite={false} blending={THREE.AdditiveBlending} />
      </lineSegments>
      <points ref={nodeRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[nodePositions, 3]} />
        </bufferGeometry>
        <pointsMaterial map={texNode} size={0.14} color={palette.primary} transparent opacity={0.55} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
      </points>
    </>
  )
}

/* ================================================================
   3. Vesicles — travel along microtubules, bud→transport→release
   ================================================================ */

const VESICLE_COUNT = 45

function VesicleSystem({
  linkData,
  nodeData,
  palette,
  audioEnergy,
  isSpeaking,
  isRecording,
  dissolveEvents,
}: {
  linkData: [number, number][]
  nodeData: THREE.Vector3[]
  palette: ReturnType<typeof getPalette>
  audioEnergy: { current: number }
  isSpeaking: { current: boolean }
  isRecording?: { current: boolean }
  dissolveEvents: { current: { type: string; count: number; pos?: THREE.Vector3 } | null }
}) {
  const ref = useRef<THREE.Points>(null)

  const vesicleData = useMemo(() => ({
    positions: new Float32Array(VESICLE_COUNT * 3),
    sizes: new Float32Array(VESICLE_COUNT),
    linkIdx: new Float32Array(VESICLE_COUNT),
    progress: new Float32Array(VESICLE_COUNT),
    speeds: new Float32Array(VESICLE_COUNT),
    states: new Float32Array(VESICLE_COUNT), // 0=budding, 1=transporting, 2=releasing, 3=recycling
    stateTimers: new Float32Array(VESICLE_COUNT),
  }), [])

  useEffect(() => {
    for (let i = 0; i < VESICLE_COUNT; i++) {
      vesicleData.linkIdx[i] = Math.floor(Math.random() * linkData.length)
      vesicleData.progress[i] = Math.random()
      vesicleData.speeds[i] = 0.05 + Math.random() * 0.15
      vesicleData.states[i] = 1
      vesicleData.stateTimers[i] = Math.random() * 5
    }
  }, [linkData.length, vesicleData])

  // Recording trigger: spawn 3-5 new vesicles at beam injection points
  const wasRecording = useRef(false)
  useEffect(() => {
    if (isRecording?.current && !wasRecording.current) {
      // Recording just started — spawn new vesicles
      let spawned = 0
      for (let i = 0; i < VESICLE_COUNT && spawned < 5; i++) {
        if (vesicleData.states[i] === 3) {
          vesicleData.states[i] = 0
          vesicleData.progress[i] = 0
          vesicleData.stateTimers[i] = 0
          vesicleData.linkIdx[i] = (spawned + Math.floor(Math.random() * 5)) % linkData.length
          spawned++
        }
      }
    }
    wasRecording.current = isRecording?.current ?? false
  }, [isRecording?.current, linkData.length, vesicleData])

  // Handle dissolve events → create vesicle bud
  useEffect(() => {
    if (dissolveEvents.current?.type === 'user_message') {
      // Find a recycling vesicle and reset it to budding
      for (let i = 0; i < VESICLE_COUNT; i++) {
        if (vesicleData.states[i] === 3) {
          vesicleData.states[i] = 0
          vesicleData.progress[i] = 0
          vesicleData.stateTimers[i] = 0
          vesicleData.linkIdx[i] = i % linkData.length
          break
        }
      }
      dissolveEvents.current = null
    }
  }, [linkData.length, vesicleData, dissolveEvents])

  const texVesicle = useMemo(() => createGlowTexture('rgba(255,255,200,1)', 64), [])

  useFrame((state) => {
    if (!ref.current) return
    const t = state.clock.elapsedTime
    const posArr = ref.current.geometry.attributes.position.array as Float32Array
    const sizeArr = ref.current.geometry.attributes.size?.array as Float32Array

    for (let i = 0; i < VESICLE_COUNT; i++) {
      vesicleData.stateTimers[i] += 0.016
      const li = vesicleData.linkIdx[i]
      const [a, b] = linkData[li]
      const na = nodeData[a]; const nb = nodeData[b]

      switch (vesicleData.states[i]) {
        case 0: // budding — small, near soma
          if (sizeArr) sizeArr[i] = Math.min(0.06, (vesicleData.stateTimers[i] / 1.5) * 0.06)
          vesicleData.progress[i] = 0
          if (vesicleData.stateTimers[i] > 1.5) {
            vesicleData.states[i] = 1; vesicleData.stateTimers[i] = 0
          }
          break
        case 1: { // transporting
          vesicleData.progress[i] += vesicleData.speeds[i] * (0.5 + audioEnergy.current * 1.5 + (isSpeaking.current ? 0.3 : 0)) * 0.016
          if (sizeArr) sizeArr[i] = 0.06 + audioEnergy.current * 0.03
          if (vesicleData.progress[i] >= 1) {
            vesicleData.progress[i] = 1
            vesicleData.states[i] = 2; vesicleData.stateTimers[i] = 0
          }
          break
        }
        case 2: // releasing — bright flash at terminal
          if (sizeArr) sizeArr[i] = 0.06 + Math.sin(vesicleData.stateTimers[i] * 8) * 0.04
          if (vesicleData.stateTimers[i] > 1.0) {
            vesicleData.states[i] = 3; vesicleData.stateTimers[i] = 0
          }
          break
        case 3: // recycling — faded, returning
          vesicleData.progress[i] -= 0.003
          if (sizeArr) sizeArr[i] = 0.02
          if (vesicleData.progress[i] <= 0) {
            vesicleData.progress[i] = 0
            if (Math.random() < 0.02) { vesicleData.states[i] = 0; vesicleData.stateTimers[i] = 0 }
          }
          break
      }

      const p = Math.max(0, Math.min(1, vesicleData.progress[i]))
      posArr[i * 3] = na.x + (nb.x - na.x) * p
      posArr[i * 3 + 1] = na.y + (nb.y - na.y) * p
      posArr[i * 3 + 2] = na.z + (nb.z - na.z) * p
    }
    ref.current.geometry.attributes.position.needsUpdate = true
    if (sizeArr) ref.current.geometry.attributes.size.needsUpdate = true
  })

  const defaultSizes = useMemo(() => new Float32Array(VESICLE_COUNT).fill(0.05), [])

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[vesicleData.positions, 3]} />
        <bufferAttribute attach="attributes-size" args={[defaultSizes, 1]} />
      </bufferGeometry>
      <pointsMaterial map={texVesicle} size={0.32} color={palette.accent} transparent opacity={0.8} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
    </points>
  )
}

/* ================================================================
   4. Myelin Sheaths — segmented tubular wrapping along links
   ================================================================ */

const MYELIN_SEGMENTS = 28

function MyelinSheaths({
  linkData,
  nodeData,
  palette,
  beat,
}: {
  linkData: [number, number][]
  nodeData: THREE.Vector3[]
  palette: ReturnType<typeof getPalette>
  beat: { current: number }
}) {
  const ref = useRef<THREE.Points>(null)

  const { positions, sizes, linkRefs, startProgress, rotPhases } = useMemo(() => {
    const pos = new Float32Array(MYELIN_SEGMENTS * 4 * 3) // 4 points per segment
    const sz = new Float32Array(MYELIN_SEGMENTS * 4)
    const lr: number[] = []; const sp: number[] = []; const rp: number[] = []
    for (let i = 0; i < MYELIN_SEGMENTS; i++) {
      const li = Math.floor(Math.random() * linkData.length)
      lr.push(li)
      sp.push(0.1 + Math.random() * 0.6)
      rp.push(Math.random() * Math.PI * 2)
      for (let j = 0; j < 4; j++) sz[i * 4 + j] = 0.04 + Math.random() * 0.03
    }
    return { positions: pos, sizes: sz, linkRefs: lr, startProgress: sp, rotPhases: rp }
  }, [linkData])

  useFrame((state) => {
    if (!ref.current) return
    const t = state.clock.elapsedTime
    const posArr = ref.current.geometry.attributes.position.array as Float32Array
    const sizeArr = ref.current.geometry.attributes.size?.array as Float32Array

    for (let i = 0; i < MYELIN_SEGMENTS; i++) {
      const [a, b] = linkData[linkRefs[i]]
      const na = nodeData[a]; const nb = nodeData[b]
      const base = startProgress[i] + Math.sin(t * 0.2 + rotPhases[i]) * 0.04
      for (let j = 0; j < 4; j++) {
        const p = base + j * 0.03
        const cp = Math.max(0, Math.min(1, p))
        posArr[(i * 4 + j) * 3] = na.x + (nb.x - na.x) * cp + (Math.sin(t * 1.5 + i + j) * 0.04)
        posArr[(i * 4 + j) * 3 + 1] = na.y + (nb.y - na.y) * cp + (Math.cos(t * 1.5 + i + j) * 0.04)
        posArr[(i * 4 + j) * 3 + 2] = na.z + (nb.z - na.z) * cp
        if (sizeArr) sizeArr[i * 4 + j] = 0.04 + beat.current * 0.02
      }
    }
    ref.current.geometry.attributes.position.needsUpdate = true
    if (sizeArr) ref.current.geometry.attributes.size.needsUpdate = true
  })

  const texMyelin = useMemo(() => createGlowTexture('rgba(200,180,255,1)', 32), [])

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-size" args={[sizes, 1]} />
      </bufferGeometry>
      <pointsMaterial map={texMyelin} size={0.28} color={palette.secondary} transparent opacity={0.5} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
    </points>
  )
}

/* ================================================================
   5. Astrocytes — star-shaped glial cells, slow amoeboid movement
   ================================================================ */

const ASTROCYTE_COUNT = 10

function Astrocytes({
  palette,
  audioEnergy,
  isSpeaking,
  dissolveEvents,
  nodeData,
}: {
  palette: ReturnType<typeof getPalette>
  audioEnergy: { current: number }
  isSpeaking: { current: boolean }
  dissolveEvents: { current: { type: string; count: number; pos?: THREE.Vector3 } | null }
  nodeData: THREE.Vector3[]
}) {
  const ref = useRef<THREE.Points>(null)

  const astroData = useMemo(() => ({
    positions: new Float32Array(ASTROCYTE_COUNT * 3),
    sizes: new Float32Array(ASTROCYTE_COUNT),
    targets: new Float32Array(ASTROCYTE_COUNT * 3),
    phases: new Float32Array(ASTROCYTE_COUNT),
    wrapping: new Float32Array(ASTROCYTE_COUNT), // 0-1 wrapping intensity
  }), [])

  useEffect(() => {
    for (let i = 0; i < ASTROCYTE_COUNT; i++) {
      const phi = Math.acos(2 * Math.random() - 1)
      const theta = Math.random() * Math.PI * 2
      const r = 1.0 + Math.random() * 1.6
      astroData.positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      astroData.positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      astroData.positions[i * 3 + 2] = r * Math.cos(phi) * 0.55
      astroData.targets[i * 3] = astroData.positions[i * 3]
      astroData.targets[i * 3 + 1] = astroData.positions[i * 3 + 1]
      astroData.targets[i * 3 + 2] = astroData.positions[i * 3 + 2]
      astroData.phases[i] = Math.random() * Math.PI * 2
      astroData.sizes[i] = 0.15 + Math.random() * 0.15
    }
  }, [astroData])

  // AI message → astrocyte wrapping
  useEffect(() => {
    if (dissolveEvents.current?.type === 'assistant_message') {
      // Find nearest astrocyte and wrap
      let best = 0; let bestDist = Infinity
      for (let i = 0; i < ASTROCYTE_COUNT; i++) {
        const d = astroData.wrapping[i]
        if (d < bestDist) { bestDist = d; best = i }
      }
      astroData.wrapping[best] = 1
      dissolveEvents.current = null
    }
  }, [astroData, dissolveEvents])

  useFrame((state) => {
    if (!ref.current) return
    const t = state.clock.elapsedTime
    const posArr = ref.current.geometry.attributes.position.array as Float32Array
    const sizeArr = ref.current.geometry.attributes.size?.array as Float32Array

    for (let i = 0; i < ASTROCYTE_COUNT; i++) {
      // Amoeboid movement — slow drift toward random targets
      if (Math.random() < 0.005) {
        const closestNode = nodeData[Math.floor(Math.random() * nodeData.length)]
        astroData.targets[i * 3] = closestNode.x + (Math.random() - 0.5) * 0.5
        astroData.targets[i * 3 + 1] = closestNode.y + (Math.random() - 0.5) * 0.5
        astroData.targets[i * 3 + 2] = closestNode.z + (Math.random() - 0.5) * 0.5
      }
      // Smooth movement toward target
      for (let j = 0; j < 3; j++) {
        const cur = posArr[i * 3 + j]
        const tar = astroData.targets[i * 3 + j]
        posArr[i * 3 + j] = cur + (tar - cur) * 0.003 + (Math.random() - 0.5) * 0.002
      }
      // Wrapping decay + brightness boost on AI response
      astroData.wrapping[i] *= 0.995
      if (sizeArr) sizeArr[i] = astroData.sizes[i] * (1 + astroData.wrapping[i] * 0.7 + audioEnergy.current * 0.3)
    }
    ref.current.geometry.attributes.position.needsUpdate = true
    if (sizeArr) ref.current.geometry.attributes.size.needsUpdate = true
  })

  const texAstro = useMemo(() => createStarTexture('rgba(155,93,229,1)'), [])

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[astroData.positions, 3]} />
        <bufferAttribute attach="attributes-size" args={[astroData.sizes, 1]} />
      </bufferGeometry>
      <pointsMaterial map={texAstro} size={0.85} color={palette.secondary} transparent opacity={0.5} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
    </points>
  )
}

/* ================================================================
   6. Plankton — ambient micro-particles, Brownian motion + phototaxis
   ================================================================ */

const PLANKTON_COUNT = 400

function PlanktonField({ palette, audioEnergy }: { palette: ReturnType<typeof getPalette>; audioEnergy: { current: number } }) {
  const ref = useRef<THREE.Points>(null)

  const { positions, sizes, velocities } = useMemo(() => {
    const p = new Float32Array(PLANKTON_COUNT * 3)
    const s = new Float32Array(PLANKTON_COUNT)
    const v = new Float32Array(PLANKTON_COUNT * 3)
    for (let i = 0; i < PLANKTON_COUNT; i++) {
      p[i * 3] = (Math.random() - 0.5) * 6
      p[i * 3 + 1] = (Math.random() - 0.5) * 5
      p[i * 3 + 2] = (Math.random() - 0.5) * 3
      s[i] = 0.01 + Math.random() * 0.03
      v[i * 3] = (Math.random() - 0.5) * 0.01
      v[i * 3 + 1] = (Math.random() - 0.5) * 0.01
      v[i * 3 + 2] = (Math.random() - 0.5) * 0.005
    }
    return { positions: p, sizes: s, velocities: v }
  }, [])

  const texPlankton = useMemo(() => createGlowTexture('rgba(0,200,170,1)', 16), [])

  useFrame(() => {
    if (!ref.current) return
    const posArr = ref.current.geometry.attributes.position.array as Float32Array
    const sizeArr = ref.current.geometry.attributes.size?.array as Float32Array

    for (let i = 0; i < PLANKTON_COUNT; i++) {
      velocities[i * 3] += (Math.random() - 0.5) * 0.008
      velocities[i * 3 + 1] += (Math.random() - 0.5) * 0.008
      velocities[i * 3 + 2] += (Math.random() - 0.5) * 0.004
      // Damping
      velocities[i * 3] *= 0.98; velocities[i * 3 + 1] *= 0.98; velocities[i * 3 + 2] *= 0.98
      // Phototaxis toward center when active
      const centerPull = audioEnergy.current * 0.003
      velocities[i * 3] -= posArr[i * 3] * centerPull
      velocities[i * 3 + 1] -= posArr[i * 3 + 1] * centerPull
      // Update position
      posArr[i * 3] += velocities[i * 3]
      posArr[i * 3 + 1] += velocities[i * 3 + 1]
      posArr[i * 3 + 2] += velocities[i * 3 + 2]
      // Wrap boundaries
      for (let j = 0; j < 3; j++) {
        const limit = j === 2 ? 1.5 : 3
        if (Math.abs(posArr[i * 3 + j]) > limit) posArr[i * 3 + j] *= -0.9
      }
      if (sizeArr) sizeArr[i] = sizes[i] * (1 + audioEnergy.current * 1.5)
    }
    ref.current.geometry.attributes.position.needsUpdate = true
    if (sizeArr) ref.current.geometry.attributes.size.needsUpdate = true
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-size" args={[sizes, 1]} />
      </bufferGeometry>
      <pointsMaterial map={texPlankton} size={0.14} color={palette.primary} transparent opacity={0.4} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
    </points>
  )
}

/* ================================================================
   Heart Core + Shockwave Rings
   ================================================================ */

const RING_COUNT = 4

function HeartCore({ palette, beat, audioEnergy }: { palette: ReturnType<typeof getPalette>; beat: { current: number }; audioEnergy: { current: number } }) {
  const coreRef = useRef<THREE.Sprite>(null)
  const ringRefs = useRef<THREE.Sprite[]>([])

  const ringStates = useRef(
    Array.from({ length: RING_COUNT }, (_, i) => ({ scale: 0.3, opacity: 0, active: false, delay: i * 0.07 }))
  )

  const texCore = useMemo(() => createGlowTexture('rgba(255,255,255,1)', 256), [])
  const texRing = useMemo(() => createRingTexture(), [])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const bpm = 55 + audioEnergy.current * 75
    const interval = 60 / bpm

    ringStates.current.forEach((ring) => {
      const localBeat = ((t + ring.delay) % interval) / interval
      if (localBeat < 0.05 && !ring.active) { ring.active = true; ring.scale = 0.3; ring.opacity = 0.6 }
      if (ring.active) { ring.scale += (5.5 - ring.scale) * 0.04; ring.opacity *= 0.93; if (ring.opacity < 0.015) { ring.active = false; ring.opacity = 0; ring.scale = 0.3 } }
    })

    if (coreRef.current) {
      const s = 0.18 + beat.current * 0.25 + audioEnergy.current * 0.15
      coreRef.current.scale.setScalar(s)
      coreRef.current.material.opacity = 0.65 + beat.current * 0.35
    }
    ringRefs.current.forEach((sprite, i) => {
      if (sprite && ringStates.current[i]) {
        const rs = ringStates.current[i]
        sprite.scale.setScalar(rs.scale); sprite.material.opacity = rs.opacity * 0.4; sprite.visible = rs.active
      }
    })
  })

  return (
    <>
      <sprite ref={coreRef} position={[0, 0, 0]}>
        <spriteMaterial map={texCore} color={palette.core} transparent opacity={0.65} depthWrite={false} blending={THREE.AdditiveBlending} />
      </sprite>
      {Array.from({ length: RING_COUNT }, (_, i) => (
        <sprite key={i} ref={(el) => { if (el) ringRefs.current[i] = el }} position={[0, 0, 0]} visible={false}>
          <spriteMaterial map={texRing} color={palette.primary} transparent opacity={0} depthWrite={false} blending={THREE.AdditiveBlending} />
        </sprite>
      ))}
    </>
  )
}

/* ================================================================
   Synaptic Terminals — filamentous endings at microtubule tips
   ================================================================ */

const TERMINAL_COUNT = 50

function SynapticTerminals({
  nodeData,
  palette,
  beat,
  isSpeaking,
}: {
  nodeData: THREE.Vector3[]
  palette: ReturnType<typeof getPalette>
  beat: { current: number }
  isSpeaking: { current: boolean }
}) {
  const ref = useRef<THREE.Points>(null)
  const filoRef = useRef<THREE.LineSegments>(null)

  const terminalData = useMemo(() => {
    const positions = new Float32Array(TERMINAL_COUNT * 3)
    const sizes = new Float32Array(TERMINAL_COUNT)
    const phases = new Float32Array(TERMINAL_COUNT)
    for (let i = 0; i < TERMINAL_COUNT; i++) {
      const src = nodeData[Math.floor(Math.random() * nodeData.length)]
      const dir = new THREE.Vector3((Math.random() - 0.5), (Math.random() - 0.5), (Math.random() - 0.5)).normalize()
      const dist = 0.15 + Math.random() * 0.4
      positions[i * 3] = src.x + dir.x * dist
      positions[i * 3 + 1] = src.y + dir.y * dist
      positions[i * 3 + 2] = src.z + dir.z * dist
      sizes[i] = 0.03 + Math.random() * 0.05
      phases[i] = Math.random() * Math.PI * 2
    }
    return { positions, sizes, phases }
  }, [nodeData])

  // Filopodia lines
  const filoData = useMemo(() => ({
    positions: new Float32Array(TERMINAL_COUNT * 6 * 3), // up to 6 filo per terminal, 2 points each
  }), [])

  const texTerm = useMemo(() => createGlowTexture('rgba(255,180,100,1)', 64), [])

  useFrame((state) => {
    if (!ref.current) return
    const t = state.clock.elapsedTime
    const sizeArr = ref.current.geometry.attributes.size?.array as Float32Array
    const posArr = ref.current.geometry.attributes.position.array as Float32Array

    if (filoRef.current) {
      const filoArr = filoRef.current.geometry.attributes.position.array as Float32Array
      for (let i = 0; i < TERMINAL_COUNT; i++) {
        const bx = posArr[i * 3]; const by = posArr[i * 3 + 1]; const bz = posArr[i * 3 + 2]
        const active = isSpeaking.current || beat.current > 0.1
        const fp = active ? 6 : 2
        for (let f = 0; f < 6; f++) {
          const fi = i * 6 + f
          const len = f < fp ? (0.08 + Math.sin(t * 3 + terminalData.phases[i] + f) * 0.05) * (1 + beat.current * 2.5) : 0.005
          const angle = (f / 6) * Math.PI * 2 + terminalData.phases[i]
          const dx = Math.cos(angle) * len; const dy = Math.sin(angle) * len; const dz = Math.cos(angle * 2) * len * 0.3
          filoArr[fi * 6] = bx; filoArr[fi * 6 + 1] = by; filoArr[fi * 6 + 2] = bz
          filoArr[fi * 6 + 3] = bx + dx; filoArr[fi * 6 + 4] = by + dy; filoArr[fi * 6 + 5] = bz + dz
        }
      }
      filoRef.current.geometry.attributes.position.needsUpdate = true
    }

    if (sizeArr) {
      for (let i = 0; i < TERMINAL_COUNT; i++) {
        sizeArr[i] = terminalData.sizes[i] * (1 + beat.current * 0.8 + (isSpeaking.current ? 0.3 : 0))
      }
      ref.current.geometry.attributes.size.needsUpdate = true
    }
  })

  return (
    <>
      <points ref={ref}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[terminalData.positions, 3]} />
          <bufferAttribute attach="attributes-size" args={[terminalData.sizes, 1]} />
        </bufferGeometry>
        <pointsMaterial map={texTerm} size={0.38} color={palette.accent} transparent opacity={0.6} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
      </points>
      <lineSegments ref={filoRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[filoData.positions, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={palette.accent} transparent opacity={0.5} depthWrite={false} blending={THREE.AdditiveBlending} />
      </lineSegments>
    </>
  )
}

/* ================================================================
   Helpers
   ================================================================ */

function getPalette(emotion: Emotion) {
  return PALETTES[emotion] || PALETTES.neutral
}

/* ================================================================
   Main Neural Culture Export
   ================================================================ */

export interface DissolveEvent {
  type: 'user_message' | 'assistant_message'
  count: number
  pos?: THREE.Vector3
}

export function NeuralCulture({
  audioEnergy: rawEnergy = 0,
  emotion = 'neutral',
  isSpeaking = false,
  isRecording = false,
  dissolveEvents,
}: {
  audioEnergy?: number
  emotion?: Emotion
  isSpeaking?: boolean
  isRecording?: boolean
  dissolveEvents?: { current: DissolveEvent | null }
}) {
  const groupRef = useRef<THREE.Group>(null)
  const smoothedEnergy = useRef(0)
  const beatIntensity = useRef(0)
  const beatForJsx = useRef(0)
  const breathVal = useRef(0)
  const currentBpm = useRef(55)
  const targetBpm = useRef(55)
  const isSpeakingRef = useRef(isSpeaking)
  const isRecordingRef = useRef(isRecording)

  useEffect(() => { isSpeakingRef.current = isSpeaking }, [isSpeaking])
  useEffect(() => { isRecordingRef.current = isRecording }, [isRecording])

  const palette = getPalette(emotion)
  const energyRef = { current: 0 }
  const beatRef = { current: 0 }
  const breathRef = { current: 0 }

  // Microtubule network data — shared by vesicles + myelin
  const mtData = useMemo(() => {
    const nodes: THREE.Vector3[] = []
    for (let i = 0; i < MT_NODES; i++) {
      const phi = Math.acos(2 * Math.random() - 1)
      const theta = Math.random() * Math.PI * 2
      const r = 1.2 + Math.random() * 1.4
      nodes.push(new THREE.Vector3(r * Math.sin(phi) * Math.cos(theta), r * Math.sin(phi) * Math.sin(theta), r * Math.cos(phi) * 0.55))
    }
    const links: [number, number][] = []
    for (let i = 0; i < nodes.length; i++) {
      const dists: { idx: number; dist: number }[] = []
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue
        const d = nodes[i].distanceTo(nodes[j])
        if (d < 1.8) dists.push({ idx: j, dist: d })
      }
      dists.sort((a, b) => a.dist - b.dist)
      for (let k = 0; k < Math.min(2, dists.length); k++) {
        if (links.length >= MT_LINKS) break
        const j = dists[k].idx
        if (!links.some(l => (l[0] === i && l[1] === j) || (l[0] === j && l[1] === i))) links.push([i, j])
      }
      if (links.length >= MT_LINKS) break
    }
    return { nodes, links }
  }, [])

  // Heartbeat & breathing in useFrame
  useFrame((state) => {
    const t = state.clock.elapsedTime
    const e = smoothedEnergy.current
    const raw = isSpeakingRef.current ? Math.max(0.06, rawEnergy) : Math.max(0.02, rawEnergy * 0.5)
    smoothedEnergy.current += (raw - smoothedEnergy.current) * 0.04
    energyRef.current = smoothedEnergy.current

    // Heart rate
    targetBpm.current = 55 + (isSpeakingRef.current ? 35 : 0) + smoothedEnergy.current * 80
    currentBpm.current += (targetBpm.current - currentBpm.current) * 0.03
    const interval = 60 / currentBpm.current
    const beatPos = (t % interval) / interval
    if (beatPos < 0.08) beatIntensity.current = Math.max(beatIntensity.current, 1 - beatPos / 0.08)
    beatIntensity.current *= 0.92
    beatRef.current = beatIntensity.current
    beatForJsx.current = beatIntensity.current

    // Breathing — ±8% amplitude, ~10s period at idle
    const breathRate = 0.2 + smoothedEnergy.current * 0.8
    breathVal.current = Math.sin(t * breathRate) * 0.08 * (1 + smoothedEnergy.current * 1.5)
    breathRef.current = breathVal.current

    // Slow rotation
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0005
      groupRef.current.rotation.x += 0.00015
    }
  })

  return (
    <group ref={groupRef}>
      {/* 0. Boundary light domain — petri dish illusion */}
      <mesh>
        <sphereGeometry args={[3.0, 32, 32]} />
        <meshBasicMaterial color="#b0d2e6" transparent opacity={0.04} side={THREE.BackSide} depthWrite={false} />
      </mesh>

      {/* 1. Microtubule skeleton */}
      <MicrotubuleNetwork palette={palette} beat={beatRef} audioEnergy={energyRef} />

      {/* 2. Myelin sheaths along microtubules */}
      <MyelinSheaths linkData={mtData.links} nodeData={mtData.nodes} palette={palette} beat={beatRef} />

      {/* 3. Synaptic terminals at microtubule tips */}
      <SynapticTerminals nodeData={mtData.nodes} palette={palette} beat={beatRef} isSpeaking={isSpeakingRef} />

      {/* 4. Vesicles transporting along microtubules */}
      <VesicleSystem
        linkData={mtData.links}
        nodeData={mtData.nodes}
        palette={palette}
        audioEnergy={energyRef}
        isSpeaking={isSpeakingRef}
        isRecording={isRecordingRef}
        dissolveEvents={dissolveEvents || { current: null }}
      />

      {/* 5. Neuron somas */}
      <NeuronSomas palette={palette} beat={beatRef} breath={breathRef} audioEnergy={energyRef} />

      {/* 6. Astrocytes */}
      <Astrocytes palette={palette} audioEnergy={energyRef} isSpeaking={isSpeakingRef} dissolveEvents={dissolveEvents || { current: null }} nodeData={mtData.nodes} />

      {/* 7. Plankton field */}
      <PlanktonField palette={palette} audioEnergy={energyRef} />

      {/* Heart core + shockwave rings */}
      <HeartCore palette={palette} beat={beatRef} audioEnergy={energyRef} />

      {/* Ambient lights */}
      <pointLight position={[0, 0, 3]} intensity={0.2 + beatForJsx.current * 0.5} color={palette.primary} distance={14} />
      <pointLight position={[1.5, -1, -2]} intensity={0.14} color={palette.secondary} distance={12} />
      <pointLight position={[-1.5, 0.5, -1]} intensity={0.08} color={palette.accent} distance={10} />
      <ambientLight intensity={0.06} />
    </group>
  )
}

export { PALETTES }
export type { Emotion }
