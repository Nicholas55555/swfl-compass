// Feature-tour and output slides, spliced into build_deck.js between the demo and architecture slides.
// Exported as a function of the shared deck context so build_deck.js stays the single entry point.
const path = require("path");
const sharp = require("sharp");

const SAMPLES = path.join(__dirname, "..", "docs", "samples", "previews");
const prev = (n) => path.join(SAMPLES, n);
const PAGE = 8.5 / 11; // Letter page aspect (w/h)
const PHONE = 780 / 1688; // 390x844 @2x captures

module.exports = async function featureSlides({ pres, P, ic, img, iconCircle, screenshot, shadow }) {
  const frameShadow = shadow;

  const phone = (s, file, x, y, h, alt) => {
    const w = h * PHONE;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.1, y: y - 0.1, w: w + 0.2, h: h + 0.2, rectRadius: 0.25, fill: { color: "1C1C1C" }, line: { color: "3A3A3A", width: 1 }, shadow: frameShadow() });
    s.addImage({ path: img(file), x, y, w, h, altText: alt });
    return w;
  };
  const page = (s, file, x, y, h, rotate = 0, alt = "") => {
    const w = h * PAGE;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, rotate, fill: { color: P.white }, line: { color: P.line, width: 0.75 }, shadow: frameShadow() });
    s.addImage({ path: prev(file), x, y, w, h, rotate, altText: alt });
    return w;
  };
  const kicker = (s, text, x, y, w, color = P.green) =>
    s.addText(text.toUpperCase(), { x, y, w, h: 0.3, fontSize: 11, bold: true, color, charSpacing: 2, margin: 0, isTextBox: true });
  const point = (s, data, color, head, body, x, y, w) => {
    iconCircle(s, data, x, y, 0.62, color);
    s.addText(head, { x: x + 0.8, y: y - 0.04, w: w - 0.8, h: 0.36, fontSize: 17, bold: true, color: P.ink, margin: 0, isTextBox: true });
    s.addText(body, { x: x + 0.8, y: y + 0.33, w: w - 0.8, h: 0.62, fontSize: 14, color: P.muted, margin: 0, valign: "top", isTextBox: true });
  };
  const caption = (s, text, x, y, w, align = "left", color = P.muted) =>
    s.addText(text, { x, y, w, h: 0.32, fontSize: 12, italic: true, color, align, margin: 0, isTextBox: true });
  const stat = (s, big, label, x, y, w, color) => {
    s.addText(big, { x, y, w, h: 0.75, fontSize: 40, bold: true, color, margin: 0, isTextBox: true });
    s.addText(label, { x, y: y + 0.72, w, h: 0.5, fontSize: 13, color: P.muted, margin: 0, valign: "top", isTextBox: true });
  };
  const arrow = (s, x, y, w, color = P.sunset) =>
    s.addShape(pres.shapes.RIGHT_ARROW, { x, y, w, h: 0.42, fill: { color }, line: { color } });

  // ── Personas
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Tailored to who you are", { placeholder: "title" });
    screenshot(s, "01-welcome.png", 0.6, 1.55, 5.6, "Welcome screen");
    screenshot(s, "12-student-welcome.png", 2.3, 3.0, 5.6, "Student persona selected with student starter questions");
    caption(s, "Pick “I study here” and the starter questions change", 2.3, 6.6, 5.6);
    const rows = [
      [ic.home, P.green, "Residents", "Hurricane zones, red tide, utility help"],
      [ic.grad, P.gulf, "Students", "Transit, housing, campus wellness"],
      [ic.work, P.mangrove, "Workers", "Training, hiring industries, childcare"],
      [ic.beach, P.sunset, "Visitors", "Beaches, wildlife, food, safety"],
    ];
    rows.forEach(([d, c, h, b], i) => point(s, d, c, h, b, 8.55, 1.65 + i * 1.12, 4.2));
    s.addText("The persona also tunes the agent’s advice, not just the suggestions.", { x: 8.55, y: 6.15, w: 4.2, h: 0.6, fontSize: 13, italic: true, color: P.mangrove, margin: 0, isTextBox: true });
    s.addNotes("Users start by saying who they are. That changes the starter questions and is passed to the agent so advice fits a resident, student, worker or visitor.");
  }

  // ── Live research with zoomed steps
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Watch the agent research in real time", { placeholder: "title" });
    screenshot(s, "13-followup-rag-steps.png", 0.6, 1.6, 6.2, "Follow-up answer with the agent steps expanded");
    const crop = await sharp(img("13-followup-rag-steps.png")).extract({ left: 236, top: 104, width: 560, height: 120 }).resize({ width: 1680 }).png().toBuffer();
    const zw = 5.75, zh = zw * (120 / 560);
    kicker(s, "Zoom: the agent’s own steps", 7.2, 1.6, zw);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.14, y: 1.94, w: zw + 0.12, h: zh + 0.12, rectRadius: 0.08, fill: { color: P.white }, line: { color: P.sunset, width: 2 }, shadow: frameShadow() });
    s.addImage({ data: "image/png;base64," + crop.toString("base64"), x: 7.2, y: 2.0, w: zw, h: zh, altText: "Agent steps: recalled passages, web search, Google Maps places" });
    const tools = [
      [ic.book, P.mangrove, "Recall", "Found 5 relevant passages from earlier in the chat"],
      [ic.search, P.green, "Web search", "SearXNG first, Google grounding when it comes back empty"],
      [ic.map, P.gulf, "Google Places", "Real apartments near FGCU with addresses and ratings"],
    ];
    tools.forEach(([d, c, h, b], i) => point(s, d, c, h, b, 7.2, 3.55 + i * 1.08, 5.75));
    s.addNotes("Every tool call streams to the UI. This is a follow-up question: the agent first pulled five passages from its own memory of the chat, searched the web once more, then checked student apartments on Google Maps.");
  }

  // ── Verified places on a map
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Real places, verified on Google Maps", { placeholder: "title" });
    screenshot(s, "10-itinerary-map.png", 0.6, 1.6, 7.2, "Six places pinned on a map with Google ratings");
    const pw = phone(s, "17-mobile-map.png", 8.2, 1.6, 4.6, "Manatee Park pinned on a phone");
    const items = [
      ["★ 4.6 (319)", "Google rating + review count"],
      ["Open now", "Live open/closed status"],
      ["Maps ↗  Website ↗", "Official links, never guessed"],
    ];
    items.forEach(([big, small], i) => {
      const x = 8.2 + pw + 0.3, y = 1.65 + i * 1.55;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.1, h: 1.35, rectRadius: 0.12, fill: { color: P.sand }, line: { color: P.sand } });
      s.addText(big, { x: x + 0.15, y: y + 0.15, w: 1.85, h: 0.5, fontSize: 15, bold: true, color: i === 1 ? P.green : P.gulf, margin: 0, isTextBox: true });
      s.addText(small, { x: x + 0.15, y: y + 0.65, w: 1.85, h: 0.6, fontSize: 12, color: P.muted, margin: 0, valign: "top", isTextBox: true });
    });
    caption(s, "Numbered pins match the place cards · click a card to zoom the map", 0.6, 6.25, 7.2);
    s.addNotes("The find_places tool calls the Google Places API, so addresses, ratings and open-now status are real. Places the answer mentions are pinned on an OpenStreetMap map, on desktop and on phones.");
  }

  // ── Resources & summaries (grounding)
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Resources you can trust, summarized in one click", { placeholder: "title" });
    screenshot(s, "05-resources-summary.png", 0.6, 1.6, 6.6, "FWC red tide page summarized in one click");
    const pts = [
      [ic.book, P.green, "Links only from pages it read", "Resources are picked by index from what the agent actually saw: no invented URLs"],
      [ic.doc, P.gulf, "Summarize any resource", "Key points + what you can do: phone numbers, schedules, sign-ups"],
      [ic.shield, P.sunset, "Official sources first", ".gov, FWC, NWS and county sites; reminds you to verify time-sensitive info"],
    ];
    pts.forEach(([d, c, h, b], i) => point(s, d, c, h, b, 7.65, 1.7 + i * 1.5, 5.1));
    s.addNotes("Resources come only from pages the agent read. One click summarizes any of them; here the FWC red tide page becomes key points plus actions, including FWC's phone line and update schedule.");
  }

  // ── Follow-ups + memory (RAG)
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Follow-ups that remember what it learned", { placeholder: "title" });
    screenshot(s, "06-followups.png", 0.6, 1.6, 5.8, "Suggested follow-up questions");
    caption(s, "Three follow-ups written in your voice, one click to ask", 0.6, 5.35, 5.8);
    kicker(s, "Per-chat RAG memory", 7.0, 1.6, 5.7, P.gulf);
    const flow = [
      [P.green, "Pages & results read", "full text, not truncated"],
      [P.gulf, "Chunk + embed", "Gemini embedding-001"],
      [P.mangrove, "Chat’s vector store", "in-memory, per session"],
      [P.sunset, "Top passages → next turn", "auto-retrieved every question"],
    ];
    flow.forEach(([c, h, b], i) => {
      const y = 2.0 + i * 1.12;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.0, y, w: 5.7, h: 0.86, rectRadius: 0.12, fill: { color: c }, line: { color: c } });
      s.addText([{ text: h, options: { bold: true, fontSize: 16, breakLine: true } }, { text: b, options: { fontSize: 12 } }], { x: 7.25, y, w: 5.3, h: 0.86, color: P.white, valign: "middle", margin: 0, isTextBox: true });
      if (i < flow.length - 1) s.addShape(pres.shapes.DOWN_ARROW, { x: 9.7, y: y + 0.88, w: 0.3, h: 0.22, fill: { color: P.line }, line: { color: P.line } });
    });
    s.addNotes("After each answer it suggests what you'd ask next. Everything the agent reads is chunked, embedded with Gemini and kept in that chat's vector store, so follow-ups, itineraries and guides build on earlier research instead of starting over.");
  }

  // ── Itinerary: builder → plan
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Plan a whole trip from one form", { placeholder: "title" });
    screenshot(s, "07-itinerary-builder.png", 0.6, 1.7, 4.3, "Itinerary builder: days, home base, interests");
    caption(s, "1 · Choose days, home base, interests", 0.6, 4.55, 4.3);
    arrow(s, 5.15, 3.0, 0.7);
    screenshot(s, "08-itinerary-doc.png", 6.1, 1.6, 6.65, "Generated 2-day Naples itinerary");
    caption(s, "2 · The agent researches and writes the plan", 6.1, 5.85, 6.65);
    screenshot(s, "09-itinerary-days.png", 0.6, 4.95, 2.85, "Day 2 of the itinerary");
    s.addText("Morning / afternoon / evening, cost, Maps link for every stop", { x: 3.65, y: 5.3, w: 2.2, h: 1.1, fontSize: 13, color: P.mangrove, margin: 0, valign: "top", isTextBox: true });
    s.addNotes("The itinerary builder takes days, a home base, interests and notes like 'visiting in March'. The agent runs a longer research loop and writes a day-by-day plan in the chat.");
  }

  // ── Itinerary output (PDF pages)
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("The output: a 3-day family itinerary, ready to print", { placeholder: "title" });
    page(s, "itinerary-3-day-fort-myers-family-p3.png", 4.25, 1.85, 4.85, 6, "Itinerary page 3: verified places table");
    page(s, "itinerary-3-day-fort-myers-family-p2.png", 2.5, 1.7, 4.95, 3, "Itinerary page 2");
    page(s, "itinerary-3-day-fort-myers-family-p1.png", 0.6, 1.55, 5.1, -2, "Itinerary page 1: days 1-3");
    stat(s, "3", "days, each with morning, afternoon and evening", 8.55, 1.6, 4.2, P.green);
    stat(s, "9", "places checked on Google Maps, with ratings, addresses and links", 8.55, 3.0, 4.2, P.gulf);
    stat(s, "1 click", "to download Markdown or print to PDF", 8.55, 4.4, 4.2, P.sunset);
    caption(s, "Unedited output: docs/samples/itinerary-3-day-fort-myers-family.pdf", 8.55, 6.2, 4.2);
    s.addNotes("This is a real, unedited export. Prompt: three days in Fort Myers with two kids in March. Ding Darling, Six Mile Cypress, Lovers Key, Calusa Nature Center, family restaurants, practical tips, sources, and a table of nine Google-verified places.");
  }

  // ── Guides
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Guides for any topic, with checklists", { placeholder: "title" });
    screenshot(s, "15-guide-doc.png", 0.6, 1.6, 6.3, "FGCU off-campus move-in guide in the app");
    caption(s, "In the app: “FGCU off-campus move-in” guide with checkboxes", 0.6, 5.65, 6.3);
    page(s, "guide-hurricane-prep-renters-lee-county-p2.png", 9.3, 1.8, 4.3, 4, "Hurricane guide page 2");
    page(s, "guide-hurricane-prep-renters-lee-county-p1.png", 7.3, 1.6, 4.5, -2, "Hurricane guide page 1");
    caption(s, "Exported PDF: “Hurricane prep for Lee County renters”", 7.3, 6.3, 5.35);
    s.addNotes("Guides work for any topic, or turn the current conversation into a guide. Left, a move-in checklist for FGCU students generated in the app; right, the exported PDF of a hurricane-prep guide for Lee County renters with AlertLee and the county's All Hazards Guide.");
  }

  // ── Every output exports
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Every output leaves the app with you", { placeholder: "title" });
    const docs = [
      ["itinerary-3-day-fort-myers-family-p1.png", "🗺️ Itinerary", P.green],
      ["guide-hurricane-prep-renters-lee-county-p1.png", "📄 Guide", P.gulf],
      ["answer-fgcu-to-downtown-without-car-p1.png", "💬 Chat answer", P.mangrove],
      ["summary-fwc-red-tide-status-p1.png", "✨ Resource summary", P.sunset],
    ];
    docs.forEach(([f, label, c], i) => {
      const x = 0.75 + i * 3.1;
      page(s, f, x, 1.6, 3.55, 0, label);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.3, w: 3.55 * PAGE, h: 0.45, rectRadius: 0.22, fill: { color: c }, line: { color: c } });
      s.addText(label, { x, y: 5.3, w: 3.55 * PAGE, h: 0.45, fontSize: 14, bold: true, color: P.white, align: "center", valign: "middle", margin: 0, isTextBox: true });
    });
    s.addText([
      { text: "⬇ Download .md", options: { bold: true, color: P.ink } },
      { text: "     🖨 Print / Save PDF", options: { bold: true, color: P.ink } },
      { text: "     📋 Copy", options: { bold: true, color: P.ink } },
      { text: "     ·  all four are real exports in docs/samples/", options: { color: P.muted, italic: true } },
    ], { x: 0.75, y: 6.05, w: 12, h: 0.45, fontSize: 15, margin: 0, isTextBox: true });
    s.addNotes("Itineraries, guides, chat answers and resource summaries all export: Markdown download, print or save as PDF, or copy. All four of these are real, unedited outputs in the repo.");
  }

  // ── Phones
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Built for phones: where people need it", { placeholder: "title" });
    const shots = [
      ["11-mobile.png", "Pick who you are"],
      ["16-mobile-answer.png", "Researched answer"],
      ["17-mobile-map.png", "Places on the map"],
    ];
    shots.forEach(([f, label], i) => {
      const x = 0.9 + i * 2.75;
      phone(s, f, x, 1.6, 4.75, label);
      caption(s, label, x - 0.2, 6.5, 2.6, "center", P.ink);
    });
    point(s, ic.beach, P.sunset, "On the beach or in the car", "Same features on a phone: research, map, resources, documents", 9.4, 2.0, 3.4);
    point(s, ic.storm, P.gulf, "When it matters most", "Storm-season questions get official sources and verify-first reminders", 9.4, 3.55, 3.4);
    s.addNotes("Most people will ask from a phone: on the beach, in the car, during storm season. Everything works at phone width.");
  }
};
