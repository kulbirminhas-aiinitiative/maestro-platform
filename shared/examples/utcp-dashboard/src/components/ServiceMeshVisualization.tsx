import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import type { UTCPService, ToolCall } from '../types';

interface Node extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  type: 'service' | 'registry' | 'claude';
  is_healthy: boolean;
  tool_count?: number;
}

interface Link extends d3.SimulationLinkDatum<Node> {
  source: string | Node;
  target: string | Node;
  call_count?: number;
  latency?: number;
}

interface Props {
  services: UTCPService[];
  recentCalls: ToolCall[];
  className?: string;
}

export const ServiceMeshVisualization: React.FC<Props> = ({
  services,
  recentCalls,
  className = '',
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!svgRef.current || services.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = dimensions;

    // Create nodes
    const nodes: Node[] = [
      {
        id: 'registry',
        name: 'UTCP Registry',
        type: 'registry',
        is_healthy: true,
        x: width / 2,
        y: height / 2,
      },
      {
        id: 'claude',
        name: 'Claude Orchestrator',
        type: 'claude',
        is_healthy: true,
        x: width / 2,
        y: height / 4,
      },
      ...services.map((service, i) => ({
        id: service.name,
        name: service.name,
        type: 'service' as const,
        is_healthy: service.is_healthy,
        tool_count: service.manual?.tools?.length || 0,
      })),
    ];

    // Create links
    const links: Link[] = [
      ...services.map((service) => ({
        source: 'registry',
        target: service.name,
      })),
      ...services.map((service) => ({
        source: 'claude',
        target: service.name,
        call_count: recentCalls.filter((call) =>
          call.name.startsWith(service.name)
        ).length,
      })),
    ];

    // Create force simulation
    const simulation = d3
      .forceSimulation(nodes)
      .force(
        'link',
        d3
          .forceLink(links)
          .id((d: any) => d.id)
          .distance(150)
      )
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(50));

    // Create container
    const container = svg
      .append('g')
      .attr('class', 'mesh-container');

    // Add zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom as any);

    // Draw links
    const link = container
      .selectAll('.link')
      .data(links)
      .enter()
      .append('line')
      .attr('class', 'link')
      .attr('stroke', (d: any) => {
        if (d.source === 'claude' || d.target === 'claude') {
          return '#8b5cf6';
        }
        return '#64748b';
      })
      .attr('stroke-width', (d: any) => {
        const callCount = d.call_count || 0;
        return Math.max(1, Math.min(callCount / 2, 5));
      })
      .attr('stroke-opacity', 0.6)
      .attr('stroke-dasharray', (d: any) =>
        d.source === 'registry' ? '5,5' : '0'
      );

    // Draw nodes
    const node = container
      .selectAll('.node')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .call(
        d3
          .drag<SVGGElement, Node>()
          .on('start', dragStarted)
          .on('drag', dragged)
          .on('end', dragEnded) as any
      );

    // Add circles for nodes
    node
      .append('circle')
      .attr('r', (d) => {
        if (d.type === 'registry') return 40;
        if (d.type === 'claude') return 35;
        return 30;
      })
      .attr('fill', (d) => {
        if (d.type === 'registry') return '#3b82f6';
        if (d.type === 'claude') return '#8b5cf6';
        return d.is_healthy ? '#10b981' : '#ef4444';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 3)
      .attr('opacity', 0.9);

    // Add node labels
    node
      .append('text')
      .text((d) => d.name)
      .attr('text-anchor', 'middle')
      .attr('dy', 45)
      .attr('fill', '#1e293b')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold');

    // Add tool count badge
    node
      .filter((d) => d.type === 'service' && (d.tool_count || 0) > 0)
      .append('circle')
      .attr('cx', 20)
      .attr('cy', -20)
      .attr('r', 12)
      .attr('fill', '#f59e0b')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    node
      .filter((d) => d.type === 'service' && (d.tool_count || 0) > 0)
      .append('text')
      .attr('x', 20)
      .attr('y', -16)
      .attr('text-anchor', 'middle')
      .attr('fill', '#fff')
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .text((d) => d.tool_count || 0);

    // Add health indicator
    node
      .filter((d) => d.type === 'service')
      .append('circle')
      .attr('cx', -20)
      .attr('cy', -20)
      .attr('r', 6)
      .attr('fill', (d) => (d.is_healthy ? '#10b981' : '#ef4444'))
      .append('title')
      .text((d) => (d.is_healthy ? 'Healthy' : 'Unhealthy'));

    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragStarted(event: any, d: Node) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: Node) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragEnded(event: any, d: Node) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [services, recentCalls, dimensions]);

  useEffect(() => {
    const handleResize = () => {
      if (svgRef.current) {
        const { width, height } = svgRef.current.getBoundingClientRect();
        setDimensions({ width, height });
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className={`relative w-full h-full ${className}`}>
      <svg
        ref={svgRef}
        className="w-full h-full bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg shadow-inner"
        style={{ minHeight: '600px' }}
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#64748b" />
          </marker>
        </defs>
      </svg>

      <div className="absolute top-4 left-4 bg-white p-4 rounded-lg shadow-lg">
        <h3 className="text-sm font-bold text-slate-700 mb-2">Legend</h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-blue-500"></div>
            <span>UTCP Registry</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-purple-500"></div>
            <span>Claude Orchestrator</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-green-500"></div>
            <span>Healthy Service</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-red-500"></div>
            <span>Unhealthy Service</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-amber-500 flex items-center justify-center text-white text-[8px] font-bold">
              N
            </div>
            <span>Tool Count</span>
          </div>
        </div>
      </div>

      <div className="absolute bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg text-xs text-slate-600">
        Drag nodes to rearrange • Scroll to zoom
      </div>
    </div>
  );
};