import { test, expect, type Page } from "@playwright/test";

// Stubs check creation + fetch so the page reaches the upload UI, and records
// every document-upload POST so tests can assert when egress actually fires.
async function stubRoutes(page: Page, uploadCalls: string[]): Promise<void> {
  await page.route("**/api/checks/**", async (route) => {
    const url = route.request().url();
    if (/\/documents$/.test(url) && route.request().method() === "POST") {
      uploadCalls.push(url);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "test-check", track: "stem_opt", documents: [] }) });
  });
}

const TEST_FILE = { name: "i20.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 test") };

test("no document upload fires until the user approves", async ({ page }) => {
  const uploadCalls: string[] = [];
  await stubRoutes(page, uploadCalls);

  await page.goto("/check/stem-opt/upload?id=test-check");

  // Select a file into the first slot.
  const input = page.getByTestId(/stem-upload-input-/).first();
  await input.setInputFiles(TEST_FILE);

  // The consent modal must appear, and NO upload may have fired yet.
  await expect(page.getByTestId("egress-consent-modal")).toBeVisible();
  expect(uploadCalls).toHaveLength(0);

  // Approve once → exactly one upload fires.
  await page.getByTestId("consent-once").click();
  await expect.poll(() => uploadCalls.length).toBe(1);
});

test("Deny → no upload", async ({ page }) => {
  const uploadCalls: string[] = [];
  await stubRoutes(page, uploadCalls);

  await page.goto("/check/stem-opt/upload?id=test-check");

  const input = page.getByTestId(/stem-upload-input-/).first();
  await input.setInputFiles(TEST_FILE);

  await expect(page.getByTestId("egress-consent-modal")).toBeVisible();
  expect(uploadCalls).toHaveLength(0);

  // Deny → modal closes and no upload ever fires.
  await page.getByTestId("consent-deny").click();
  await page.waitForTimeout(300);
  expect(uploadCalls).toHaveLength(0);
});

test("Allow for this session → second file skips the modal and uploads", async ({ page }) => {
  const uploadCalls: string[] = [];
  await stubRoutes(page, uploadCalls);

  await page.goto("/check/stem-opt/upload?id=test-check");

  // First slot: pick a file, grant for the session, wait for the upload.
  const inputs = page.getByTestId(/stem-upload-input-/);
  await inputs.first().setInputFiles(TEST_FILE);
  await expect(page.getByTestId("egress-consent-modal")).toBeVisible();
  await page.getByTestId("consent-session").click();
  await expect.poll(() => uploadCalls.length).toBe(1);

  // Second slot: session consent is held, so no modal should reappear.
  await inputs.nth(1).setInputFiles(TEST_FILE);
  await expect(page.getByTestId("egress-consent-modal")).toHaveCount(0);
  await expect.poll(() => uploadCalls.length).toBe(2);
});
