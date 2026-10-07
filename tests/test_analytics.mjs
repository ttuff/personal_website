import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../static/scripts/analytics.js", import.meta.url), "utf8");

function createRuntime({ hostname = "drtuff.com", measurementId = "G-TEST123", bodyClass = "" } = {}) {
  const appendedScripts = [];
  let clickHandler;
  const document = {
    currentScript: { dataset: { measurementId } },
    title: "Test page",
    body: { classList: { contains: (name) => bodyClass.split(" ").includes(name) } },
    head: { appendChild: (element) => appendedScripts.push(element) },
    createElement: (tagName) => ({ tagName, async: false, src: "" }),
    addEventListener: (type, handler) => {
      if (type === "click") clickHandler = handler;
    },
  };
  const window = {
    location: {
      hostname,
      pathname: "/my-cv/",
      href: `https://${hostname}/my-cv/?private=not-sent`,
    },
  };
  const context = vm.createContext({ document, window, URL, Set, Date, encodeURIComponent });
  vm.runInContext(source, context);

  function click(href, { project = false, projectName = "", linkType = "" } = {}) {
    const anchor = {
      href,
      dataset: { projectName, projectLinkType: linkType },
      closest: () => (project ? {} : null),
    };
    clickHandler?.({ target: { closest: () => anchor } });
  }

  return { appendedScripts, click, context, document, window };
}

function commands(runtime) {
  return Array.from(runtime.window.dataLayer || [], (entry) => Array.from(entry));
}

test("analytics stays disabled outside the canonical production hostname", () => {
  for (const hostname of ["localhost", "127.0.0.1", "ttuff.github.io"]) {
    const runtime = createRuntime({ hostname });
    assert.equal(runtime.appendedScripts.length, 0);
    assert.equal(runtime.window.dataLayer, undefined);
  }
});

test("the placeholder measurement ID keeps production tracking disabled", () => {
  const runtime = createRuntime({ measurementId: "G-XXXXXXXXXX" });
  assert.equal(runtime.appendedScripts.length, 0);
  assert.equal(runtime.window.dataLayer, undefined);
});

test("production initializes gtag once and sends one explicit page view", () => {
  const runtime = createRuntime();
  vm.runInContext(source, runtime.context);
  const queued = commands(runtime);

  assert.equal(runtime.appendedScripts.length, 1);
  assert.equal(runtime.appendedScripts[0].async, true);
  assert.match(runtime.appendedScripts[0].src, /^https:\/\/www\.googletagmanager\.com\/gtag\/js\?id=G-TEST123$/);
  assert.equal(queued.filter((entry) => entry[0] === "config").length, 1);
  assert.equal(queued.find((entry) => entry[0] === "config")[2].send_page_view, false);
  assert.equal(queued.filter((entry) => entry[0] === "event" && entry[1] === "page_view").length, 1);
  assert.equal(queued.find((entry) => entry[1] === "page_view")[2].page_location, "https://drtuff.com/my-cv/");
});

test("internal links are ignored and outbound destinations are categorized without path-level data", () => {
  const runtime = createRuntime();
  const initialCount = commands(runtime).length;

  runtime.click("https://drtuff.com/my-science/?email=not-sent");
  runtime.click("https://www.drtuff.com/my-projects/");
  assert.equal(commands(runtime).length, initialCount);

  runtime.click("https://github.com/ttuff/example?token=not-sent#readme");
  runtime.click("https://scholar.google.com/citations?user=not-sent");
  runtime.click("https://orcid.org/0000-0000-0000-0000");
  runtime.click("https://earthlab.github.io/example/?private=not-sent", { project: true });

  const events = commands(runtime).slice(initialCount);
  assert.deepEqual(events.map((entry) => entry[1]), ["outbound_click", "outbound_click", "outbound_click", "outbound_click"]);
  assert.deepEqual(events.map((entry) => entry[2].link_category), ["github", "google_scholar", "orcid", "external_project"]);
  assert.equal(events[0][2].link_url, "https://github.com");
  assert.equal(events[1][2].link_url, "https://scholar.google.com");
  assert.ok(events.every((entry) => !entry[2].link_url.includes("?") && !entry[2].link_url.includes("#")));
});

test("PDF links send one file_download event and distinguish a CV", () => {
  const runtime = createRuntime({ bodyClass: "page-my-cv" });
  const initialCount = commands(runtime).length;
  runtime.click("https://files.example.org/Ty-Tuff-CV.pdf?email=not-sent#download");

  const events = commands(runtime).slice(initialCount);
  assert.equal(events.length, 1);
  assert.equal(events[0][1], "file_download");
  assert.equal(events[0][2].file_category, "cv");
  assert.equal(events[0][2].file_extension, "pdf");
  assert.equal(events[0][2].link_url, "https://files.example.org");
});

test("project website and GitHub actions use distinct non-PII events", () => {
  const runtime = createRuntime();
  const initialCount = commands(runtime).length;
  runtime.click("https://cu-esiil.github.io/fire_vase/?visitor=not-sent#results", {
    project: true,
    projectName: "Fire VASE",
    linkType: "website",
  });
  runtime.click("https://github.com/CU-ESIIL/fire_vase?token=not-sent#readme", {
    project: true,
    projectName: "Fire VASE",
    linkType: "github",
  });

  const events = commands(runtime).slice(initialCount);
  assert.deepEqual(events.map((entry) => entry[1]), ["project_visit", "project_github_click"]);
  assert.deepEqual(events.map((entry) => entry[2].link_type), ["website", "github"]);
  assert.ok(events.every((entry) => entry[2].project_name === "Fire VASE"));
  assert.equal(events[0][2].destination_url, "https://cu-esiil.github.io/fire_vase/");
  assert.equal(events[1][2].destination_url, "https://github.com/CU-ESIIL/fire_vase");
  assert.ok(events.every((entry) => !entry[2].destination_url.includes("?") && !entry[2].destination_url.includes("#")));
});
