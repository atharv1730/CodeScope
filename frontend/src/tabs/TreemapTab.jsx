import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import { useSection } from "../hooks/useSection";
import { Card, Empty, Spinner } from "../components/ui";
import { fmtNumber } from "../lib/format";

export default function TreemapTab({ id }) {
  const { data, loading, error } = useSection(id, "structure");
  const wrapRef = useRef(null);
  const svgRef = useRef(null);
  const [tip, setTip] = useState(null);
  const [width, setWidth] = useState(900);

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => setWidth(entries[0].contentRect.width));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const maxChange = useMemo(() => {
    if (!data?.treemap) return 1;
    let m = 1;
    const walk = (n) => {
      if (n.children) n.children.forEach(walk);
      else m = Math.max(m, n.change_frequency || 0);
    };
    walk(data.treemap);
    return m;
  }, [data]);

  useEffect(() => {
    if (!data?.treemap || !svgRef.current) return;
    const height = 560;
    // change-frequency overlay: cool (rarely changed) -> hot red (churned).
    const heat = d3.scaleSequential(d3.interpolateRgb("#dbe4f5", "#dc2626")).domain([0, maxChange]);

    const rootData = d3.hierarchy(data.treemap, (d) => d.children).sum((d) => (d.children ? 0 : d.size || 0));
    if (!rootData.value) return;
    rootData.sort((a, b) => b.value - a.value);

    d3.treemap().size([width, height]).paddingInner(2).paddingTop(0).round(true)(rootData);

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", [0, 0, width, height]);

    const leaves = rootData.leaves();
    const cell = svg
      .selectAll("g")
      .data(leaves)
      .join("g")
      .attr("transform", (d) => `translate(${d.x0},${d.y0})`);

    cell
      .append("rect")
      .attr("width", (d) => Math.max(0, d.x1 - d.x0))
      .attr("height", (d) => Math.max(0, d.y1 - d.y0))
      .attr("rx", 3)
      .attr("fill", (d) => heat(d.data.change_frequency || 0))
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 1)
      .style("cursor", "default")
      .on("mouseenter", (event, d) => {
        const rect = wrapRef.current.getBoundingClientRect();
        setTip({ x: event.clientX - rect.left + 12, y: event.clientY - rect.top + 12, d: d.data });
      })
      .on("mousemove", (event) => {
        const rect = wrapRef.current.getBoundingClientRect();
        setTip((t) => (t ? { ...t, x: event.clientX - rect.left + 12, y: event.clientY - rect.top + 12 } : t));
      })
      .on("mouseleave", () => setTip(null));

    // Labels for cells big enough to hold text.
    cell
      .filter((d) => d.x1 - d.x0 > 46 && d.y1 - d.y0 > 18)
      .append("text")
      .attr("x", 5)
      .attr("y", 14)
      .attr("font-size", 11)
      .attr("fill", (d) => ((d.data.change_frequency || 0) > maxChange * 0.55 ? "#fff" : "#334155"))
      .text((d) => d.data.name)
      .each(function (d) {
        // Trim label to fit cell width.
        const maxW = d.x1 - d.x0 - 8;
        let t = d3.select(this);
        let txt = d.data.name;
        while (this.getComputedTextLength() > maxW && txt.length > 1) {
          txt = txt.slice(0, -1);
          t.text(txt + "…");
        }
      });
  }, [data, width, maxChange]);

  if (loading) return <Spinner />;
  if (error) return <Empty title="Couldn’t load structure" hint={error} />;
  if (!data.treemap || !data.treemap.children?.length) {
    return <Empty title="No files to map" />;
  }

  return (
    <Card
      title="Directory treemap"
      subtitle="Each rectangle is a file · area = lines of code · color = how often it changes"
      right={
        <div className="flex items-center gap-2 text-xs text-ink-500">
          rarely
          <span className="h-2 w-24 rounded-full" style={{ background: "linear-gradient(90deg,#dbe4f5,#dc2626)" }} />
          often
        </div>
      }
    >
      <div ref={wrapRef} className="relative w-full">
        <svg ref={svgRef} width="100%" height={560} />
        {tip && (
          <div
            className="pointer-events-none absolute z-10 rounded-lg border border-hairline bg-white px-3 py-2 shadow-lift text-xs max-w-xs"
            style={{ left: tip.x, top: tip.y }}
          >
            <div className="font-mono text-ink-900 break-all">{tip.d.path}</div>
            <div className="text-ink-500 mt-1">
              {fmtNumber(tip.d.size)} LOC
              {tip.d.language ? ` · ${tip.d.language}` : ""}
              {` · ${tip.d.change_frequency || 0} changes`}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
