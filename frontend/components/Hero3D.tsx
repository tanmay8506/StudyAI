"use client";

import { useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Float, Icosahedron } from "@react-three/drei";
import { useTheme } from "next-themes";
import * as THREE from "three";

/**
 * 3D Tech Geometry — Lightweight, mesmerizing, perfectly centered.
 */
function WireframeShape() {
  const meshRef = useRef<THREE.Mesh>(null);
  const { viewport, pointer } = useThree();
  const { resolvedTheme } = useTheme();

  // Subtle mouse tracking for rotation
  useFrame((state, delta) => {
    if (!meshRef.current) return;
    
    // Base slow rotation
    meshRef.current.rotation.x += 0.1 * delta;
    meshRef.current.rotation.y += 0.15 * delta;

    // Add mouse influence
    const targetX = (pointer.y * viewport.height) / 8;
    const targetY = (pointer.x * viewport.width) / 8;

    meshRef.current.rotation.x = THREE.MathUtils.lerp(meshRef.current.rotation.x, targetX, 1 * delta);
    meshRef.current.rotation.y = THREE.MathUtils.lerp(meshRef.current.rotation.y, targetY, 1 * delta);
  });

  const isDark = resolvedTheme === "dark";
  const color = isDark ? "#e8c84a" : "#4f52ff";

  return (
    <Float
      speed={2.5} 
      rotationIntensity={1} 
      floatIntensity={1.5} 
    >
      <Icosahedron ref={meshRef} args={[3, 1]}>
        <meshBasicMaterial
          color={color}
          wireframe
          transparent
          opacity={0.15} // Very subtle so it doesn't distract from text
        />
      </Icosahedron>
      {/* Inner solid core */}
      <Icosahedron args={[1.2, 0]}>
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.05}
        />
      </Icosahedron>
    </Float>
  );
}

export function Hero3D() {
  return (
    <div className="absolute inset-0 z-0 pointer-events-none flex items-center justify-center">
      <Canvas camera={{ position: [0, 0, 8], fov: 45 }}>
        <WireframeShape />
      </Canvas>
    </div>
  );
}
