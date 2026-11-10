export function render(graph, container) {
  const evidenceElement = container.querySelector("[data-evidence]");
  const nodes = new vis.DataSet(graph.entities.map((entity) => ({id: entity.id, label: entity.name, title: entity.type})));
  const edges = new vis.DataSet(graph.edges.map((edge, index) => ({id: index, from: edge.head_id, to: edge.tail_id, label: edge.relation, evidence: edge.evidence})));
  new vis.Network(container.querySelector("[data-graph]"), {nodes, edges}, {interaction: {hover: true}}).on("selectEdge", (event) => {
    evidenceElement.textContent = event.edges.length ? edges.get(event.edges[0]).evidence.join("\n") : "";
  });
}

async function loadSharedGraph() {
  const shareId = window.location.pathname.split("/").pop();
  const response = await fetch(`/v1/share/${encodeURIComponent(shareId)}`);
  if (response.ok) render(await response.json(), document);
}

if (window.location.pathname.startsWith("/g/")) loadSharedGraph();
