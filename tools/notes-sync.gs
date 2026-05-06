// =====================================================================
// Spatial Deck — Notes Sync (Google Apps Script Web App)
// =====================================================================
// Bound to a Google Sheet. Deployed as a Web App, "Execute as: me",
// "Anyone with the link". The browser deck calls this URL via fetch().
//
// Sheet layout (auto-created on first call):
//   Tab "slides": deckId | idx | type | title | script | bullets | video_seconds
//   Tab "meta":   deckId | key | value
//
// Meta keys used by the deck:
//   target_finish    ISO datetime string ("2026-09-25T18:30:00")
//   default_view     "script" | "bullets"
//   wpm              Number (override; otherwise adaptive)
//   calibration      JSON: {videoDurations:{src:seconds}, thumbnails:{idx:dataUrl}}
//   state            JSON: {currentSlide, lastAction, lastActionTs, locked}
// =====================================================================

const SHEET_ID = '1i2uKrT4UpslV8hWOetBZy4IW4ORWKidUnpwjigtzVP4';

const SLIDES_HEADERS = ['deckId', 'idx', 'type', 'title', 'script', 'bullets', 'video_seconds'];
const META_HEADERS = ['deckId', 'key', 'value'];

function doGet(e) { return handle_(e); }
function doPost(e) { return handle_(e); }

function handle_(e) {
  try {
    const body = e.postData && e.postData.contents
      ? JSON.parse(e.postData.contents)
      : {};
    const params = e.parameter || {};
    const action = body.action || params.action;
    const deckId = body.deckId || params.deckId || 'default';

    let result;
    switch (action) {
      case 'getNotes': result = getNotes_(deckId); break;
      case 'setNotes': result = setNotes_(deckId, body.slides, body.meta); break;
      case 'setSlideNote': result = setSlideNote_(deckId, body.idx, body.fields); break;
      case 'setMeta': result = setMeta_(deckId, body.key, body.value); break;
      case 'getState': result = getState_(deckId); break;
      case 'setState': result = setMeta_(deckId, 'state', JSON.stringify(body.state)); break;
      case 'seedNotes': result = seedNotes_(deckId, body.slides); break;
      case 'ping': result = { pong: true, ts: Date.now() }; break;
      default: throw new Error('Unknown action: ' + action);
    }
    return jsonResponse_({ ok: true, result });
  } catch (err) {
    return jsonResponse_({ ok: false, error: String(err && err.message || err) });
  }
}

function jsonResponse_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function getOrCreateSheet_(name, headers) {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headers);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function getNotes_(deckId) {
  const slides = getOrCreateSheet_('slides', SLIDES_HEADERS);
  const meta = getOrCreateSheet_('meta', META_HEADERS);

  const slideRows = slides.getDataRange().getValues().slice(1)
    .filter(r => r[0] === deckId);
  const metaRows = meta.getDataRange().getValues().slice(1)
    .filter(r => r[0] === deckId);

  const metaObj = {};
  metaRows.forEach(r => {
    let v = r[2];
    if (typeof v === 'string' && (v.startsWith('{') || v.startsWith('['))) {
      try { v = JSON.parse(v); } catch (_) {}
    }
    metaObj[r[1]] = v;
  });

  return {
    slides: slideRows.map(r => ({
      idx: Number(r[1]),
      type: r[2],
      title: r[3],
      script: r[4] || '',
      bullets: r[5] ? String(r[5]).split('\n').map(s => s.trim()).filter(Boolean) : null,
      video_seconds: r[6] !== '' && r[6] != null ? Number(r[6]) : null
    })).sort((a, b) => a.idx - b.idx),
    meta: metaObj
  };
}

function setNotes_(deckId, slidesData, metaData) {
  if (slidesData) writeSlides_(deckId, slidesData);
  if (metaData) {
    Object.keys(metaData).forEach(k => setMeta_(deckId, k, metaData[k]));
  }
  return { ok: true };
}

function writeSlides_(deckId, slidesData) {
  const sheet = getOrCreateSheet_('slides', SLIDES_HEADERS);
  // Wipe existing rows for this deckId (bottom-up to keep indices stable)
  const data = sheet.getDataRange().getValues();
  for (let i = data.length - 1; i >= 1; i--) {
    if (data[i][0] === deckId) sheet.deleteRow(i + 1);
  }
  if (!slidesData || !slidesData.length) return;
  const rows = slidesData.map(s => [
    deckId,
    s.idx,
    s.type || '',
    s.title || '',
    s.script || '',
    Array.isArray(s.bullets) ? s.bullets.join('\n') : (s.bullets || ''),
    s.video_seconds != null ? s.video_seconds : ''
  ]);
  sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, SLIDES_HEADERS.length)
    .setValues(rows);
}

function setSlideNote_(deckId, idx, fields) {
  const sheet = getOrCreateSheet_('slides', SLIDES_HEADERS);
  const data = sheet.getDataRange().getValues();
  let rowNum = -1;
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === deckId && Number(data[i][1]) === Number(idx)) {
      rowNum = i + 1;
      break;
    }
  }
  if (rowNum === -1) {
    // Append new row
    sheet.appendRow([
      deckId, idx,
      fields.type || '',
      fields.title || '',
      fields.script || '',
      Array.isArray(fields.bullets) ? fields.bullets.join('\n') : (fields.bullets || ''),
      fields.video_seconds != null ? fields.video_seconds : ''
    ]);
    return { ok: true, created: true };
  }
  // Update existing row, only changed fields
  if ('type' in fields) sheet.getRange(rowNum, 3).setValue(fields.type);
  if ('title' in fields) sheet.getRange(rowNum, 4).setValue(fields.title);
  if ('script' in fields) sheet.getRange(rowNum, 5).setValue(fields.script);
  if ('bullets' in fields) {
    sheet.getRange(rowNum, 6).setValue(
      Array.isArray(fields.bullets) ? fields.bullets.join('\n') : fields.bullets
    );
  }
  if ('video_seconds' in fields) {
    sheet.getRange(rowNum, 7).setValue(fields.video_seconds == null ? '' : fields.video_seconds);
  }
  return { ok: true, updated: true };
}

function setMeta_(deckId, key, value) {
  const sheet = getOrCreateSheet_('meta', META_HEADERS);
  const data = sheet.getDataRange().getValues();
  const stored = (typeof value === 'object' && value !== null)
    ? JSON.stringify(value)
    : value;
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === deckId && data[i][1] === key) {
      sheet.getRange(i + 1, 3).setValue(stored);
      return { ok: true, updated: true };
    }
  }
  sheet.appendRow([deckId, key, stored]);
  return { ok: true, created: true };
}

function getState_(deckId) {
  const sheet = getOrCreateSheet_('meta', META_HEADERS);
  const data = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === deckId && data[i][1] === 'state') {
      try { return JSON.parse(data[i][2]); }
      catch (_) { return null; }
    }
  }
  return null;
}

function seedNotes_(deckId, slidesData) {
  const sheet = getOrCreateSheet_('slides', SLIDES_HEADERS);
  const data = sheet.getDataRange().getValues();
  const existing = data.slice(1).filter(r => r[0] === deckId);
  if (existing.length > 0) {
    return { seeded: false, existingCount: existing.length };
  }
  writeSlides_(deckId, slidesData);
  return { seeded: true, count: slidesData.length };
}
