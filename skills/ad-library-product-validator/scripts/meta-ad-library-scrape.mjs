#!/usr/bin/env node
import { writeFile } from "node:fs/promises";
import puppeteer from "puppeteer";

const args = parseArgs(process.argv.slice(2));
const keyword = args.keyword;
if (!keyword) {
  console.error("Error: --keyword is required (the product keyword to search in Meta Ad Library).");
  process.exit(1);
}
const country = args.country ?? "US";
const maxAds = Number(args.maxAds ?? 20);
const scrolls = Number(args.scrolls ?? 12);
const waitMs = Number(args.waitMs ?? 1500);
const observedAt = args.observedAt ?? new Date().toISOString().slice(0, 10);
const outPath = args.out;
const screenshotPath = args.screenshot;
const chromePath = args.chromePath ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const url = buildUrl({ keyword, country });
const browser = await puppeteer.launch({
  headless: true,
  executablePath: chromePath,
  args: [
    "--no-sandbox",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled"
  ]
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1000 });
  await page.setUserAgent(
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
  );

  await page.goto(url, { waitUntil: "networkidle2", timeout: 45000 }).catch(() => {});
  await page.waitForFunction(
    () => /Library ID:\s*\d+/.test(document.body?.innerText ?? ""),
    { timeout: 30000 }
  );
  const textSnapshots = await loadMoreAds(page, { maxAds, scrolls, waitMs });

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: false });
  }

  const bodyText = await page.evaluate(() => document.body.innerText);
  const mergedText = [...textSnapshots, bodyText].join("\n");
  const result = {
    keyword,
    country,
    adType: "All ads",
    activeStatus: "Active ads",
    observedAt,
    sourceUrl: page.url(),
    reportedResultCount: parseResultCount(mergedText),
    ads: uniqueAds(parseAds(mergedText, maxAds)).slice(0, maxAds)
  };

  const json = `${JSON.stringify(result, null, 2)}\n`;
  if (outPath) {
    await writeFile(outPath, json, "utf8");
  }
  process.stdout.write(json);
} finally {
  await browser.close();
}

function parseArgs(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === "--keyword") parsed.keyword = argv[++i];
    if (item === "--country") parsed.country = argv[++i];
    if (item === "--max-ads") parsed.maxAds = argv[++i];
    if (item === "--scrolls") parsed.scrolls = argv[++i];
    if (item === "--wait-ms") parsed.waitMs = argv[++i];
    if (item === "--observed-at") parsed.observedAt = argv[++i];
    if (item === "--out") parsed.out = argv[++i];
    if (item === "--screenshot") parsed.screenshot = argv[++i];
    if (item === "--chrome-path") parsed.chromePath = argv[++i];
  }
  return parsed;
}

async function loadMoreAds(page, { maxAds, scrolls, waitMs }) {
  let previousScrollY = -1;
  let stuckRounds = 0;
  const snapshots = [];

  for (let i = 0; i < scrolls; i += 1) {
    const state = await page.evaluate(() => {
      const text = document.body?.innerText ?? "";
      return {
        text,
        count: (text.match(/Library ID:\s*\d+/g) ?? []).length,
        scrollY: window.scrollY,
        scrollHeight: document.body.scrollHeight,
        viewportHeight: window.innerHeight
      };
    });
    snapshots.push(state.text);

    const mergedCount = uniqueAds(parseAds(snapshots.join("\n"), maxAds)).length;
    if (mergedCount >= maxAds) break;
    if (state.scrollY === previousScrollY) stuckRounds += 1;
    if (stuckRounds >= 6 && state.scrollY + state.viewportHeight >= state.scrollHeight - 20) break;
    previousScrollY = state.scrollY;

    await page.evaluate(() => {
      const step = Math.max(window.innerHeight * 1.5, 1200);
      window.scrollBy(0, step);
    });
    await new Promise((resolve) => setTimeout(resolve, waitMs));
  }
  return snapshots;
}

function buildUrl({ keyword, country }) {
  const params = new URLSearchParams({
    active_status: "active",
    ad_type: "all",
    country,
    is_targeted_country: "false",
    media_type: "all",
    q: keyword,
    search_type: "keyword_unordered"
  });
  params.append("sort_data[mode]", "total_impressions");
  params.append("sort_data[direction]", "desc");
  return `https://www.facebook.com/ads/library/?${params.toString()}`;
}

function parseResultCount(text) {
  const match = text.match(/~?([\d,]+)\s+results/i);
  return match ? Number(match[1].replace(/,/g, "")) : null;
}

function parseAds(text, maxAds) {
  const normalized = text
    .replace(/\u200b/g, "")
    .replace(/\r/g, "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const ads = [];
  for (let i = 0; i < normalized.length; i += 1) {
    const idMatch = normalized[i].match(/^Library ID:\s*(\d+)/);
    if (!idMatch) continue;

    const nextIdIndex = findNextLibraryId(normalized, i + 1);
    const block = normalized.slice(i, nextIdIndex === -1 ? normalized.length : nextIdIndex);
    const startedLine = block.find((line) => /^Started running on /i.test(line));
    const pageName = findPageName(block);
    const bodyText = findBodyText(block, pageName);
    const platforms = inferPlatforms(block);
    const landingDomain = findLandingDomain(block);

    ads.push({
      libraryId: idMatch[1],
      pageName,
      startedRunningOn: startedLine ? normalizeDate(startedLine.replace(/^Started running on /i, "")) : null,
      platforms,
      landingDomain,
      bodyText,
      snapshotUrl: null
    });

    if (ads.length >= maxAds) break;
  }
  return ads;
}

function findNextLibraryId(lines, start) {
  for (let i = start; i < lines.length; i += 1) {
    if (/^Library ID:\s*\d+/.test(lines[i])) return i;
  }
  return -1;
}

function findPageName(block) {
  const sponsoredIndex = block.findIndex((line) => line === "Sponsored");
  if (sponsoredIndex > 0) return block[sponsoredIndex - 1];
  return null;
}

function findBodyText(block, pageName) {
  const sponsoredIndex = block.findIndex((line) => line === "Sponsored");
  if (sponsoredIndex === -1) return "";

  const stopPatterns = [
    /^\d+:\d+\s*\/\s*\d+:\d+$/,
    /^[A-Z0-9.-]+\.[A-Z]{2,}/,
    /^Shop now$/i,
    /^Learn more$/i,
    /^Send message$/i
  ];
  const parts = [];
  for (const line of block.slice(sponsoredIndex + 1)) {
    if (line === pageName) continue;
    if (stopPatterns.some((pattern) => pattern.test(line))) break;
    if (/^This ad has multiple versions$/i.test(line)) continue;
    if (/^\d+ ads use this creative and text$/i.test(line)) continue;
    parts.push(line);
  }
  return parts.join("\n").trim();
}

function findLandingDomain(block) {
  const domainLine = block.find((line) => /^[A-Z0-9.-]+\.[A-Z]{2,}/.test(line));
  return domainLine ? domainLine.toLowerCase() : null;
}

function inferPlatforms(block) {
  const text = block.join(" ").toLowerCase();
  const platforms = [];
  if (text.includes("facebook")) platforms.push("Facebook");
  if (text.includes("instagram")) platforms.push("Instagram");
  if (text.includes("messenger")) platforms.push("Messenger");
  if (text.includes("audience network")) platforms.push("Audience Network");
  return platforms;
}

function normalizeDate(value) {
  const date = new Date(`${value} UTC`);
  if (!Number.isFinite(date.valueOf())) return value;
  return date.toISOString().slice(0, 10);
}

function uniqueAds(ads) {
  const seen = new Set();
  const unique = [];
  for (const ad of ads) {
    if (seen.has(ad.libraryId)) continue;
    seen.add(ad.libraryId);
    unique.push(ad);
  }
  return unique;
}
