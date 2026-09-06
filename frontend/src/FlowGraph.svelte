<script>
  import { untrack } from "svelte";
  import { SvelteFlow, Background, MiniMap } from "@xyflow/svelte";
  import CardNode from "./CardNode.svelte";

  let { graph } = $props();

  // App re-keys this component whenever the state changes, so each instance is
  // seeded once from the fresh graph (untrack silences the reactive-capture
  // warning) and fitView re-frames the view on remount.
  let nodes = $state.raw(untrack(() => graph.nodes));
  let edges = $state.raw(untrack(() => graph.edges));

  const nodeTypes = { card: CardNode };

  const miniColor = (n) => {
    const v = n.data?.variant || "";
    if (v === "cdc" || v === "federal") return "var(--ff-federal)";
    if (v === "mech") return "var(--ff-mech)";
    if (v === "state") return "var(--ff-state)";
    if (v === "dataset") return "var(--ff-dataset)";
    return "var(--ff-county)";
  };
</script>

<SvelteFlow
  bind:nodes
  bind:edges
  {nodeTypes}
  colorMode="system"
  fitView
  fitViewOptions={{ padding: 0.1 }}
  nodesDraggable={false}
  nodesConnectable={false}
  elementsSelectable={false}
  zoomOnScroll={false}
  zoomOnPinch={false}
  zoomOnDoubleClick={false}
  panOnDrag={false}
  panOnScroll={false}
  preventScrolling={false}
  proOptions={{ hideAttribution: true }}
>
  <Background gap={22} />
  <MiniMap pannable={false} zoomable={false} nodeColor={miniColor} />
</SvelteFlow>
