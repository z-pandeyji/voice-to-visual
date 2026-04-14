import { test, expect, Page } from "@playwright/test";

// ── Helpers ────────────────────────────────────────────────────────────────

async function mockBrowserAPIs(page: Page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "mediaDevices", {
      value: {
        getUserMedia: async () => ({
          getTracks: () => [{ stop: () => {} }],
        }),
      },
      writable: true,
    });

    (window as any).MediaRecorder = class MockMediaRecorder {
      ondataavailable: ((e: any) => void) | null = null;
      onstop: (() => void) | null = null;

      start() {
        setTimeout(() => {
          if (this.ondataavailable) {
            this.ondataavailable({
              data: new Blob(["fake-audio"], { type: "audio/webm" }),
              size: 10,
            });
          }
        }, 50);
      }

      stop() {
        if (this.onstop) this.onstop();
      }
    };
  });
}

async function mockGenerateEndpoint(page: Page, jobId: string) {
  await page.route("**/generate", (route) =>
    route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ job_id: jobId }),
    })
  );
}

async function mockWebSocketSuccess(page: Page) {
  await page.addInitScript(() => {
    const events = [
      { phase: "stt", status: "start", message: "Transcribing audio..." },
      { phase: "stt", status: "complete", data: "a sunset over the ocean" },
      { phase: "enhancing", status: "start", message: "Enhancing prompt..." },
      { phase: "enhancing", status: "complete", data: "golden hour cinematic, 8k" },
      { phase: "generating", status: "start", message: "Generating image..." },
      { phase: "generating", status: "complete", output_url: "/outputs/test.png" },
      {
        phase: "done",
        status: "complete",
        output_url: "/outputs/test.png",
        transcript: "a sunset over the ocean",
        enhanced_prompt: "golden hour cinematic, 8k",
      },
    ];

    (window as any).WebSocket = class MockWebSocket {
      onmessage: ((e: any) => void) | null = null;
      onerror: (() => void) | null = null;
      close() {}

      constructor(_url: string) {
        events.forEach((event, i) => {
          setTimeout(() => {
            if (this.onmessage) {
              this.onmessage({ data: JSON.stringify(event) });
            }
          }, i * 80 + 100);
        });
      }
    };
  });
}

async function mockWebSocketError(page: Page, message: string) {
  await page.addInitScript((msg: string) => {
    (window as any).WebSocket = class MockWebSocket {
      onmessage: ((e: any) => void) | null = null;
      onerror: (() => void) | null = null;
      close() {}

      constructor(_url: string) {
        setTimeout(() => {
          if (this.onmessage) {
            this.onmessage({
              data: JSON.stringify({ phase: "error", status: "error", message: msg }),
            });
          }
        }, 150);
      }
    };
  }, message);
}

// ── Tests ──────────────────────────────────────────────────────────────────

test.describe("Voice to Visual", () => {
  test("page loads with mic button visible and enabled", async ({ page }) => {
    await page.goto("/");
    // The mic button is the large circular button (not Image/Video toggle buttons)
    const micBtn = page.locator("button[class*='rounded-full'][class*='w-24']");
    await expect(micBtn).toBeVisible();
    await expect(micBtn).toBeEnabled();
  });

  test("image/video mode toggle works", async ({ page }) => {
    await page.goto("/");
    const videoBtn = page.getByRole("button", { name: "Video" });
    await videoBtn.click();
    await expect(videoBtn).toHaveClass(/bg-indigo-500/);

    const imageBtn = page.getByRole("button", { name: "Image" });
    await imageBtn.click();
    await expect(imageBtn).toHaveClass(/bg-indigo-500/);
  });

  test("pipeline progress shows phases during processing", async ({ page }) => {
    await mockBrowserAPIs(page);
    await mockGenerateEndpoint(page, "test123");
    await mockWebSocketSuccess(page);

    await page.goto("/");

    const micBtn = page.locator("button[class*='rounded-full'][class*='w-24']");
    await micBtn.click();
    await page.waitForTimeout(200);
    await micBtn.click();

    await expect(page.getByText("Transcribing")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Enhancing")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Generating")).toBeVisible({ timeout: 5000 });
  });

  test("result displays after done event", async ({ page }) => {
    await mockBrowserAPIs(page);
    await mockGenerateEndpoint(page, "done456");
    await mockWebSocketSuccess(page);

    await page.route("**/outputs/test.png", (route) =>
      route.fulfill({
        status: 200,
        contentType: "image/png",
        body: Buffer.alloc(100),
      })
    );

    await page.goto("/");

    const micBtn = page.locator("button[class*='rounded-full'][class*='w-24']");
    await micBtn.click();
    await page.waitForTimeout(200);
    await micBtn.click();

    await expect(page.getByText("Original Idea")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("AI Enhanced")).toBeVisible({ timeout: 5000 });
  });

  test("error state renders when backend sends error phase", async ({ page }) => {
    await mockBrowserAPIs(page);
    await mockGenerateEndpoint(page, "err789");
    await mockWebSocketError(page, "STT failed: unsupported audio format");

    await page.goto("/");

    const micBtn = page.locator("button[class*='rounded-full'][class*='w-24']");
    await micBtn.click();
    await page.waitForTimeout(200);
    await micBtn.click();

    await expect(page.getByText("STT failed: unsupported audio format")).toBeVisible({ timeout: 5000 });
  });
});
