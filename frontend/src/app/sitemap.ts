import type { MetadataRoute } from "next";

const BASE = "https://guardiancompliance.app";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const routes = [
    { path: "/",                priority: 1.0, changeFrequency: "weekly" as const },
    { path: "/services",        priority: 0.9, changeFrequency: "weekly" as const },
    { path: "/docs/install",    priority: 0.9, changeFrequency: "weekly" as const },
    { path: "/connect",         priority: 0.8, changeFrequency: "monthly" as const },
    { path: "/form-8843",       priority: 0.8, changeFrequency: "monthly" as const },
    { path: "/login",           priority: 0.3, changeFrequency: "yearly" as const },
  ];
  return routes.map((r) => ({
    url: `${BASE}${r.path}`,
    lastModified: now,
    changeFrequency: r.changeFrequency,
    priority: r.priority,
  }));
}
