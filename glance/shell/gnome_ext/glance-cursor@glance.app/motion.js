// Pure animation state for Glance's buddy cursor — no GNOME imports, so it can
// be unit-tested with node. A faithful port of glance/shell/ui/overlay.py:
// spring-follow, bezier flight to a target, dwell, and return.

export const OFFSET_X = 35;
export const OFFSET_Y = 25;

const FLY_MIN = 0.35, FLY_MAX = 0.7, DWELL = 4.0, RETURN = 1.4;
const STEP = 1 / 60;                 // spring/phase constants are per-60Hz-frame
const STIFFNESS = 0.28, DAMPING = 0.62;

export const FOLLOW = 'follow', FLYING = 'flying',
    DWELLING = 'dwelling', RETURNING = 'returning';

export class Motion {
    constructor() {
        this.pos = {x: 0, y: 0};
        this.vel = {x: 0, y: 0};
        this.mode = 'idle';
        this.audio = 0;
        this.phase = 0;
        this.spin = 0;
        this.locked = null;
        this.bubbleText = '';
        this.bubbleAlpha = 0;
        this.bubbleScale = 0.5;
        this.rotation = 0;
        this.scale = 1;
        this.flight = FOLLOW;
        this.hold = false;
        this.slow = false;
        this.annotations = [];
        this.now = 0;
        this._seeded = false;
        this._acc = 0;
        this._last = null;
        this._dwellUntil = 0;
        this._f = null;              // active flight {start,end,ctrl,t0,dur}
    }

    // ── commands (mirror CursorOverlay's public API) ───────────────────────
    setMode(mode) { this.mode = mode; }

    setAudioLevel(rms) {
        const norm = Math.max(rms - 0.008, 0);
        const eased = Math.min(norm * 2.85, 1) ** 0.76;
        this.audio = this.audio * 0.55 + eased * 0.45;
    }

    setSlowMode(on) { this.slow = !!on; }

    setPointHold(hold) {
        this.hold = !!hold;
        if (hold && this.flight === DWELLING)
            this._dwellUntil = Infinity;
    }

    pointAt(x, y, label) {
        this.locked = {x, y};
        this.bubbleText = label || '';
        this.bubbleScale = 0.5;
        this.bubbleAlpha = 0;
        this._beginFlight(this.pos, this.locked, FLYING);
    }

    releasePoint() {
        this.hold = false;
        if (this.flight === DWELLING)
            this._dwellUntil = 0;
        this.annotations = [];
    }

    hideCursor() {
        this._releaseLock();
        this.mode = 'idle';
    }

    addAnnotation(kind, args, ttl) {
        this.annotations.push({kind, args, born: this.now, ttl: ttl || 8});
    }

    clearAnnotations() { this.annotations = []; }

    // ── frame update ──────────────────────────────────────────────────────
    /** Advance to monotonic time `now` (seconds) with the real pointer at (px,py). */
    update(now, px, py) {
        this.now = now;
        if (!this._seeded) {
            this.pos = {x: px + OFFSET_X, y: py + OFFSET_Y};
            this._seeded = true;
        }
        const dt = this._last === null ? STEP : Math.min(now - this._last, 0.1);
        this._last = now;
        this._acc += dt;
        let n = 0;
        while (this._acc >= STEP && n < 8) {
            this._step(now, px, py);
            this._acc -= STEP;
            n++;
        }
        if (n === 8) this._acc = 0;
        this.annotations = this.annotations.filter(a => now - a.born <= a.ttl);
    }

    annotationAlpha(a) {
        const age = this.now - a.born;
        if (age <= a.ttl * 0.75) return 1;
        return Math.max(0, 1 - (age - a.ttl * 0.75) / (a.ttl * 0.25));
    }

    // ── internals ─────────────────────────────────────────────────────────
    _beginFlight(start, end, phase) {
        const dx = end.x - start.x, dy = end.y - start.y;
        const dist = Math.hypot(dx, dy);
        const mult = this.slow ? 1.7 : 1.0;
        let dur = Math.max(FLY_MIN, Math.min(FLY_MAX, FLY_MIN + dist / 700));
        if (phase === RETURNING) dur = RETURN;
        dur *= mult;
        const arc = Math.min(dist * 0.22, 90);
        this._f = {
            start: {x: start.x, y: start.y},
            end: {x: end.x, y: end.y},
            ctrl: {x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 - arc},
            t0: this.now,
            dur,
        };
        this.flight = phase;
        this.vel = {x: 0, y: 0};
    }

    _releaseLock() {
        this.locked = null;
        this.bubbleText = '';
        this.bubbleAlpha = 0;
        this.bubbleScale = 0.5;
        this.flight = FOLLOW;
        this.scale = 1;
        this.rotation = 0;
        this.hold = false;
    }

    _step(now, px, py) {
        if (this.flight === FLYING || this.flight === RETURNING) {
            const f = this._f;
            const lp = Math.min(1, (now - f.t0) / Math.max(0.001, f.dur));
            const t = lp * lp * (3 - 2 * lp);
            const o = 1 - t;
            this.pos = {
                x: o * o * f.start.x + 2 * o * t * f.ctrl.x + t * t * f.end.x,
                y: o * o * f.start.y + 2 * o * t * f.ctrl.y + t * t * f.end.y,
            };
            const tx = 2 * o * (f.ctrl.x - f.start.x) + 2 * t * (f.end.x - f.ctrl.x);
            const ty = 2 * o * (f.ctrl.y - f.start.y) + 2 * t * (f.end.y - f.ctrl.y);
            this.rotation = Math.atan2(ty, tx) * 180 / Math.PI + 90;
            this.scale = 1 + Math.sin(lp * Math.PI) * 0.25;
            if (this.flight === FLYING) {
                this.bubbleAlpha = Math.min(1, lp * 1.4);
                this.bubbleScale = 0.5 + lp * 0.5;
            }
            if (lp >= 1) {
                if (this.flight === FLYING) {
                    this.flight = DWELLING;
                    this._dwellUntil = this.hold
                        ? Infinity
                        : now + DWELL * (this.slow ? 1.7 : 1.0);
                    this.scale = 1;
                    this.rotation = 0;
                } else {
                    this._releaseLock();
                }
            }
            this.phase += 0.10;
            return;
        }

        if (this.flight === DWELLING) {
            this.scale = 1 + 0.05 * Math.sin(this.phase * 1.4);
            this.bubbleAlpha = Math.min(1, this.bubbleAlpha + 0.05);
            this.bubbleScale += (1 - this.bubbleScale) * 0.15;
            this.pos = {x: this.locked.x, y: this.locked.y};
            if (now >= this._dwellUntil) {
                this._beginFlight(this.pos, {x: px + OFFSET_X, y: py + OFFSET_Y}, RETURNING);
                this.bubbleAlpha = 0;
            }
            this.phase += 0.10;
            return;
        }

        // normal cursor-follow spring
        const ax = (px + OFFSET_X - this.pos.x) * STIFFNESS;
        const ay = (py + OFFSET_Y - this.pos.y) * STIFFNESS;
        this.vel = {x: this.vel.x * DAMPING + ax, y: this.vel.y * DAMPING + ay};
        this.pos = {x: this.pos.x + this.vel.x, y: this.pos.y + this.vel.y};
        this.phase += 0.10;
        this.spin += 0.14;
    }
}
