import assert from 'node:assert/strict';
import {Motion, OFFSET_X, OFFSET_Y, FOLLOW, FLYING, DWELLING} from './glance-cursor@glance.app/motion.js';

const run = (m, t0, secs, px, py, fps = 60) => {
  let t = t0; const end = t0 + secs;
  while (t < end) { t += 1 / fps; m.update(t, px, py); }
  return t;
};

// 1. seeds next to the pointer, then follows it smoothly (no teleport, converges)
let m = new Motion(); let t = 1; m.update(t, 100, 100);
assert.deepEqual(m.pos, {x: 100 + OFFSET_X, y: 100 + OFFSET_Y});
m.update(t += 1/60, 600, 400);
assert.ok(m.pos.x < 400, 'moves gradually, not instant');
t = run(m, t, 1.5, 600, 400);
assert.ok(Math.abs(m.pos.x - (600 + OFFSET_X)) < 0.5 && Math.abs(m.pos.y - (400 + OFFSET_Y)) < 0.5, 'converges');

// 2. frame-rate independent: 30fps and 144fps land in about the same place after 0.3s
const at = fps => { const k = new Motion(); k.update(1, 0, 0); run(k, 1, 0.3, 500, 0, fps); return k.pos.x; };
assert.ok(Math.abs(at(30) - at(144)) < 12, `fps independent ${at(30)} vs ${at(144)}`);

// 3. pointAt: flies, dwells at the target while held, then returns to the cursor
m = new Motion(); t = 1; m.update(t, 0, 0);
m.pointAt(800, 500, 'here'); m.setPointHold(true);
assert.equal(m.flight, FLYING);
t = run(m, t, 1.0, 0, 0);
assert.equal(m.flight, DWELLING);
assert.deepEqual(m.pos, {x: 800, y: 500});
t = run(m, t, 6, 0, 0);                    // hold => never auto-expires
assert.equal(m.flight, DWELLING);
m.releasePoint();
t = run(m, t, 2.5, 0, 0);
assert.equal(m.flight, FOLLOW);
assert.equal(m.locked, null);

// 4. dwell expires on its own when not held (4s)
m = new Motion(); t = 1; m.update(t, 0, 0); m.pointAt(300, 300, '');
t = run(m, t, 1.0, 0, 0); assert.equal(m.flight, DWELLING);
t = run(m, t, 4.5, 0, 0); assert.notEqual(m.flight, DWELLING);

// 5. annotations expire and fade
m = new Motion(); m.update(1, 0, 0); m.addAnnotation('circle', [1,2,3], 2);
m.update(1.5, 0, 0); assert.equal(m.annotations.length, 1); assert.equal(m.annotationAlpha(m.annotations[0]), 1);
m.update(2.8, 0, 0); assert.ok(m.annotationAlpha(m.annotations[0]) < 1);
m.update(3.5, 0, 0); assert.equal(m.annotations.length, 0);
console.log('motion: all tests passed');
