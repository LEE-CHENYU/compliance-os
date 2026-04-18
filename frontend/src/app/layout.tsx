import type { Metadata } from "next";
import Script from "next/script";

import MixpanelIdentitySync from "@/components/analytics/MixpanelIdentitySync";

import "./globals.css";
import { ThemeProvider } from "@/lib/theme";

const MIXPANEL_TOKEN = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN?.trim();
const MIXPANEL_BOOTSTRAP = MIXPANEL_TOKEN ? `
  (function(e){
    if (window.__guardianMixpanelBootstrapped) return;
    if (window.mixpanel && typeof window.mixpanel.identify === "function" && !Array.isArray(window.mixpanel)) {
      window.__guardianMixpanelBootstrapped = true;
      return;
    }

    var c = window.mixpanel = window.mixpanel || [];
    if (c.__SV) {
      window.__guardianMixpanelBootstrapped = true;
      return;
    }

    var l, h;
    c._i = [];
    c.init = function(q,r,f){function t(d,a){var g=a.split(".");2==g.length&&(d=d[g[0]],a=g[1]);d[a]=function(){d.push([a].concat(Array.prototype.slice.call(arguments,0)))}}var b=c;"undefined"!==typeof f?b=c[f]=[]:f="mixpanel";b.people=b.people||[];b.toString=function(d){var a="mixpanel";"mixpanel"!==f&&(a+="."+f);d||(a+=" (stub)");return a};b.people.toString=function(){return b.toString(1)+".people (stub)"};l="disable time_event track track_pageview track_links track_forms track_with_groups add_group set_group remove_group register register_once alias unregister identify name_tag set_config reset opt_in_tracking opt_out_tracking has_opted_in_tracking has_opted_out_tracking clear_opt_in_out_tracking start_batch_senders start_session_recording stop_session_recording people.set people.set_once people.unset people.increment people.append people.union people.track_charge people.clear_charges people.delete_user people.remove".split(" ");
    for(h=0;h<l.length;h++)t(b,l[h]);var n="set set_once union unset remove delete".split(" ");b.get_group=function(){function d(p){a[p]=function(){b.push([g,[p].concat(Array.prototype.slice.call(arguments,0))])}}for(var a={},g=["get_group"].concat(Array.prototype.slice.call(arguments,0)),m=0;m<n.length;m++)d(n[m]);return a};c._i.push([q,r,f])};
    c.__SV = 1.2;
    window.__guardianMixpanelBootstrapped = true;
    var k = e.createElement("script");
    k.type = "text/javascript";
    k.async = true;
    k.src = "undefined"!==typeof MIXPANEL_CUSTOM_LIB_URL?MIXPANEL_CUSTOM_LIB_URL:"file:"===e.location.protocol&&"//cdn.mxpnl.com/libs/mixpanel-2-latest.min.js".match(/^\\/\\//)?"https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js":"//cdn.mxpnl.com/libs/mixpanel-2-latest.min.js";
    e = e.getElementsByTagName("script")[0];
    e.parentNode.insertBefore(k,e);
  })(document);

  mixpanel.init('${MIXPANEL_TOKEN}', {
    autocapture: false,
    track_pageview: true,
  });
` : "";

const SITE_URL = "https://guardiancompliance.app";
const SITE_NAME = "Guardian";
const SITE_DESC =
  "Guardian cross-checks your immigration and tax documents to find mismatches, missing forms, and deadline risks before USCIS or the IRS does. Built for F-1 / OPT / STEM OPT / H-1B workers, international students, and nonresident-alien entrepreneurs with US entities.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Guardian — compliance copilot for visas, tax, and entities",
    template: "%s · Guardian",
  },
  description: SITE_DESC,
  applicationName: SITE_NAME,
  keywords: [
    "H-1B", "STEM OPT", "CPT", "OPT", "F-1 visa", "I-983", "I-20",
    "Form 8843", "Form 1040-NR", "FBAR", "Form 5472", "Form 1120",
    "nonresident tax", "immigration compliance", "tax compliance",
    "immigration attorney data room", "CPA data room",
    "MCP server", "Model Context Protocol",
    "Claude Code", "Claude Desktop", "Codex",
  ],
  authors: [{ name: "Guardian" }],
  creator: "Guardian",
  publisher: "Guardian",
  alternates: { canonical: SITE_URL },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: "Guardian — compliance copilot for visas, tax, and entities",
    description: SITE_DESC,
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Guardian — compliance copilot for visas, tax, and entities",
    description: SITE_DESC,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-snippet": -1, "max-image-preview": "large" },
  },
  icons: { icon: "/favicon.ico" },
  category: "productivity",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const enableMixpanel = process.env.NODE_ENV === "production" && Boolean(MIXPANEL_TOKEN);

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {enableMixpanel && (
          <Script
            id="mixpanel"
            strategy="afterInteractive"
            dangerouslySetInnerHTML={{ __html: MIXPANEL_BOOTSTRAP }}
          />
        )}
      </head>
      <body className="min-h-screen bg-[#e8eff6] dark:bg-[#121620] transition-colors duration-300">
        <ThemeProvider>
          {enableMixpanel && <MixpanelIdentitySync />}
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
