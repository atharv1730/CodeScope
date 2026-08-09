import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import { useSection } from "../hooks/useSection";
import { Card, Empty, Spinner } from "../components/ui";
import { complexityColor } from "../lib/format";

export default function GraphTab({ id }) {
  const { data, loading, error } = useSection(id, "graph");
  const wrapRef = useRef(null);
  const svgRef = useRef(null);
  const [tip, setTip] = useState(null);
  const [width, setWidth] = useState(900);

  // Track container width for a responsive SVG.
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => {
      setWidth(entries[0].contentRect.width);
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const maxComplexity = useMemo(() => {
    if (!data?.nodes) return 1;
    return Math.max(1, ...data.nodes.map((n) => n.complexity_score || 0));
  }, [data]);

  useEffect(() => {
    if (!data || !data.nodes.length || !svgRef.current) return;
    const height = 540;
    const nodes = data.nodes.map((n) => ({ ...n }));
    const links = data.edges
      .filter((e) => nodes.some((n) => n.id === e.source) && nodes.some((n) => n.id === e.target))
      .map((e) => ({ ...e }));

    const radius = (n) => 5 + Math.min(18, (n.in_degree || 0) * 2.2);

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", [0, 0, width, height]);

    const root = svg.append("g");

    // Arrow markers for directed import edges.
    svg
      .append("defs")
      .append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 18)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-4L8,0L0,4")
      .attr("fill", "#cbd5e1");

    const link = root
      .append("g")
      .attr("stroke", "#cbd5e1")
      .attr("stroke-opacity", 0.7)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", 1.2)
      .attr("marker-end", "url(#arrow)");

    const node = root
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .style("cursor", "grab");

    node
      .append("circle")
      .attr("r", radius)
      .attr("fill", (d) =>
        d.complexity_score != null ? complexityColor(d.complexity_score, maxComplexity) : "#94a3b8"
      )
      .attr("stroke", (d) => (d.is_entry_point ? "#4f46e5" : "#ffffff"))
      .attr("stroke-width", (d) => (d.is_entry_point ? 3 : 1.5));

    // Label only the more-connected nodes to avoid clutter.
    node
      .filter((d) => (d.in_degree || 0) >= 1 || d.is_entry_point)
      .append("text")
      .text((d) => d.name)
      .attr("x", (d) => radius(d) + 4)
      .attr("y", 4)
      .attr("font-size", 11)
      .attr("fill", "#334155")
      .attr("paint-order", "stroke")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 3);

    node
      .on("mouseenter", (event, d) => {
        const rect = wrapRef.current.getBoundingClientRect();
        setTip({
          x: event.clientX - rect.left + 12,
          y: event.clientY - rect.top + 12,
          d,
        });
      })
      .on("mousemove", (event) => {
        const rect = wrapRef.current.getBoundingClientRect();
        setTip((t) => (t ? { ...t, x: event.clientX - rect.left + 12, y: event.clientY - rect.top + 12 } : t));
      })
      .on("mouseleave", () => setTip(null));

    const sim = d3
      .forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d) => d.id).distance(70).strength(0.6))
      .force("charge", d3.forceManyBody().strength(-220))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius((d) => radius(d) + 4));

    sim.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);
      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    // Drag behavior.
    node.call(
      d3
        .drag()
        .on("start", (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) sim.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
    );

    // Zoom / pan.
    const zoom = d3
      .zoom()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => root.attr("transform", event.transform));
    svg.call(zoom);

    return () => sim.stop();
  }, [data, width, maxComplexity]);

  if (loading) return <Spinner />;
  if (error) return <Empty title="Couldn’t load graph" hint={error} />;
  if (!data.nodes.length) {
    return (
      <Empty
        title="No import graph to show"
        hint="The dependency graph is built from Python imports. This repo has no resolvable intra-project Python imports."
      />
    );
  }

  return (
    <Card
      title="File dependency graph"
      subtitle="Python imports · node size = how many files import it · color = complexity · ringed = entry point"
      right={<Legend />}
    >
      <div ref={wrapRef} className="relative w-full">
        <svg ref={svgRef} width="100%" height={540} className="rounded-lg bg-canvas/60" />
        {tip && (
          <div
            className="pointer-events-none absolute z-10 rounded-lg border border-hairline bg-white px-3 py-2 shadow-lift text-xs max-w-xs"
            style={{ left: tip.x, top: tip.y }}
          >
            <div className="font-mono text-ink-900 break-all">{tip.d.id}</div>
            <div className="text-ink-500 mt-1">
              imported by {tip.d.in_degree} · {tip.d.lines_of_code} LOC
              {tip.d.complexity_score != null ? ` · complexity ${tip.d.complexity_score}` : ""}
            </div>
            {tip.d.is_entry_point && <div className="text-brand-600 mt-0.5">entry point</div>}
          </div>
        )}
      </div>
      <p className="mt-3 text-xs text-ink-400">Drag nodes to explore · scroll to zoom · {data.summary.node_count} files, {data.summary.edge_count} imports</p>
    </Card>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3 text-xs text-ink-500">
      <span className="flex items-center gap-1.5">
        <span className="w-3 h-3 rounded-full ring-2 ring-brand-500" style={{ background: "#94a3b8" }} />
        entry point
      </span>
      <span className="flex items-center gap-1.5">
        simple
        <span className="h-2 w-16 rounded-full" style={{ background: "linear-gradient(90deg,#16a34a,#d97706,#dc2626)" }} />
        complex
      </span>
    </div>
  );
}
