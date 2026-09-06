<script>
  import FlowGraph from "./FlowGraph.svelte";
  import { build, stateOptions, STATES, TOTAL_LOCALS } from "./model.js";

  const codes = stateOptions();
  let selected = $state(codes.includes("AL") ? "AL" : codes[0]);

  let graph = $derived(build(selected));
</script>

<div class="ff-root">
  <header class="ff-bar">
    <div class="ff-brand">
      <h2>How the money reaches the county</h2>
      <p>CDC appropriations flow down through cooperative agreements; the surveillance they fund flows back up as the datasets this repo collects.</p>
    </div>

    <div class="ff-picker">
      <label for="ff-state">State</label>
      <select id="ff-state" bind:value={selected}>
        {#each codes as c (c)}
          <option value={c}>{STATES[c].name}</option>
        {/each}
      </select>
    </div>

    <div class="ff-legend">
      <span class="ff-leg"><span class="ff-swatch money"></span> Federal dollars</span>
      <span class="ff-leg"><span class="ff-swatch data"></span> Data reported up</span>
    </div>

    <div class="ff-stats">
      <div class="ff-stat"><b>{graph.st.county_count ?? (graph.st.counties || []).length}</b><span>Local depts</span></div>
      <div class="ff-stat"><b>{TOTAL_LOCALS.toLocaleString()}</b><span>Nationwide</span></div>
    </div>
  </header>

  <div class="ff-canvas">
    {#key selected}
      <FlowGraph {graph} />
    {/key}
  </div>
</div>
