import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// Sitemap is consumed by Google Search Console + Bing IndexNow + the
// AI crawlers that read /llms.txt for an inventory of canonical URLs.
// Keep listings limited to public, indexable routes — anything noindex
// (login, dashboard, account, search results) belongs in robots.txt
// disallow or per-route metadata.robots, not here.

const ROUTES: { path: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"] }[] = [
  { path: "/",               priority: 1.0, changeFrequency: "weekly" },
  { path: "/services",       priority: 0.9, changeFrequency: "weekly" },
  { path: "/pricing",        priority: 0.9, changeFrequency: "monthly" },
  { path: "/find-lawyer",    priority: 0.9, changeFrequency: "weekly" },
  { path: "/docs/install",   priority: 0.8, changeFrequency: "weekly" },
  { path: "/form-8843",      priority: 0.8, changeFrequency: "monthly" },
  { path: "/connect",        priority: 0.7, changeFrequency: "monthly" },
  // Per-service detail pages — wizard entry points users land on from
  // the marketplace listing or external links.
  { path: "/services/form_8843_free",       priority: 0.7, changeFrequency: "monthly" },
  { path: "/services/student_tax_1040nr",   priority: 0.7, changeFrequency: "monthly" },
  { path: "/services/h1b_doc_check",        priority: 0.7, changeFrequency: "monthly" },
  { path: "/services/fbar_check",           priority: 0.7, changeFrequency: "monthly" },
  { path: "/services/election_83b",         priority: 0.6, changeFrequency: "monthly" },
  { path: "/services/opt_execution",        priority: 0.6, changeFrequency: "monthly" },
  { path: "/services/opt_advisory",         priority: 0.6, changeFrequency: "monthly" },
  { path: "/privacy",        priority: 0.4, changeFrequency: "yearly" },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return ROUTES.map((r) => ({
    url: `${SITE_URL}${r.path}`,
    lastModified: now,
    changeFrequency: r.changeFrequency,
    priority: r.priority,
  }));
}
