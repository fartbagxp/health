import "@xyflow/svelte/dist/style.css";
import "./app.css";
import { mount } from "svelte";
import App from "./App.svelte";

// Mount into any #funding-flow container present on the page (front page + funding page).
for (const el of document.querySelectorAll("#funding-flow")) {
  mount(App, { target: el });
}
