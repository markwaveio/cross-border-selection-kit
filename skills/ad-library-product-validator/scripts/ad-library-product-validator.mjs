#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";

// Generic, keyword-agnostic phrasing keyed by the hook labels classifyHooks emits.
// These describe the *angle pattern* (not any specific product), so they read correctly
// whatever keyword the scrape was run on. Declared before any code runs (no TDZ).
const HOOK_ANGLE = {
  "travel": "Travel/portability scenario: lean into the on-the-go use case the winning ads already validate.",
  "mom-family": "Family/parent angle: frame the product around reducing daily household friction.",
  "amazon-affiliate": "Proof-led roundup angle: 'as seen on Amazon best-seller lists' social proof.",
  "organization": "Tidy/declutter angle: before-after organization transformation.",
  "demo": "Demonstration-first creative: show the product working in a quick before/after clip.",
  "space-saving": "Space-saving angle: quantify how much room/effort it saves.",
  "discount-promo": "Time-boxed offer: pair a sharp creative with a limited discount to drive urgency.",
  "social-proof": "Social-proof angle: viral/restock/sold-out framing with real review counts.",
  "bundle": "Bundle angle: pair with a complementary item to lift average order value.",
  "guarantee-warranty": "Risk-reversal angle: lead with guarantee/warranty to lower purchase hesitation.",
  "durability-protection": "Protection angle: emphasize durability/spill/odor resistance.",
  "unclear": "No dominant proven angle yet — test a clear demonstration creative to find one."
};

const HOOK_RISK = {
  "amazon-affiliate": "Amazon/affiliate competition: shoppers comparison-shop quickly, compressing margin.",
  "discount-promo": "Discount-led saturation: if rivals compete mainly on promos, price erosion is likely.",
  "space-saving": "Commodity pressure: many advertisers sell the same space-saving benefit, so demos copy easily.",
  "social-proof": "Social-proof arms race: review/viral claims are easy to imitate and hard to defend.",
  "bundle": "Bundle parity: competitors can replicate the same bundle, eroding the differentiator.",
  "travel": "Seasonal/occasion dependence: travel-framed demand can be uneven across the year.",
  "organization": "Demo sameness: organization before/after clips are validated but trivial to copy.",
  "unclear": "No proven creative angle emerged from the sample — positioning risk is higher than usual."
};

const args = parseArgs(process.argv.slice(2));
const inputPath = args.input ?? "generated/ad-library-product-validator/sample.json";
const outPath = args.out;

const raw = await readFile(inputPath, "utf8");
const data = JSON.parse(raw);
const observedAt = new Date(`${data.observedAt}T00:00:00Z`);
const ads = (data.ads ?? []).map((ad) => {
  const start = new Date(`${ad.startedRunningOn}T00:00:00Z`);
  const activeDays = Number.isFinite(start.valueOf())
    ? Math.max(0, Math.floor((observedAt - start) / 86400000))
    : null;
  return {
    ...ad,
    activeDays,
    hookTypes: classifyHooks(ad.bodyText ?? "", ad.pageName ?? "")
  };
});

const report = buildReport({ ...data, ads });

if (outPath) {
  await writeFile(outPath, report, "utf8");
}

process.stdout.write(report);

function parseArgs(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === "--input") parsed.input = argv[++i];
    if (item === "--out") parsed.out = argv[++i];
  }
  return parsed;
}

function classifyHooks(text, pageName) {
  const haystack = `${text} ${pageName}`.toLowerCase();
  const hooks = [];
  const rules = [
    ["travel", /\btravel|traveler|trip|mexico|suitcase|packing|luggage|journey\b/],
    ["mom-family", /\bmom|toddler|kids|family\b/],
    ["amazon-affiliate", /\bamazon|best seller|deals?\b/],
    ["organization", /\borganizer|organization|organised|organized|packed up|chaos|unpack\b/],
    ["demo", /\bdemo|showed|before|after\b/],
    ["space-saving", /\bcompression|compress|space|save|fit up to|compact\b/],
    ["discount-promo", /\boff|sale|discount|coupon|while supplies last|before we run out\b/],
    ["social-proof", /\bviral|sold|sells|customers|reviews|restock\b/],
    ["bundle", /\bbundle|buy 1|get all|free gift|set of\b/],
    ["guarantee-warranty", /\bguarantee|warranty|money-back|satisfaction\b/],
    ["durability-protection", /\bwaterproof|durable|protect|spills|odor|odors\b/]
  ];

  for (const [label, pattern] of rules) {
    if (pattern.test(haystack)) hooks.push(label);
  }

  return hooks.length ? hooks : ["unclear"];
}

function buildReport(data) {
  const ads = data.ads ?? [];
  const uniqueAdvertisers = new Set(ads.map((ad) => ad.pageName).filter(Boolean));
  const long30 = ads.filter((ad) => ad.activeDays >= 30).length;
  const long90 = ads.filter((ad) => ad.activeDays >= 90).length;
  const long180 = ads.filter((ad) => ad.activeDays >= 180).length;
  const hasText = ads.filter((ad) => (ad.bodyText ?? "").trim()).length;
  const hookCounts = countFlat(ads.flatMap((ad) => ad.hookTypes ?? []));
  const advertiserCounts = countFlat(ads.map((ad) => ad.pageName ?? "Unknown"));
  const domainCounts = countFlat(ads.map((ad) => ad.landingDomain ?? "unknown"));
  const advertiserTypeCounts = countFlat(ads.map(inferAdvertiserType));
  const ageBuckets = bucketAges(ads);
  const activeAdScore = scoreActiveAds(data.reportedResultCount);
  const longRunningScore = scoreRatio(ads.length ? long90 / ads.length : 0);
  const diversityScore = scoreRatio(ads.length ? uniqueAdvertisers.size / ads.length : 0);
  const textCoverageScore = scoreRatio(ads.length ? hasText / ads.length : 0);
  const sampleConfidence = ads.length >= 30 ? "high" : ads.length >= 10 ? "medium" : "low";

  const marketScore = activeAdScore + longRunningScore + diversityScore + textCoverageScore;
  const recommendation = marketScore >= 10
    ? "Worth a deeper scrape and creative testing."
    : marketScore >= 7
      ? "Promising, but collect a larger sample before deciding."
      : "Insufficient signal from this sample; expand the scrape or refine keywords.";

  const lines = [];
  lines.push(`# Ad Library Product Validation: ${data.keyword}`);
  lines.push("");
  lines.push(`- Country: ${data.country}`);
  lines.push(`- Filter: ${data.adType}, ${data.activeStatus}`);
  lines.push(`- Observed at: ${data.observedAt}`);
  lines.push(`- Reported active result count: ${formatNumber(data.reportedResultCount)}`);
  lines.push(`- Sampled ads: ${ads.length}`);
  lines.push(`- Sample confidence: ${sampleConfidence}`);
  if (data.sourceUrl) lines.push(`- Source URL: ${data.sourceUrl}`);
  lines.push("");
  lines.push("## Final Read");
  lines.push("");
  lines.push(finalRead({ keyword: data.keyword, ads, long30, long90, uniqueAdvertisers, hookCounts, advertiserTypeCounts, domainCounts }));
  lines.push("");
  lines.push("## Scorecard");
  lines.push("");
  lines.push(`- Unique advertisers in sample: ${uniqueAdvertisers.size}`);
  lines.push(`- Ads with readable copy: ${hasText}/${ads.length}`);
  lines.push(`- Ads active for 30+ days: ${long30}/${ads.length}`);
  lines.push(`- Ads active for 90+ days: ${long90}/${ads.length}`);
  lines.push(`- Ads active for 180+ days: ${long180}/${ads.length}`);
  lines.push(`- Active-ad volume score: ${activeAdScore}/5`);
  lines.push(`- Long-running score: ${longRunningScore}/5`);
  lines.push(`- Advertiser diversity score: ${diversityScore}/5`);
  lines.push(`- Text coverage score: ${textCoverageScore}/5`);
  lines.push(`- Total quick score: ${marketScore}/20`);
  lines.push(`- Recommendation: ${recommendation}`);
  lines.push("");
  lines.push("## Age Distribution");
  lines.push("");
  for (const [bucket, count] of Object.entries(ageBuckets)) {
    lines.push(`- ${bucket}: ${count}`);
  }
  lines.push("");
  lines.push("## Top Hooks");
  lines.push("");
  for (const [hook, count] of sortedEntries(hookCounts)) {
    lines.push(`- ${hook}: ${count}`);
  }
  lines.push("");
  lines.push("## Advertiser Types");
  lines.push("");
  for (const [type, count] of sortedEntries(advertiserTypeCounts)) {
    lines.push(`- ${type}: ${count}`);
  }
  lines.push("");
  lines.push("## Landing Domains");
  lines.push("");
  for (const [domain, count] of sortedEntries(domainCounts).slice(0, 20)) {
    lines.push(`- ${domain}: ${count}`);
  }
  lines.push("");
  lines.push("## Advertisers");
  lines.push("");
  for (const [advertiser, count] of sortedEntries(advertiserCounts)) {
    lines.push(`- ${advertiser}: ${count}`);
  }
  lines.push("");
  lines.push("## Sample Ads");
  lines.push("");
  lines.push("| Library ID | Advertiser | Domain | Started | Active days | Hooks |");
  lines.push("|---|---|---|---:|---:|---|");
  for (const ad of ads) {
    lines.push(`| ${ad.libraryId} | ${ad.pageName} | ${ad.landingDomain ?? ""} | ${ad.startedRunningOn} | ${ad.activeDays ?? "n/a"} | ${(ad.hookTypes ?? []).join(", ")} |`);
  }
  lines.push("");
  lines.push("## Suggested Test Angles");
  lines.push("");
  for (const angle of suggestTestAngles({ keyword: data.keyword, hookCounts, long90, adsLength: ads.length })) {
    lines.push(`- ${angle}`);
  }
  lines.push("");
  lines.push("## Main Risks");
  lines.push("");
  for (const risk of mainRisks({ keyword: data.keyword, hookCounts, advertiserTypeCounts, uniqueAdvertisers, adsLength: ads.length, long90 })) {
    lines.push(`- ${risk}`);
  }
  lines.push("");

  return lines.join("\n");
}

function finalRead({ keyword, ads, long30, long90, uniqueAdvertisers, hookCounts, advertiserTypeCounts, domainCounts }) {
  if (!ads.length) return "No ads were parsed, so no market read is available.";

  const topHook = sortedEntries(hookCounts)[0]?.[0] ?? "unclear";
  const topType = sortedEntries(advertiserTypeCounts)[0]?.[0] ?? "unknown";
  const topDomain = sortedEntries(domainCounts).filter(([domain]) => domain !== "unknown")[0]?.[0] ?? "unknown";
  const label = keyword ? `"${keyword}"` : "this keyword";
  return [
    `${capitalize(label)} shows real demand: ${long30}/${ads.length} sampled ads have been active for 30+ days, and ${long90}/${ads.length} have lasted 90+ days.`,
    `Competition is broad rather than concentrated: ${uniqueAdvertisers.size} unique advertisers appeared in ${ads.length} sampled ads.`,
    `The dominant creative angle is ${topHook}, with ${topType} as the most common advertiser type and ${topDomain} as the strongest visible landing domain.`,
    `Decision: keep researching and prepare a small creative test, but only enter with a sharper angle than the dominant ${topHook} approach already saturating ${label}.`
  ].join(" ");
}

function suggestTestAngles({ keyword, hookCounts, long90, adsLength }) {
  const label = keyword ? `"${keyword}"` : "this product";
  const angles = [];
  const ranked = sortedEntries(hookCounts).map(([hook]) => hook).filter((h) => h !== "unclear");
  for (const hook of ranked.slice(0, 3)) {
    if (HOOK_ANGLE[hook]) angles.push(HOOK_ANGLE[hook]);
  }
  if (!angles.length) angles.push(HOOK_ANGLE.unclear);
  // Longevity-aware closing suggestion, derived from the data not a fixed product.
  if (adsLength && long90 / adsLength >= 0.25) {
    angles.push(`Differentiate beyond the proven angles above: the long-running ads on ${label} show the easy angles are already saturated.`);
  } else {
    angles.push(`Few long-running ads on ${label} yet — there may be room to define the category-winning angle first.`);
  }
  return angles;
}

function mainRisks({ keyword, hookCounts, advertiserTypeCounts, uniqueAdvertisers, adsLength, long90 }) {
  const label = keyword ? `"${keyword}"` : "this product";
  const risks = [];
  const ranked = sortedEntries(hookCounts).map(([hook]) => hook).filter((h) => h !== "unclear");
  for (const hook of ranked.slice(0, 3)) {
    if (HOOK_RISK[hook] && !risks.includes(HOOK_RISK[hook])) risks.push(HOOK_RISK[hook]);
  }
  const topType = sortedEntries(advertiserTypeCounts)[0]?.[0];
  if (topType === "amazon-affiliate/deal" && !risks.some((r) => r.startsWith("Amazon/affiliate"))) {
    risks.push("Affiliate/deal accounts dominate the sample, so headline ad counts overstate genuine brand demand — confirm with deduped advertisers.");
  }
  if (adsLength && uniqueAdvertisers.size / adsLength >= 0.75) {
    risks.push(`High advertiser fragmentation on ${label}: broad demand but crowded, so paid CPMs may be bid up.`);
  }
  if (adsLength && long90 / adsLength < 0.1) {
    risks.push(`Very few ads on ${label} survive 90+ days — winning creative may be hard to sustain, or demand is shallow.`);
  }
  if (!risks.length) risks.push(`Differentiation must come from bundle, audience, guarantee, or a sharper use case rather than the generic ${label} pitch.`);
  return risks;
}

function capitalize(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : str;
}

function inferAdvertiserType(ad) {
  const haystack = `${ad.pageName ?? ""} ${ad.landingDomain ?? ""} ${ad.bodyText ?? ""}`.toLowerCase();
  if (/\bamazon|deals?\b/.test(haystack)) return "amazon-affiliate/deal";
  if (/\bsamsonite|wool & oak|nobl|simplify living|travel with frank|guru\b/.test(haystack)) return "brand/dtc";
  if (/\b[a-z]+\.[a-z]+/.test(ad.pageName ?? "")) return "creator/influencer";
  return "other";
}

function bucketAges(ads) {
  return {
    "0-14 days": ads.filter((ad) => ad.activeDays >= 0 && ad.activeDays <= 14).length,
    "15-30 days": ads.filter((ad) => ad.activeDays >= 15 && ad.activeDays <= 30).length,
    "31-90 days": ads.filter((ad) => ad.activeDays >= 31 && ad.activeDays <= 90).length,
    "91-180 days": ads.filter((ad) => ad.activeDays >= 91 && ad.activeDays <= 180).length,
    "181+ days": ads.filter((ad) => ad.activeDays >= 181).length,
    unknown: ads.filter((ad) => ad.activeDays == null).length
  };
}

function countFlat(items) {
  return items.reduce((acc, item) => {
    acc[item] = (acc[item] ?? 0) + 1;
    return acc;
  }, {});
}

function sortedEntries(counts) {
  return Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

function scoreActiveAds(count) {
  if (count >= 3000) return 2;
  if (count >= 800) return 4;
  if (count >= 200) return 5;
  if (count >= 50) return 3;
  return 1;
}

function scoreRatio(ratio) {
  if (ratio >= 0.75) return 5;
  if (ratio >= 0.5) return 4;
  if (ratio >= 0.25) return 3;
  if (ratio > 0) return 2;
  return 1;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}
