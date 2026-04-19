#!/usr/bin/env node
// Bounce the procedural Web Audio soundtrack from promo/index.html to a WAV.
// Mirrors kick/hat/bass/arp/riser/whoosh/bing/tick_sfx + scheduleMusic + sceneFX
// from /Users/alex/spatial-deck/promo/index.html.

const { OfflineAudioContext } = require('node-web-audio-api');
const { WaveFile } = require('wavefile');
const fs = require('fs');
const path = require('path');

const SR = 48000;
const DURATION = 39.0; // seconds (matches DURATION = 39000ms in source)
const BPM = 128;
const BEAT = 60 / BPM; // seconds per beat

// Stereo offline context, 39s
const ctx = new OfflineAudioContext(2, Math.ceil(SR * (DURATION + 0.5)), SR);
const master = ctx.createGain();
master.gain.value = 0.55;
master.connect(ctx.destination);

function kick(t){
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.frequency.setValueAtTime(120, t);
  o.frequency.exponentialRampToValueAtTime(40, t + 0.12);
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(1, t + 0.005);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
  o.connect(g).connect(master);
  o.start(t); o.stop(t + 0.25);
}
function hat(t, open=false){
  const dur = 0.1;
  const b = ctx.createBuffer(1, Math.floor(SR * dur), SR);
  const d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random()*2 - 1);
  const s = ctx.createBufferSource(); s.buffer = b;
  const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 7000;
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.18, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + (open ? 0.18 : 0.05));
  s.connect(hp).connect(g).connect(master);
  s.start(t); s.stop(t + 0.2);
}
function bass(t, freq, dur = BEAT * 0.9){
  const o = ctx.createOscillator(), g = ctx.createGain(), lp = ctx.createBiquadFilter();
  o.type = 'sawtooth'; o.frequency.value = freq;
  lp.type = 'lowpass';
  lp.frequency.setValueAtTime(400, t);
  lp.frequency.exponentialRampToValueAtTime(1300, t + 0.05);
  lp.frequency.exponentialRampToValueAtTime(300, t + dur);
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.3, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.001, t + dur);
  o.connect(lp).connect(g).connect(master);
  o.start(t); o.stop(t + dur + 0.05);
}
function arp(t, freq){
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.type = 'square'; o.frequency.value = freq;
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.1, t + 0.005);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.15);
  o.connect(g).connect(master);
  o.start(t); o.stop(t + 0.2);
}
function riser(t, dur = 1.5){
  const b = ctx.createBuffer(1, Math.floor(SR * dur), SR);
  const d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random()*2 - 1);
  const n = ctx.createBufferSource(); n.buffer = b;
  const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 4;
  bp.frequency.setValueAtTime(300, t);
  bp.frequency.exponentialRampToValueAtTime(6500, t + dur);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.22, t + dur * 0.85);
  g.gain.linearRampToValueAtTime(0, t + dur);
  n.connect(bp).connect(g).connect(master);
  n.start(t); n.stop(t + dur + 0.05);
}
function whoosh(t){
  const dur = 0.4;
  const b = ctx.createBuffer(1, Math.floor(SR * dur), SR);
  const d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random()*2 - 1) * 0.7;
  const n = ctx.createBufferSource(); n.buffer = b;
  const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 2;
  bp.frequency.setValueAtTime(800, t);
  bp.frequency.exponentialRampToValueAtTime(4500, t + 0.35);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.35, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.4);
  n.connect(bp).connect(g).connect(master);
  n.start(t); n.stop(t + 0.45);
}
function bing(t, freq = 880){
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.type = 'triangle'; o.frequency.value = freq;
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.13, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.3);
  o.connect(g).connect(master);
  o.start(t); o.stop(t + 0.35);
}
function tick_sfx(t){
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.type = 'sine'; o.frequency.value = 2200;
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.06, t + 0.005);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.06);
  o.connect(g).connect(master);
  o.start(t); o.stop(t + 0.07);
}

// === scheduleMusic — directly ported ===
function scheduleMusic(startT){
  const bassNotes = [110, 110, 164.8, 110, 130.8, 110, 146.8, 110];
  const arpNotes  = [440, 523, 659, 523, 440, 659, 880, 659];
  const BARS = Math.ceil(DURATION / (BEAT * 4));
  for (let b = 0; b < BARS; b++){
    const barT = startT + b * BEAT * 4;
    if (barT >= DURATION) break;
    kick(barT);
    kick(barT + 2 * BEAT);
    hat(barT + BEAT, true);
    hat(barT + 3 * BEAT, true);
    for (let i = 0; i < 8; i++) hat(barT + i * BEAT / 2);
    for (let i = 0; i < 8; i++) bass(barT + i * BEAT / 2, bassNotes[i], BEAT / 2 * 0.95);
    if (b >= 2 && b % 2 === 1){
      for (let i = 0; i < 8; i++) arp(barT + i * BEAT / 2, arpNotes[i]);
    }
  }
  riser(startT + 6.0, 1.0);
  riser(startT + 18.0, 1.0);
  riser(startT + 33.0, 1.5);
}

// === Per-scene FX (mirrors sceneFX in source) ===
// Scene start times (seconds): s1=0, s2=2.5, s3=7, s4=15, s5=19, s6=27, s7=30.5, s8=34
function scheduleSceneFX(){
  // s2 (2.5s): whoosh, then typewrite ticks for "python tools/import_tokens.py claude-design.css"
  // typewrite speed=26ms/char. Tick fires per character.
  const s2 = 2.5;
  whoosh(s2);
  const t1Text = 'python tools/import_tokens.py claude-design.css';
  for (let i = 0; i < t1Text.length; i++) tick_sfx(s2 + (i + 1) * 0.026);
  bing(s2 + 1.3, 660);
  // 5 swatches: bing(440 + k*90) at +1.5s + k*0.1
  for (let k = 0; k < 5; k++) bing(s2 + 1.5 + k * 0.1, 440 + k * 90);

  // s3 (7s): whoosh + flythru1 (6 bing steps over ~6.5s with random freq)
  const s3 = 7;
  whoosh(s3);
  const tour1 = [50, 1300, 2600, 3900, 5200, 6500];
  tour1.forEach((ms) => bing(s3 + ms / 1000, 659 + 100)); // fixed freq (no rng)

  // s4 (15s): whoosh + typewrite "python tools/import_pptx.py talk.pptx"
  const s4 = 15;
  whoosh(s4);
  const t2Text = 'python tools/import_pptx.py talk.pptx';
  for (let i = 0; i < t2Text.length; i++) tick_sfx(s4 + (i + 1) * 0.026);
  bing(s4 + 1.1, 660);
  for (let k = 0; k < 4; k++) bing(s4 + 1.3 + k * 0.15, 523 + k * 80);

  // s5 (19s): whoosh + flythru2
  const s5 = 19;
  whoosh(s5);
  const tour2 = [50, 1400, 2800, 4200, 5600, 6900];
  tour2.forEach((ms) => bing(s5 + ms / 1000, 523 + 150));

  // s6 (27s): whoosh + bing(784) at +0.3
  const s6 = 27;
  whoosh(s6);
  bing(s6 + 0.3, 784);

  // s7 (30.5s): whoosh
  const s7 = 30.5;
  whoosh(s7);

  // s8 (34s): whoosh + chord
  const s8 = 34;
  whoosh(s8);
  bing(s8 + 0.1, 880);
  bing(s8 + 0.3, 1175);
  bing(s8 + 0.5, 1318);
}

scheduleMusic(0);
scheduleSceneFX();

(async () => {
  console.log('Rendering OfflineAudioContext...');
  const buf = await ctx.startRendering();
  console.log('Rendered. length=', buf.length, 'channels=', buf.numberOfChannels, 'sr=', buf.sampleRate);

  // Trim to DURATION seconds
  const outLen = Math.floor(SR * DURATION);
  const left = buf.getChannelData(0).subarray(0, outLen);
  const right = buf.numberOfChannels > 1 ? buf.getChannelData(1).subarray(0, outLen) : left;

  // Convert float32 to int16
  const toInt16 = (f32) => {
    const out = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++){
      let s = Math.max(-1, Math.min(1, f32[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return out;
  };

  const wav = new WaveFile();
  wav.fromScratch(2, SR, '16', [toInt16(left), toInt16(right)]);
  const outPath = path.resolve(__dirname, 'hyperframes/assets/track.wav');
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, wav.toBuffer());
  console.log('Wrote', outPath, 'bytes=', fs.statSync(outPath).size);
})().catch(e => { console.error(e); process.exit(1); });
