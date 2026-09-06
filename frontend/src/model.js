// Conceptual money-flow model + graph builder.
// The scraped state/county roster is imported at build time (baked into the
// bundle), so the compiled graph carries the data with no runtime fetch.

import summary from "../../data/processed/health_depts/summary.json";

export const STATES = summary.states;
export const TOTAL_LOCALS = summary.generated_locals ?? 0;

// CDC funding mechanisms -> the datasets this repo collects.
export const MECHS = [
  { id: "elc", k: "ELC", t: "Epidemiology & Lab Capacity", ds: ["nndss", "nors", "beam"] },
  { id: "phep", k: "PHEP", t: "Emergency Preparedness", ds: ["nssp"] },
  { id: "brfss", k: "BRFSS", t: "Behavioral risk survey", ds: ["places"] },
  { id: "npcr", k: "NPCR", t: "Cancer registries", ds: ["seer"] },
  { id: "imm", k: "§317", t: "Immunization program", ds: ["nis"] },
  { id: "epht", k: "EPHT", t: "Environmental tracking", ds: ["epht"] },
  { id: "nvss", k: "NVSS", t: "Vital statistics coop.", ds: ["wonder"] },
];

export const DATASETS = [
  { id: "nndss", k: "NNDSS", t: "Notifiable diseases" },
  { id: "nors", k: "NORS", t: "Outbreak reporting" },
  { id: "beam", k: "BEAM", t: "Enteric pathogens" },
  { id: "nssp", k: "NSSP", t: "ED syndromic visits" },
  { id: "places", k: "PLACES", t: "Small-area estimates" },
  { id: "seer", k: "SEER", t: "Cancer statistics" },
  { id: "nis", k: "NIS", t: "Vaccination coverage" },
  { id: "epht", k: "EPHT", t: "Env. health tracking" },
  { id: "wonder", k: "WONDER", t: "Mortality & natality" },
];

const X = { cdc: 20, mech: 250, state: 545, county: 820, ds: 1120 };
const MECH_GAP = 78;
const DS_GAP = 74;
const COUNTY_GAP = 44;
const COUNTY_CAP = 48;
const MID = 40 + ((MECHS.length - 1) * MECH_GAP) / 2;

const MONEY = "stroke: var(--ff-money); stroke-width: 1.8;";
const MONEY_FAINT = "stroke: var(--ff-money); stroke-width: 1.1; opacity: 0.5;";
const MONEY_HAIR = "stroke: var(--ff-money); stroke-width: 1; opacity: 0.38;";
const DATA = "stroke: var(--ff-data); stroke-width: 1.4; stroke-dasharray: 6 4; opacity: 0.85;";

function arrow(color, size = 15) {
  return { type: "arrowclosed", color, width: size, height: size };
}

function node(id, variant, x, y, k, t) {
  return {
    id,
    type: "card",
    position: { x, y },
    data: { variant, k, t },
    sourcePosition: "right",
    targetPosition: "left",
    selectable: false,
    draggable: false,
  };
}

export function build(code) {
  const st = STATES[code] || { name: code, dept: "", counties: [], county_count: 0 };
  const nodes = [];
  const edges = [];

  nodes.push(node("cdc", "cdc", X.cdc, MID - 14, "CDC", "Federal appropriation"));

  MECHS.forEach((m, i) => {
    const y = 40 + i * MECH_GAP;
    nodes.push(node("m-" + m.id, "mech", X.mech, y, m.k, m.t));
    edges.push({ id: "e-cdc-" + m.id, source: "cdc", target: "m-" + m.id, type: "smoothstep", animated: true, style: MONEY, markerEnd: arrow("var(--ff-money)") });
    edges.push({ id: "e-" + m.id + "-state", source: "m-" + m.id, target: "state", type: "smoothstep", animated: true, style: MONEY_FAINT });
  });

  nodes.push(node("state", "state", X.state, MID - 22, st.name, st.dept || "Department of Public Health"));

  const counties = st.counties || [];
  const shown = counties.slice(0, COUNTY_CAP);
  const colH = (Math.max(shown.length, 1) - 1) * COUNTY_GAP;
  const startY = MID - colH / 2 - (counties.length > COUNTY_CAP ? COUNTY_GAP / 2 : 0);
  shown.forEach((name, i) => {
    const id = "c-" + i;
    nodes.push(node(id, "county", X.county, startY + i * COUNTY_GAP, name, null));
    edges.push({ id: "e-state-" + id, source: "state", target: id, type: "smoothstep", animated: true, style: MONEY_HAIR });
  });
  if (counties.length > COUNTY_CAP) {
    const my = startY + shown.length * COUNTY_GAP;
    nodes.push(node("c-more", "more", X.county, my, "+ " + (counties.length - COUNTY_CAP) + " more", "local health departments"));
    edges.push({ id: "e-state-more", source: "state", target: "c-more", type: "smoothstep", animated: true, style: MONEY_HAIR });
  }

  DATASETS.forEach((d, i) => {
    nodes.push(node("d-" + d.id, "dataset", X.ds, 40 + i * DS_GAP, d.k, d.t));
  });
  MECHS.forEach((m) => {
    m.ds.forEach((dsid) => {
      edges.push({ id: "e-data-" + m.id + "-" + dsid, source: "state", target: "d-" + dsid, type: "smoothstep", animated: true, style: DATA, markerEnd: arrow("var(--ff-data)", 13) });
    });
  });

  return { nodes, edges, st };
}

export function stateOptions() {
  return Object.keys(STATES).sort((a, b) =>
    (STATES[a].name || a).localeCompare(STATES[b].name || b),
  );
}
