"use client";

import React, { useEffect, useRef } from 'react';

export function MathCanvas({ isFocused }: { isFocused: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;

    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };
    window.addEventListener('resize', handleResize);

    let mouseX = width / 2;
    let mouseY = height / 2;
    let targetMouseX = width / 2;
    let targetMouseY = height / 2;

    const handleMouseMove = (e: MouseEvent) => {
      targetMouseX = e.clientX;
      targetMouseY = e.clientY;
    };
    window.addEventListener('mousemove', handleMouseMove);

    let frame = 0;
    
    // Create node points for geometric/math connections
    const numNodes = Math.min(Math.floor((width * height) / 25000), 80);
    const nodes = Array.from({ length: numNodes }).map(() => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      baseAngle: Math.random() * Math.PI * 2,
      orbitRadius: Math.random() * 50 + 20,
      orbitSpeed: (Math.random() - 0.5) * 0.02
    }));

    const draw = () => {
      frame++;
      
      // Interpolate mouse for smooth movement
      mouseX += (targetMouseX - mouseX) * 0.05;
      mouseY += (targetMouseY - mouseY) * 0.05;

      ctx.clearRect(0, 0, width, height);
      
      // Draw a subtle grid background
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
      ctx.lineWidth = 1;
      const gridSize = 100;
      const offsetX = (mouseX * 0.05) % gridSize;
      const offsetY = (mouseY * 0.05) % gridSize;
      
      ctx.beginPath();
      for (let x = -gridSize; x < width + gridSize; x += gridSize) {
        ctx.moveTo(x - offsetX, 0);
        ctx.lineTo(x - offsetX, height);
      }
      for (let y = -gridSize; y < height + gridSize; y += gridSize) {
        ctx.moveTo(0, y - offsetY);
        ctx.lineTo(width, y - offsetY);
      }
      ctx.stroke();

      // Update and draw nodes
      ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
      nodes.forEach((node, i) => {
        // Drift
        node.x += node.vx;
        node.y += node.vy;
        
        // Wrap around
        if (node.x < -100) node.x = width + 100;
        if (node.x > width + 100) node.x = -100;
        if (node.y < -100) node.y = height + 100;
        if (node.y > height + 100) node.y = -100;

        // Calculate dynamic position with orbit and mouse parallax
        const dx = node.x - mouseX;
        const dy = node.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        const parallaxX = (dx / width) * 40;
        const parallaxY = (dy / height) * 40;
        
        const drawX = node.x + Math.cos(frame * node.orbitSpeed + node.baseAngle) * node.orbitRadius - parallaxX;
        const drawY = node.y + Math.sin(frame * node.orbitSpeed + node.baseAngle) * node.orbitRadius - parallaxY;

        ctx.beginPath();
        ctx.arc(drawX, drawY, 1.5, 0, Math.PI * 2);
        ctx.fill();

        // Draw connections
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const n2ParallaxX = ((n2.x - mouseX) / width) * 40;
          const n2ParallaxY = ((n2.y - mouseY) / height) * 40;
          const n2DrawX = n2.x + Math.cos(frame * n2.orbitSpeed + n2.baseAngle) * n2.orbitRadius - n2ParallaxX;
          const n2DrawY = n2.y + Math.sin(frame * n2.orbitSpeed + n2.baseAngle) * n2.orbitRadius - n2ParallaxY;
          
          const connDist = Math.sqrt(Math.pow(drawX - n2DrawX, 2) + Math.pow(drawY - n2DrawY, 2));
          
          if (connDist < 180) {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(255, 255, 255, ${0.1 * (1 - connDist / 180)})`;
            ctx.moveTo(drawX, drawY);
            ctx.lineTo(n2DrawX, n2DrawY);
            ctx.stroke();
          }
        }
        
        // Connect to mouse if close
        if (dist < 250) {
           ctx.beginPath();
           ctx.strokeStyle = `rgba(120, 160, 255, ${0.15 * (1 - dist / 250)})`;
           ctx.moveTo(drawX, drawY);
           ctx.lineTo(mouseX, mouseY);
           ctx.stroke();
        }
      });

      // Draw mathematical orbital rings around the mouse
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
      ctx.arc(mouseX, mouseY, 300, 0, Math.PI * 2);
      ctx.stroke();
      
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.setLineDash([5, 15]);
      ctx.arc(mouseX, mouseY, 150 + Math.sin(frame * 0.02) * 20, frame * 0.01, Math.PI * 2 + frame * 0.01);
      ctx.stroke();
      ctx.setLineDash([]);

      requestAnimationFrame(draw);
    };

    const animationId = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none select-none z-0 transition-all duration-700 ease-in-out"
      style={{
        filter: isFocused ? 'blur(20px) opacity(0.3)' : 'blur(0px) opacity(1)',
        transform: isFocused ? 'scale(1.05)' : 'scale(1)'
      }}
    />
  );
}
