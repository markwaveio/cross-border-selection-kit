#!/usr/bin/env node
import { writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import puppeteer from "puppeteer";
import iconvLite from "iconv-lite";

const args = parseArgs(process.argv.slice(2));
const keyword = args.keyword;
const observedAt = args.observedAt ?? new Date().toISOString().slice(0, 10);
const outPath = args.out;
const qrScreenshotPath = args.qrScreenshot;
const userDataDir = args.userDataDir ?? "generated/1688-supplier-validator/.browser-profile";
const chromePath = args.chromePath ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const headless = args.headless !== "false";

if (!keyword) {
  console.error("Missing required --keyword <Chinese keyword>");
  process.exit(1);
}

await mkdir(userDataDir, { recursive: true });

const url = buildSearchUrl(keyword);
const browser = await puppeteer.launch({
  headless,
  executablePath: chromePath,
  userDataDir,
  args: ["--disable-blink-features=AutomationControlled", "--window-size=1440,1000"]
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1000 });
  await page.setUserAgent(
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
  );

  await page.goto(url, { waitUntil: "networkidle2", timeout: 45000 }).catch(() => {});
  await new Promise((resolve) => setTimeout(resolve, 1500));

  const loginCheck = await detectLoginWall(page);
  if (loginCheck.needsLogin) {
    if (qrScreenshotPath) {
      await mkdir(path.dirname(qrScreenshotPath), { recursive: true });
      await page.screenshot({ path: qrScreenshotPath, fullPage: false });
    }
    const result = {
      status: "login_required",
      message: "1688 未检测到有效登录态，已截图二维码，请扫码登录后重新运行本脚本。",
      qrScreenshot: qrScreenshotPath ?? null,
      observedAt
    };
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    process.exitCode = 2;
  } else {
    const data = await extractSearchResults(page, { keyword, url: page.url(), observedAt });
    const json = `${JSON.stringify(data, null, 2)}\n`;
    if (outPath) {
      await mkdir(path.dirname(outPath), { recursive: true });
      await writeFile(outPath, json, "utf8");
    }
    process.stdout.write(json);
  }
} finally {
  await browser.close();
}

function parseArgs(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === "--keyword") parsed.keyword = argv[++i];
    if (item === "--observed-at") parsed.observedAt = argv[++i];
    if (item === "--out") parsed.out = argv[++i];
    if (item === "--qr-screenshot") parsed.qrScreenshot = argv[++i];
    if (item === "--user-data-dir") parsed.userDataDir = argv[++i];
    if (item === "--chrome-path") parsed.chromePath = argv[++i];
    if (item === "--headless") parsed.headless = argv[++i];
  }
  return parsed;
}

/**
 * 1688 offer_search.htm 的 keywords 参数后端按 GBK 字符集解析。
 * 标准 UTF-8 percent-encoding（encodeURIComponent）会被误解析成 GBK 字节，
 * 导致页面标题/搜索框乱码、搜索结果为空或不相关。
 * 必须先取关键词的 GBK 字节，再对这些字节做 percent-encode。
 * Node.js 核心 Buffer 不内置 gbk 编码，用 iconv-lite 转换。
 */
function gbkPercentEncode(text) {
  const bytes = iconvLite.encode(text, "gbk");
  return Array.from(bytes)
    .map((byte) => `%${byte.toString(16).toUpperCase().padStart(2, "0")}`)
    .join("");
}

function buildSearchUrl(keyword) {
  const encoded = gbkPercentEncode(keyword);
  return `https://s.1688.com/selloffer/offer_search.htm?keywords=${encoded}`;
}

async function detectLoginWall(page) {
  const signals = await page.evaluate(() => {
    const text = document.body?.innerText ?? "";
    const hasQrImage = Boolean(document.querySelector("img[src*='qrcode'], canvas, .login-qrcode, [class*=qrcode]"));
    const hasLoginKeyword = /扫码登录|手机淘宝.*扫码|账号登录|密码登录/.test(text);
    const title = document.title ?? "";
    return { hasQrImage, hasLoginKeyword, title, urlIncludesLogin: location.href.includes("login.1688.com") };
  });
  return {
    needsLogin: signals.urlIncludesLogin || signals.hasLoginKeyword || (signals.hasQrImage && /登录/.test(signals.title))
  };
}

async function extractSearchResults(page, { keyword, url, observedAt }) {
  const extracted = await page.evaluate(() => {
    const pageBodyText = document.body.innerText;
    const totalPagesMatch = pageBodyText.match(/共\s*(\d+)\s*页/);
    const offerLinks = Array.from(document.querySelectorAll("a[href*='detail.m.1688.com'], a[href*='dj.1688.com']"));

    const offers = [];
    const seen = new Set();
    for (const link of offerLinks) {
      const block = link.innerText?.trim();
      if (!block || seen.has(block)) continue;
      seen.add(block);

      const priceMatch = block.match(/¥\s*([\d.]+)/);
      const moqMatch = block.match(/(\d+)\s*件起购/);
      const salesMatch = block.match(/(全网)?([\d.万+]+)\s*件/);
      const companyLink = link.querySelector("a[href*='.1688.com/']") ?? Array.from(link.querySelectorAll("a")).find((a) => /1688\.com\/?$/.test(a.href) || a.href.includes(".1688.com"));

      offers.push({
        rawText: block.slice(0, 200),
        priceCny: priceMatch ? Number(priceMatch[1]) : null,
        moqUnits: moqMatch ? Number(moqMatch[1]) : null,
        salesSignal: salesMatch ? salesMatch[0] : null,
        companyName: companyLink ? companyLink.textContent.trim() : null,
        companyUrl: companyLink ? companyLink.href : null
      });
    }

    return {
      title: document.title,
      searchBoxValue: document.querySelector("input[type=text]")?.value ?? null,
      totalResultPages: totalPagesMatch ? Number(totalPagesMatch[1]) : null,
      offers: offers.slice(0, 40)
    };
  });

  const distinctSuppliers = new Set(extracted.offers.map((o) => o.companyName).filter(Boolean));
  const prices = extracted.offers.map((o) => o.priceCny).filter((p) => typeof p === "number");

  return {
    status: "ok",
    keyword,
    sourceUrl: url,
    observedAt,
    pageTitle: extracted.title,
    searchBoxValue: extracted.searchBoxValue,
    totalResultPages: extracted.totalResultPages,
    priceRangeCny: prices.length ? { min: Math.min(...prices), max: Math.max(...prices) } : null,
    distinctSupplierCountSampled: distinctSuppliers.size,
    suppliersSampled: Array.from(distinctSuppliers),
    offersSampled: extracted.offers
  };
}
