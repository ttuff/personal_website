(() => {
  "use strict";

  const PRODUCTION_HOSTNAME = "drtuff.com";
  const PRODUCTION_ORIGIN = `https://${PRODUCTION_HOSTNAME}`;
  const PLACEHOLDER_ID = "G-XXXXXXXXXX";
  const script = document.currentScript;
  const measurementId = (script?.dataset.measurementId || "").trim().toUpperCase();

  if (
    window.location.hostname !== PRODUCTION_HOSTNAME ||
    measurementId === PLACEHOLDER_ID ||
    !/^G-[A-Z0-9]+$/.test(measurementId) ||
    window.__drTuffAnalyticsInitialized
  ) {
    return;
  }
  window.__drTuffAnalyticsInitialized = true;

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function gtag() {
    window.dataLayer.push(arguments);
  };

  const pagePath = window.location.pathname;
  const pageLocation = `${PRODUCTION_ORIGIN}${pagePath}`;
  const loader = document.createElement("script");
  loader.async = true;
  loader.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
  document.head.appendChild(loader);

  window.gtag("js", new Date());
  window.gtag("config", measurementId, {
    send_page_view: false,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    page_location: pageLocation,
    page_path: pagePath,
  });
  window.gtag("event", "page_view", {
    send_to: measurementId,
    page_title: document.title,
    page_location: pageLocation,
    page_path: pagePath,
  });

  const internalHosts = new Set([PRODUCTION_HOSTNAME, `www.${PRODUCTION_HOSTNAME}`]);

  function linkCategory(url, anchor) {
    const hostname = url.hostname.toLowerCase();
    if (hostname === "github.com") return "github";
    if (hostname === "scholar.google.com") return "google_scholar";
    if (hostname === "orcid.org") return "orcid";
    if (
      hostname.endsWith(".github.io") ||
      anchor.closest(".project-section, .projects-public, .github-life, [data-projects-page]")
    ) {
      return "external_project";
    }
    return "outbound";
  }

  function sanitizedUrl(url) {
    return url.origin;
  }

  function sanitizedProjectUrl(url) {
    return `${url.origin}${url.pathname}`;
  }

  document.addEventListener("click", (event) => {
    const anchor = event.target?.closest?.("a[href]");
    if (!anchor) return;

    let url;
    try {
      url = new URL(anchor.href, window.location.href);
    } catch (_error) {
      return;
    }
    if (!/^https?:$/.test(url.protocol)) return;

    const destinationDomain = url.hostname.toLowerCase();
    const eventParameters = {
      send_to: measurementId,
      link_url: sanitizedUrl(url),
      destination_domain: destinationDomain,
      page_path: pagePath,
    };

    const projectName = (anchor.dataset.projectName || "").trim();
    const projectLinkType = (anchor.dataset.projectLinkType || "").trim();
    if (projectName && ["website", "github"].includes(projectLinkType)) {
      window.gtag(
        "event",
        projectLinkType === "github" ? "project_github_click" : "project_visit",
        {
          send_to: measurementId,
          project_name: projectName,
          destination_url: sanitizedProjectUrl(url),
          destination_domain: destinationDomain,
          source_page: pagePath,
          link_type: projectLinkType,
        },
      );
      return;
    }

    if (url.pathname.toLowerCase().endsWith(".pdf")) {
      window.gtag("event", "file_download", {
        ...eventParameters,
        file_extension: "pdf",
        file_category:
          document.body.classList.contains("page-my-cv") ||
          /(?:^|[-_/])(cv|resume|curriculum[-_]?vitae)(?:[-_. /]|$)/i.test(url.pathname)
            ? "cv"
            : "other_pdf",
      });
      return;
    }

    if (!internalHosts.has(destinationDomain)) {
      window.gtag("event", "outbound_click", {
        ...eventParameters,
        link_category: linkCategory(url, anchor),
      });
    }
  });
})();
