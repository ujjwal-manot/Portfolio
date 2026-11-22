// Renders the EdgeSense-130 3D die on its package in three.js with pass/fail/not-run tiles, passing-only signal particles, reduced-motion switch, and click-to-layout selection.
import { useEffect, useRef } from "react";
import * as THREE from "three";
import { TRACKS } from "./catalog";
import { blockStatus, type BlockStatus, type CheckRow } from "./summary";

interface Die3DViewProps {
  summaries: Record<string, CheckRow[] | null>;
  reducedMotion: boolean;
  onSelectBlockLayout: (blockId: string) => void;
}

const STATUS_COLOR: Record<BlockStatus, number> = {
  pass: 0x2fb36d,
  fail: 0xd94854,
  "not run": 0x4b5563,
};

const CHAIN_ORDER = ["opamp", "adc", "fifo_bridge", "cpu"];

export function Die3DView({ summaries, reducedMotion, onSelectBlockLayout }: Die3DViewProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const selectRef = useRef(onSelectBlockLayout);
  selectRef.current = onSelectBlockLayout;

  useEffect(() => {
    const el = hostRef.current;
    if (!el) return;
    const width = Math.max(480, el.clientWidth);
    const height = 420;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050608);

    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(0, 10.5, 11.5);
    camera.lookAt(0, 0, 0);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch {
      el.textContent = "WebGL unavailable in this browser context.";
      return;
    }
    renderer.setSize(width, height);
    el.innerHTML = "";
    el.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const dir = new THREE.DirectionalLight(0xffffff, 0.9);
    dir.position.set(6, 12, 8);
    scene.add(dir);

    const pkg = new THREE.Mesh(
      new THREE.BoxGeometry(11.6, 0.5, 8.6),
      new THREE.MeshStandardMaterial({ color: 0x161b24, roughness: 0.85 })
    );
    pkg.position.y = -0.35;
    scene.add(pkg);

    const die = new THREE.Mesh(
      new THREE.BoxGeometry(10.0, 0.2, 7.2),
      new THREE.MeshStandardMaterial({ color: 0x202736, roughness: 0.5 })
    );
    scene.add(die);

    const tileMeshes: THREE.Mesh[] = [];
    const tileCenters: Record<string, THREE.Vector3> = {};
    const tileStatus: Record<string, BlockStatus> = {};

    const coreTracks = TRACKS.filter((t) => t.id !== "integration");
    coreTracks.forEach((track, rowIdx) => {
      track.blocks.forEach((block, colIdx) => {
        const st = blockStatus(summaries[block.id] ?? null);
        tileStatus[block.id] = st;
        const mesh = new THREE.Mesh(
          new THREE.BoxGeometry(2.0, 0.35, 1.7),
          new THREE.MeshStandardMaterial({ color: STATUS_COLOR[st], roughness: 0.45 })
        );
        const x = -3.3 + colIdx * 2.2;
        const z = -2.1 + rowIdx * 2.1;
        mesh.position.set(x, 0.28, z);
        mesh.userData = { blockId: block.id };
        scene.add(mesh);
        tileMeshes.push(mesh);
        tileCenters[block.id] = new THREE.Vector3(x, 0.6, z);
      });
    });

    const passingChain = CHAIN_ORDER.filter((id) => tileStatus[id] === "pass").map((id) => tileCenters[id]);
    const particles: THREE.Mesh[] = [];
    if (!reducedMotion && passingChain.length >= 2) {
      for (let i = 0; i < 8; i++) {
        const dot = new THREE.Mesh(
          new THREE.SphereGeometry(0.11, 10, 10),
          new THREE.MeshBasicMaterial({ color: 0x5ce1e6 })
        );
        scene.add(dot);
        particles.push(dot);
      }
    }

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const handleClick = (ev: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(tileMeshes);
      if (hits.length > 0) {
        const id = hits[0].object.userData.blockId as string | undefined;
        if (id) selectRef.current(id);
      }
    };
    renderer.domElement.addEventListener("click", handleClick);

    let rafId = 0;
    const clock = new THREE.Clock();
    const renderFrame = () => {
      const t = clock.getElapsedTime();
      if (!reducedMotion) {
        camera.position.x = Math.sin(t * 0.18) * 1.4;
        camera.lookAt(0, 0, 0);
        if (passingChain.length >= 2) {
          const segs = passingChain.length - 1;
          particles.forEach((p, idx) => {
            const u = ((t * 0.35 + idx / particles.length) % 1) * segs;
            const seg = Math.min(segs - 1, Math.floor(u));
            const frac = u - seg;
            p.position.lerpVectors(passingChain[seg], passingChain[seg + 1], frac);
          });
        }
        rafId = requestAnimationFrame(renderFrame);
      }
      renderer.render(scene, camera);
    };
    renderFrame();

    return () => {
      cancelAnimationFrame(rafId);
      renderer.domElement.removeEventListener("click", handleClick);
      renderer.dispose();
    };
  }, [summaries, reducedMotion]);

  return (
    <section className="results-card">
      <div className="results-head">
        <strong>EdgeSense-130 3D Die View</strong>
        <span>Green: pass | Red: fail | Grey: not run (click any tile to open Layout)</span>
      </div>
      <div ref={hostRef} className="die3d-host" />
    </section>
  );
}
