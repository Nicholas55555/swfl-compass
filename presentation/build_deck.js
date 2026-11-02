// Builds presentation/SWFL-Compass.pptx from the demo screenshots + video in docs/demo.
//   cd presentation && npm install && npm run build
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const md = require("react-icons/md");

const DEMO = path.join(__dirname, "..", "docs", "demo");
const OUT = path.join(__dirname, "SWFL-Compass.pptx");
const img = (n) => path.join(DEMO, n);

// Gulf-coast palette: deep mangrove, gulf blue, FGCU green, sunset accent
const P = {
  night: "0B2E2B",
  mangrove: "0F4C45",
  green: "00885A",
  gulf: "0B5EA8",
  sunset: "F08A24",
  sand: "F3F7F5",
  ink: "12302C",
  muted: "5D7570",
  white: "FFFFFF",
  line: "D5E3DF",
};
const HEAD = "Calibri";
const BODY = "Calibri";

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

const shadow = () => ({ type: "outer", color: "000000", blur: 8, offset: 3, angle: 90, opacity: 0.22 });

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.title = "SWFL Compass";
  pres.author = "Nicholas Taylor";
  pres.subject = "FGCU AI Day H{AI}ckathon - AI for SWFL";
  pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: P.white },
    objects: [
      { text: { text: "SWFL Compass  ·  FGCU AI Day 2026", options: { x: 0.6, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: P.muted, fontFace: BODY } } },
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontSize: 34, bold: true, color: P.ink, fontFace: HEAD, valign: "middle", margin: 0 }, text: "" } },
    ],
    slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: P.muted, align: "right" },
  });
  pres.defineSlideMaster({ title: "DARK", background: { color: P.night }, objects: [] });

  const ic = {
    home: await icon(fa.FaHome, P.white),
    grad: await icon(fa.FaGraduationCap, P.white),
    work: await icon(fa.FaBriefcase, P.white),
    beach: await icon(fa.FaUmbrellaBeach, P.white),
    search: await icon(fa.FaSearch, P.white),
    map: await icon(fa.FaMapMarkedAlt, P.white),
    book: await icon(fa.FaBookOpen, P.white),
    chat: await icon(fa.FaRegCommentDots, P.white),
    doc: await icon(fa.FaFileAlt, P.white),
    shield: await icon(fa.FaShieldAlt, P.white),
    bolt: await icon(fa.FaBolt, P.white),
    wifi: await icon(fa.FaWifi, P.white),
    globe: await icon(fa.FaGlobeAmericas, P.white),
    storm: await icon(md.MdThunderstorm, P.white),
    sms: await icon(fa.FaSms, P.white),
    city: await icon(fa.FaCity, P.white),
    compass: await icon(fa.FaRegCompass, P.sunset, 512),
    github: await icon(fa.FaGithub, P.white),
  };

  const iconCircle = (s, data, x, y, d, fill) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
    const pad = d * 0.24;
    s.addImage({ data, x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
  };
  const screenshot = (s, file, x, y, w, alt) => {
    const h = w / 1.6; // 1280x800 captures
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.06, y: y - 0.06, w: w + 0.12, h: h + 0.12, rectRadius: 0.12, fill: { color: P.white }, line: { color: P.line, width: 1 }, shadow: shadow() });
    s.addImage({ path: img(file), x, y, w, h, altText: alt });
    return h;
  };

  // 1 ─ Title
  {
    const s = pres.addSlide({ masterName: "DARK" });
    s.addImage({ data: ic.compass, x: 0.7, y: 1.2, w: 0.9, h: 0.9 });
    s.addText("SWFL Compass", { x: 0.7, y: 2.25, w: 5.6, h: 1.0, fontSize: 48, bold: true, color: P.white, fontFace: HEAD, margin: 0, isTextBox: true });
    s.addText("An agentic AI guide for everyone who lives, studies, works in, or visits Southwest Florida", { x: 0.7, y: 3.3, w: 5.4, h: 1.2, fontSize: 20, color: "CFE6DF", fontFace: BODY, margin: 0, isTextBox: true });
    s.addText([
      { text: "FGCU AI Day H{AI}ckathon  ·  Challenge: AI for SWFL", options: { breakLine: true } },
      { text: "November 2, 2026" },
    ], { x: 0.7, y: 5.4, w: 5.6, h: 0.8, fontSize: 14, color: "9FC3BA", fontFace: BODY, margin: 0, isTextBox: true });
    screenshot(s, "01-welcome.png", 6.75, 1.55, 6.0, "SWFL Compass welcome screen with personas and starter questions");
    s.addNotes("Hi, we built SWFL Compass: one place to ask anything about life in Southwest Florida and get a researched, sourced answer, real places on a map, and a plan you can take with you.");
  }

  // 2 ─ Problem
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Answers about SWFL are scattered across dozens of sites", { placeholder: "title" });
    const who = [
      [ic.home, "Residents", "Evacuation zones, red tide, flooding, utility help"],
      [ic.grad, "Students", "Getting around without a car, housing, campus resources"],
      [ic.work, "Workers", "Job training, hiring industries, childcare support"],
      [ic.beach, "Visitors", "Beaches, wildlife, food, staying safe in storm season"],
    ];
    who.forEach(([data, head, body], i) => {
      const x = 0.6 + (i % 2) * 3.95, y = 1.65 + Math.floor(i / 2) * 2.45;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.7, h: 2.15, rectRadius: 0.15, fill: { color: P.sand }, line: { color: P.sand } });
      iconCircle(s, data, x + 0.3, y + 0.3, 0.75, i % 2 ? P.gulf : P.green);
      s.addText(head, { x: x + 0.3, y: y + 1.12, w: 3.2, h: 0.4, fontSize: 18, bold: true, color: P.ink, margin: 0, isTextBox: true });
      s.addText(body, { x: x + 0.3, y: y + 1.5, w: 3.2, h: 0.55, fontSize: 14, color: P.muted, margin: 0, isTextBox: true });
    });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.75, y: 1.65, w: 4.0, h: 4.6, rectRadius: 0.15, fill: { color: P.mangrove }, line: { color: P.mangrove } });
    s.addText("Today you have to know where to look", { x: 9.05, y: 1.9, w: 3.4, h: 0.9, fontSize: 20, bold: true, color: P.white, margin: 0, isTextBox: true });
    s.addText([
      { text: "County emergency management", options: { bullet: true, breakLine: true } },
      { text: "NWS + FWC red tide reports", options: { bullet: true, breakLine: true } },
      { text: "LeeTran / CAT transit", options: { bullet: true, breakLine: true } },
      { text: "CareerSource, FGCU, FSW", options: { bullet: true, breakLine: true } },
      { text: "Tourism boards, reviews, maps", options: { bullet: true } },
    ], { x: 9.05, y: 2.85, w: 3.45, h: 2.2, fontSize: 15, color: "DCEFEA", paraSpaceAfter: 6, margin: 0, isTextBox: true });
    s.addText("…and much of it is time-sensitive.", { x: 9.05, y: 5.35, w: 3.45, h: 0.5, fontSize: 15, italic: true, color: P.sunset, margin: 0, isTextBox: true });
    s.addNotes("Four audiences, one region. The information exists, but it's spread over county sites, state agencies, transit, schools and tourism boards, and things like storms and red tide change daily.");
  }

  // 3 ─ Solution
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("One question in, a researched answer out", { placeholder: "title" });
    const rows = [
      [ic.search, P.green, "Researches live", "Searches the web, reads official pages, streams each step"],
      [ic.map, P.gulf, "Shows real places", "Verified Google Maps places, pinned on a map"],
      [ic.book, P.green, "Points to resources", "Only links it actually read, plus one-click summaries"],
      [ic.chat, P.gulf, "Keeps the conversation going", "Suggests follow-up questions tailored to you"],
      [ic.doc, P.sunset, "Makes a plan", "Itineraries and guides to download or print"],
    ];
    rows.forEach(([data, color, head, body], i) => {
      const y = 1.6 + i * 1.0;
      iconCircle(s, data, 0.6, y, 0.7, color);
      s.addText(head, { x: 1.55, y: y - 0.02, w: 4.6, h: 0.38, fontSize: 18, bold: true, color: P.ink, margin: 0, isTextBox: true });
      s.addText(body, { x: 1.55, y: y + 0.36, w: 4.6, h: 0.4, fontSize: 14, color: P.muted, margin: 0, isTextBox: true });
    });
    screenshot(s, "03-answer.png", 6.6, 1.6, 6.15, "A sourced answer about Naples beaches and current red tide status");
    s.addNotes("Ask in plain language. The agent decides what to search, reads the pages, checks places on Google Maps and writes a sourced answer, then hands you resources, follow-up questions and, if you want, a full plan.");
  }

  // 4 ─ Demo video
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Live demo", { placeholder: "title" });
    const w = 8.6, h = w / 1.6;
    const poster = fs.readFileSync(img("03-answer.png")).toString("base64");
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.54, y: 1.39, w: w + 0.12, h: h + 0.12, rectRadius: 0.1, fill: { color: P.night }, line: { color: P.night }, shadow: shadow() });
    s.addMedia({ type: "video", path: img("swfl-compass-demo.mp4"), cover: "image/png;base64," + poster, x: 0.6, y: 1.45, w, h });
    const steps = ["Pick who you are", "Ask a question", "Watch the agent research", "Answer + map + resources", "Summarize a source", "Build a 2-day itinerary"];
    s.addText("In 60 seconds", { x: 9.85, y: 1.45, w: 2.9, h: 0.45, fontSize: 18, bold: true, color: P.ink, margin: 0, isTextBox: true });
    steps.forEach((t, i) => {
      const y = 2.05 + i * 0.68;
      s.addShape(pres.shapes.OVAL, { x: 9.85, y, w: 0.42, h: 0.42, fill: { color: i === 5 ? P.sunset : P.green }, line: { color: i === 5 ? P.sunset : P.green } });
      s.addText(String(i + 1), { x: 9.85, y, w: 0.42, h: 0.42, fontSize: 13, bold: true, color: P.white, align: "center", valign: "middle", margin: 0, isTextBox: true });
      s.addText(t, { x: 10.4, y: y - 0.02, w: 2.4, h: 0.46, fontSize: 14, color: P.ink, valign: "middle", margin: 0, isTextBox: true });
    });
    s.addNotes("Click play. A visitor asks about Naples beaches and red tide. You can see each agent step live, then the sourced answer, map pins from Google Places, resources with a one-click summary of the FWC red tide page, and finally a two-day Naples itinerary built from the form.");
  }

  // 5 ─ Architecture
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("How it works: an agent with four tools", { placeholder: "title" });
    const box = (x, y, w, h, fill, head, sub, headColor = P.white, subColor = "DCEFEA") => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill } });
      s.addText(head, { x: x + 0.2, y: y + 0.15, w: w - 0.4, h: 0.4, fontSize: 16, bold: true, color: headColor, margin: 0, isTextBox: true });
      s.addText(sub, { x: x + 0.2, y: y + 0.55, w: w - 0.4, h: h - 0.7, fontSize: 13, color: subColor, margin: 0, valign: "top", isTextBox: true });
    };
    box(0.6, 2.75, 2.5, 1.7, P.gulf, "React UI", "Personas, live steps, map, documents");
    box(3.85, 2.45, 3.1, 2.3, P.night, "FastAPI agent", "Gemini 3.1 Flash-Lite function-calling loop. Streams every step (SSE)");
    const tools = [
      ["web_search", "Self-hosted SearXNG · Google grounding fallback"],
      ["read_page", "Scraper + PDF · Gemini url_context for blocked sites"],
      ["find_places", "Google Places API (New) · verified places"],
      ["recall (RAG)", "Per-chat vector store · Gemini embeddings"],
    ];
    tools.forEach(([h, sub], i) => box(7.75, 1.45 + i * 1.32, 5.0, 1.12, P.sand, h, sub, P.ink, P.muted));
    const arrow = (x1, y1, x2, y2) => s.addShape(pres.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color: P.green, width: 2, endArrowType: "triangle" } });
    arrow(3.15, 3.6, 3.8, 3.6);
    tools.forEach((_, i) => {
      const ty = 1.45 + i * 1.32 + 0.56;
      s.addShape(pres.shapes.LINE, { x: 7.0, y: Math.min(3.6, ty), w: 0.7, h: Math.abs(ty - 3.6), flipV: ty < 3.6, line: { color: P.green, width: 1.5, endArrowType: "triangle" } });
    });
    s.addText("Answer + resources + follow-ups, chosen only from what the agent actually saw", { x: 0.6, y: 5.25, w: 6.4, h: 0.8, fontSize: 15, italic: true, color: P.mangrove, margin: 0, isTextBox: true });
    s.addNotes("The React front end streams from a FastAPI backend. Gemini runs a tool loop: SearXNG web search we host ourselves, a page reader, Google Places for verified locations, and a per-chat vector store so follow-ups and documents build on earlier research.");
  }

  // 6 ─ Trust
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Grounded, not guessed", { placeholder: "title" });
    screenshot(s, "05-resources-summary.png", 0.6, 1.6, 6.6, "Resource card with a one-click summary of the FWC red tide status page");
    const pts = [
      [ic.book, "Links only from pages it read", "Resources are picked by index from sources the agent actually saw: no invented URLs"],
      [ic.map, "Places checked on Google Maps", "Addresses, ratings and open-now come from the Places API, not the model"],
      [ic.shield, "Official sources first", "Prefers .gov, FWC, NWS and county sites, and says to verify anything time-sensitive"],
    ];
    pts.forEach(([data, head, body], i) => {
      const y = 1.65 + i * 1.5;
      iconCircle(s, data, 7.65, y, 0.7, i === 2 ? P.sunset : i ? P.gulf : P.green);
      s.addText(head, { x: 8.55, y: y - 0.02, w: 4.2, h: 0.4, fontSize: 18, bold: true, color: P.ink, margin: 0, isTextBox: true });
      s.addText(body, { x: 8.55, y: y + 0.4, w: 4.2, h: 0.85, fontSize: 14, color: P.muted, margin: 0, valign: "top", isTextBox: true });
    });
    s.addNotes("For safety topics, trust matters. Every link comes from a page the agent read, places come from Google Maps, and the summary here is of the actual FWC red tide page, including their phone line and update schedule.");
  }

  // 7 ─ Itinerary
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("From an answer to a plan you can take with you", { placeholder: "title" });
    screenshot(s, "08-itinerary-doc.png", 0.6, 1.6, 5.85, "Generated 2-day Naples itinerary document");
    screenshot(s, "10-itinerary-map.png", 6.9, 1.6, 5.85, "Itinerary places pinned on a map with Google ratings");
    const chips = ["🗺️ Day-by-day itinerary", "📄 Practical guides", "📍 Map with verified places", "⬇ Download .md", "🖨 Print / Save PDF"];
    let x = 0.6;
    chips.forEach((t) => {
      const w = 0.35 + t.length * 0.085;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.75, w, h: 0.45, rectRadius: 0.22, fill: { color: P.sand }, line: { color: P.line } });
      s.addText(t, { x, y: 5.75, w, h: 0.45, fontSize: 13, color: P.ink, align: "center", valign: "middle", margin: 0, isTextBox: true });
      x += w + 0.15;
    });
    s.addNotes("Pick days, a home base and interests and the agent researches a full itinerary: morning, afternoon and evening, places verified on Google Maps, where to eat, practical tips like heat and red tide checks, and sources. Download it or print it as a PDF. Guides work the same way for any topic, like hurricane prep for renters.");
  }

  // 8 ─ Engineering
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Built to hold up on demo day", { placeholder: "title" });
    const cards = [
      [ic.bolt, P.green, "Cheap and fast", "Gemini 3.1 Flash-Lite first, automatic fallback to other models when one is overloaded"],
      [ic.wifi, P.gulf, "Search that survives venue Wi-Fi", "Our own SearXNG in Docker with public DNS and short engine timeouts; Google grounding if it comes back empty"],
      [ic.shield, P.sunset, "Never a dead end", "Retries empty model replies, reads blocked sites through Gemini, answers from gathered research if a step fails"],
      [ic.city, P.mangrove, "Self-contained", "Pinned search image saved in the repo folder, one-click start.bat, keys in a local .env"],
    ];
    cards.forEach(([data, color, head, body], i) => {
      const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.4;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 5.95, h: 2.15, rectRadius: 0.15, fill: { color: P.sand }, line: { color: P.sand } });
      iconCircle(s, data, x + 0.3, y + 0.35, 0.8, color);
      s.addText(head, { x: x + 1.35, y: y + 0.3, w: 4.35, h: 0.45, fontSize: 18, bold: true, color: P.ink, margin: 0, isTextBox: true });
      s.addText(body, { x: x + 1.35, y: y + 0.8, w: 4.35, h: 1.1, fontSize: 14, color: P.muted, margin: 0, valign: "top", isTextBox: true });
    });
    s.addNotes("Real-world problems we hit today and fixed: model overload, search engines timing out on the venue network, sites that block scrapers. Every one has a fallback, so the user always gets an answer.");
  }

  // 9 ─ Next
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("What's next for SWFL Compass", { placeholder: "title" });
    const next = [
      [ic.globe, "Spanish and Haitian Creole", "Serve more of SWFL's communities in their own language"],
      [ic.storm, "Hurricane mode", "Live NWS alerts, evacuation zone lookup by address, shelter map"],
      [ic.sms, "Text and voice access", "Ask by SMS or phone when the internet is down after a storm"],
      [ic.city, "Local partners", "County 311, FGCU and transit data feeds as trusted sources"],
    ];
    next.forEach(([data, head, body], i) => {
      const x = 0.6 + i * 3.08;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.75, w: 2.85, h: 3.9, rectRadius: 0.15, fill: { color: i % 2 ? P.sand : "E6F2EE" }, line: { color: i % 2 ? P.sand : "E6F2EE" } });
      iconCircle(s, data, x + 0.3, 2.05, 0.9, [P.green, P.sunset, P.gulf, P.mangrove][i]);
      s.addText(head, { x: x + 0.3, y: 3.15, w: 2.3, h: 0.8, fontSize: 18, bold: true, color: P.ink, margin: 0, valign: "top", isTextBox: true });
      s.addText(body, { x: x + 0.3, y: 3.95, w: 2.3, h: 1.5, fontSize: 14, color: P.muted, margin: 0, valign: "top", isTextBox: true });
    });
    s.addNotes("Where we'd take it: more languages for SWFL's communities, a dedicated hurricane mode, SMS and voice for when the internet is down after a storm, and partnerships with local data sources.");
  }

  // 10 ─ Close
  {
    const s = pres.addSlide({ masterName: "DARK" });
    s.addImage({ data: ic.compass, x: 0.7, y: 0.9, w: 0.8, h: 0.8 });
    s.addText("Thank you: questions?", { x: 0.7, y: 1.85, w: 7, h: 0.9, fontSize: 40, bold: true, color: P.white, margin: 0, isTextBox: true });
    s.addImage({ data: ic.github, x: 0.7, y: 3.05, w: 0.42, h: 0.42 });
    s.addText("github.com/Nicholas55555/swfl-compass", { x: 1.25, y: 3.0, w: 6, h: 0.5, fontSize: 20, color: P.sunset, margin: 0, valign: "middle", hyperlink: { url: "https://github.com/Nicholas55555/swfl-compass" }, isTextBox: true });
    s.addText("AI tools & APIs used", { x: 0.7, y: 4.0, w: 6, h: 0.45, fontSize: 18, bold: true, color: P.white, margin: 0, isTextBox: true });
    s.addText([
      { text: "Google Gemini API (3.1 Flash-Lite, function calling, url_context, Search grounding)", options: { bullet: true, breakLine: true } },
      { text: "Gemini Embeddings (gemini-embedding-001)", options: { bullet: true, breakLine: true } },
      { text: "Google Maps Places API (New)", options: { bullet: true, breakLine: true } },
      { text: "SearXNG (self-hosted) · OpenStreetMap + Leaflet", options: { bullet: true, breakLine: true } },
      { text: "Claude Code (development assistant)", options: { bullet: true } },
    ], { x: 0.7, y: 4.55, w: 7.6, h: 2.0, fontSize: 14, color: "CFE6DF", paraSpaceAfter: 4, margin: 0, valign: "top", isTextBox: true });
    // phone capture is 780x1688 (aspect 0.462)
    const mh = 5.7, mw = mh * 0.462;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.3 - 0.12, y: 0.9 - 0.12, w: mw + 0.24, h: mh + 0.24, rectRadius: 0.3, fill: { color: "1C1C1C" }, line: { color: "3A3A3A", width: 1 }, shadow: shadow() });
    s.addImage({ path: img("11-mobile.png"), x: 9.3, y: 0.9, w: mw, h: mh, altText: "SWFL Compass on a phone" });
    s.addText("Works on phones too", { x: 9.0, y: 6.85, w: mw + 0.6, h: 0.35, fontSize: 12, color: "9FC3BA", align: "center", margin: 0, isTextBox: true });
    s.addNotes("Thanks! The code, this deck and the demo video are on GitHub. Happy to take questions.");
  }

  await pres.writeFile({ fileName: OUT });
  console.log("wrote", OUT);
})();
