import { test, expect } from "@playwright/test";

// Minimal compliance and UX checks without external deps (axe-core)
// Focus on semantic landmarks, headings, alt text, link names, and basic error messaging.

test.describe("Compliance :: Accessibility & Semantics", () => {
  test("home page exposes main landmark and H1", async ({ page }) => {
    await page.goto("/");
    const main = page.locator("main");
    await expect(main, "Missing <main> landmark").toBeVisible();

    const h1 = page.locator("h1").first();
    await expect(h1, "Missing top-level <h1>").toBeVisible();
  });

  test("images provide alt text", async ({ page }) => {
    await page.goto("/");
    const missingAltCount = await page.$$eval("img", (imgs) =>
      imgs.filter((img) => {
        const alt = img.getAttribute("alt");
        return !alt || alt.trim().length === 0;
      }).length
    );
    expect(missingAltCount, `Found ${missingAltCount} <img> without alt`).toBe(0);
  });

  test("links have accessible names (text/aria-label/title)", async ({ page }) => {
    await page.goto("/");
    const namelessLinks = await page.$$eval("a", (anchors) =>
      anchors.filter((a) => {
        const text = (a.textContent || "").trim();
        const aria = (a.getAttribute("aria-label") || "").trim();
        const title = (a.getAttribute("title") || "").trim();
        return text.length === 0 && aria.length === 0 && title.length === 0;
      }).length
    );
    expect(namelessLinks, `Found ${namelessLinks} <a> without accessible name`).toBe(0);
  });

  test("viewport meta present for responsive UX", async ({ page }) => {
    await page.goto("/");
    const hasViewport = await page.$('meta[name="viewport"]');
    expect(!!hasViewport, "Missing viewport meta tag").toBe(true);
  });
});

test.describe("Compliance :: Error Handling & UX Signals", () => {
  test("api error surfaces user-friendly feedback (alert or message)", async ({ page }) => {
    await page.route("**/api/v1/notebook/list", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Simulated Backend Failure" }),
      })
    );

    await page.goto("/notebook");

    const roleAlert = page.locator('[role="alert"]').first();
    const genericError = page
      .locator("text=Error, text=failed, text=went wrong")
      .first();
    const safeFallback = page.locator("text=No notebooks").first();

    await expect(roleAlert.or(genericError).or(safeFallback)).toBeVisible();
  });
});
