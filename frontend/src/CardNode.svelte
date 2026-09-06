<script>
  import { Handle, Position } from "@xyflow/svelte";

  let { data } = $props();
</script>

<Handle type="target" position={Position.Left} />
<div class="ff-nd {data.variant}">
  <div class="ff-k">{data.k}</div>
  {#if data.t}<div class="ff-t">{data.t}</div>{/if}
</div>
<Handle type="source" position={Position.Right} />
