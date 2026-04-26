// Single source of truth for site-wide SEO constants. Imported by
// metadata exports in route-level layout.tsx files and JSON-LD schema
// components. Keeping this in one place makes it cheap to migrate
// domains and prevents canonical drift between pages.

export const SITE_URL = "https://guardiancompliance.app";
export const SITE_NAME = "Guardian";
export const SITE_DESC =
  "Guardian cross-checks your immigration and tax documents to find mismatches, missing forms, and deadline risks before USCIS or the IRS does. Built for F-1 / OPT / STEM OPT / H-1B workers, international students, and nonresident-alien entrepreneurs with US entities.";
// 1200x630 PNG used by OG/Twitter cards. Falls back to logo until a
// branded card image lands at /og-image.png.
export const OG_IMAGE = "/assets/guardian-logo-1024.png";

export function absoluteUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
