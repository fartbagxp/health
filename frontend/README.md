# frontend — funding-flow graph (Svelte Flow)

The interactive federal → state → county **money-flow graph** embedded on the docs
front page and on [Funding & Governance](../docs/funding.md). Built with
[`@xyflow/svelte`](https://svelte.xyflow.com/) (Svelte Flow) + Svelte 5, compiled by
Vite into a single self-mounting bundle.

## How it fits together

```
data/processed/health_depts/summary.json   (scraped by `health_depts`)
        │  imported at build time (baked into the bundle — no runtime fetch)
        ▼
frontend/  ──pnpm build──▶  docs/funding-flow/{funding-flow.js,funding-flow.css}
        │                          │  zensical passes these through
        ▼                          ▼
  <div id="funding-flow">   served on the docs site; the script mounts the
  in docs/index.md &        Svelte app into every #funding-flow container
  docs/funding.md
```

`src/model.js` holds the conceptual model (CDC mechanisms → repo datasets) and the
`build(stateCode)` graph builder; `App.svelte` is the shell (state selector, legend,
stats); `FlowGraph.svelte` wraps `<SvelteFlow>`; `CardNode.svelte` is the custom node.

## Develop

```bash
cd frontend
pnpm install
pnpm dev      # local preview at the printed URL
pnpm build    # compile into ../docs/funding-flow/
```

`pnpm build` is run automatically in CI by `.github/workflows/docs.yml` before
`zensical build`, so the compiled bundle is never committed (it is `.gitignore`d).
When the monthly scrape refreshes `summary.json`, the docs deploy rebuilds the graph
with the new data.

## Notes

- **No runtime fetch.** The scrape data is imported as JSON at build time, so the
  graph is fully static once compiled — it works on GitHub Pages with no API.
- **Theme.** The graph follows the docs' own light/dark toggle
  (`[data-md-color-scheme="slate"]`) and falls back to the OS setting elsewhere.
- **pnpm.** `pnpm-workspace.yaml` allowlists esbuild's post-install (pnpm 11 gates
  build scripts); `packageManager` pins pnpm for corepack in CI.
