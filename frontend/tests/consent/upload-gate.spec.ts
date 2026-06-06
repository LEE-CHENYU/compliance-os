import { test, expect } from "@playwright/test";

// Drives the stem-opt upload page; stubs the API so no real backend is needed.
test("no document upload fires until the user approves", async ({ page }) => {
  const uploadCalls: string[] = [];

  // Stub check creation + fetch so the page reaches the upload UI.
  await page.route("**/api/checks/**", async (route) => {
    const url = route.request().url();
    if (/\/documents$/.test(url) && route.request().method() === "POST") {
      uploadCalls.push(url);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "test-check", track: "stem_opt", documents: [] }) });
  });

  await page.goto("/check/stem-opt/upload?id=test-check");

  // Select a file into the first slot.
  const input = page.getByTestId(/stem-upload-input-/).first();
  await input.setInputFiles({ name: "i20.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 test") });

  // The consent modal must appear, and NO upload may have fired yet.
  await expect(page.getByTestId("egress-consent-modal")).toBeVisible();
  expect(uploadCalls).toHaveLength(0);

  // Approve once → exactly one upload fires.
  await page.getByTestId("consent-once").click();
  await expect.poll(() => uploadCalls.length).toBe(1);
});
