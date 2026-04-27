"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import api from "@/lib/api";
import { ZoomIn, ZoomOut, Maximize, Target } from "lucide-react";

interface GraphData {
  nodes: Array<{ id: string; name: string; x?: number; y?: number }>;
  links: Array<{ source: string; target: string; label: string }>;
}

const GraphView: React.FC = () => {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 });

  const fetchData = async () => {
    try {
      const response = await api.get("/graph_data");
      setData(response.data);
    } catch (error) {
      // Failed to fetch graph data
    } finally {
      setLoading(false);
    }
  };

  const handleResize = useCallback(() => {
    if (containerRef.current) {
      setDimensions({
        width: containerRef.current.offsetWidth,
        height: containerRef.current.offsetHeight,
      });
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    
    handleResize();
    window.addEventListener('resize', handleResize);

    // Initial zoom to fit after a short delay to allow graph to settle
    const timeout = setTimeout(() => {
      if (fgRef.current) {
        fgRef.current.zoomToFit(400);
      }
    }, 1000);

    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', handleResize);
      clearTimeout(timeout);
    };
  }, [handleResize]);

  // Zoom controls
  const zoomIn = () => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom();
      fgRef.current.zoom(currentZoom * 1.5, 400);
    }
  };

  const zoomOut = () => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom();
      fgRef.current.zoom(currentZoom / 1.5, 400);
    }
  };

  const zoomToFit = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400);
    }
  };

  const handleNodeClick = useCallback((node: any) => {
    if (fgRef.current) {
      // Center and zoom into the clicked node
      fgRef.current.centerAt(node.x, node.y, 1000);
      fgRef.current.zoom(2, 1000);
    }
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full min-h-[400px] bg-black/40 backdrop-blur-xl border border-emerald-500/20 rounded-xl overflow-hidden relative group transition-all duration-500">
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
        <h3 className="text-emerald-400 text-[10px] font-bold uppercase tracking-widest bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-emerald-500/30 flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
          Neural_Explorer_v2
        </h3>
      </div>

      {/* Zoom Controls Overlay */}
      <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-2 bg-black/60 backdrop-blur-md p-2 rounded-xl border border-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <button 
          onClick={zoomIn}
          className="p-2 hover:bg-emerald-500/20 text-emerald-500 rounded-lg transition-colors border border-transparent hover:border-emerald-500/30"
          title="Zoom In"
        >
          <ZoomIn size={16} />
        </button>
        <button 
          onClick={zoomOut}
          className="p-2 hover:bg-emerald-500/20 text-emerald-500 rounded-lg transition-colors border border-transparent hover:border-emerald-500/30"
          title="Zoom Out"
        >
          <ZoomOut size={16} />
        </button>
        <button 
          onClick={zoomToFit}
          className="p-2 hover:bg-emerald-500/20 text-emerald-500 rounded-lg transition-colors border border-transparent hover:border-emerald-500/30"
          title="Fit to Screen"
        >
          <Maximize size={16} />
        </button>
      </div>

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-20">
          <div className="text-emerald-500 animate-pulse font-mono text-sm uppercase tracking-widest">
            Initialising_Graph_Data...
          </div>
        </div>
      )}

      {!loading && data.nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/40 z-10">
          <div className="text-emerald-500/40 font-mono text-xs uppercase tracking-widest">
            No_Concepts_Mapped_Yet
          </div>
        </div>
      )}

      <ForceGraph2D
        ref={fgRef}
        graphData={data}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="#00000000"
        nodeColor={() => "#10b981"} // emerald-500
        linkColor={() => "#064e3b"} // emerald-900
        nodeLabel="name"
        linkLabel="label"
        nodeRelSize={6}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.25}
        onNodeClick={handleNodeClick}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.name;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px JetBrains Mono, monospace`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

          ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
          ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions as [number, number]);

          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillStyle = "#10b981";
          ctx.fillText(label, node.x, node.y);
        }}
      />
      
      {/* Decorative scanning overlay */}
      <div className="absolute inset-0 pointer-events-none border border-emerald-500/5 opacity-30 mix-blend-overlay" />
    </div>
  );
};

export default GraphView;
