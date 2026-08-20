#!/usr/bin/env python3
"""
Check the mobile booking bar (.book-bar in public/index.html).

    python3 assets/check-bookbar.py                 # the repo file, over file://
    python3 assets/check-bookbar.py http://localhost:8787/   # a running wrangler dev

The bar is the phone-side half of a pair: below 640px the header CTA is hidden
and this fixed bar carries the booking action instead, and a script tucks the
bar away whenever one of the page's own booking buttons is already on screen.
That is behaviour no static check can see, so this drives a real Chrome over
the DevTools Protocol, emulates a phone viewport, scrolls the page, and reads
the bar's state at each stop.

Headless Chrome clamps --window-size to a 500px minimum, which is why this
uses Emulation.setDeviceMetricsOverride rather than a window size: 320px is
the width the layout is tightest at and the one worth testing.

Requires the websocket-client package and Google Chrome.
"""

import contextlib
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "public" / "index.html"
TARGET = PAGE.as_uri()          # overridden by an argv URL, e.g. a wrangler dev origin
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def _free_port():
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

# 320 is the classic narrow floor, 390/430 current iPhones, 639/640 the boundary
# the bar and the header CTA trade places across.
WIDTHS = [320, 360, 390, 430, 639, 640, 900]
VIEWPORT_H = 780


class Chrome:
    """A minimal CDP client: launch, one target, send/recv commands."""

    def __init__(self, port=None):
        port = port or _free_port()
        self.profile = tempfile.mkdtemp()
        self.proc = subprocess.Popen(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--no-first-run", "--disable-extensions", "--remote-allow-origins=*",
             f"--remote-debugging-port={port}", f"--user-data-dir={self.profile}",
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws_url = self._wait_for_target(port)
        self.ws = websocket.create_connection(ws_url, timeout=30, suppress_origin=True)
        self.n = 0

    @staticmethod
    def _wait_for_target(port, timeout=25):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as r:
                    for t in json.load(r):
                        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                            return t["webSocketDebuggerUrl"]
            except Exception:
                pass
            time.sleep(0.2)
        raise RuntimeError("Chrome did not expose a debuggable page target")

    def send(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def eval(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=await_promise)
        if r.get("exceptionDetails"):
            raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


# Scrolls to each stop, lets the observer settle, and reports the bar's state.
PROBE = """
(async function () {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const bar = document.querySelector('.book-bar');
  const gates = Array.from(document.querySelectorAll('.hero-actions, #book .cta-band'));
  const gatesOnScreen = () => gates.filter(g => {
    const r = g.getBoundingClientRect();
    return r.bottom > 0 && r.top < innerHeight;
  }).map(g => g.className.split(' ')[0]);
  const hdr = document.querySelector('.header-cta');
  const btn = bar && bar.querySelector('.btn');
  const foot = document.querySelector('footer.site-footer');
  if (!bar || !hdr || !btn) return { fatal: 'missing .book-bar, .header-cta or its button' };
  if (!gates.length) return { fatal: 'no booking CTAs found to gate the bar against' };

  // Stops are anchored to real elements rather than to fractions of the page, so
  // they keep meaning if the copy grows. The page sets scroll-behavior: smooth,
  // so every scroll here is explicitly instant -- otherwise the probe samples
  // mid-flight, and a fixed bar gives no hint that the page is still moving.
  const top = el => el.getBoundingClientRect().top + scrollY;
  const stops = [
    ['top-hero',    () => 0],
    ['past-hero',   () => top(document.querySelector('.hero-actions')) + 200],
    ['mid-page',    () => top(document.querySelector('#approach'))],
    ['rates-top',   () => top(document.querySelector('#book'))],
    ['page-bottom', () => document.documentElement.scrollHeight]
  ];
  const out = { widthCSS: innerWidth, stops: [] };
  out.headerCta = getComputedStyle(hdr).display;
  out.barDisplay = getComputedStyle(bar).display;
  out.hOverflow = document.documentElement.scrollWidth > innerWidth;
  out.scrollW = document.documentElement.scrollWidth;

  // IntersectionObserver delivers its callback as an idle task, so the slide can
  // start well after the scroll. Wait for the bar to stop moving instead of
  // guessing a delay, or the snapshot lands mid-transition.
  async function settle() {
    let last = null, still = 0;
    for (let i = 0; i < 60 && still < 3; i++) {
      await sleep(50);
      const now = bar.getBoundingClientRect().top + ':' + Math.round(scrollY);
      still = (last !== null && now === last) ? still + 1 : 0;
      last = now;
    }
  }

  for (const [label, at] of stops) {
    scrollTo({ top: at(), left: 0, behavior: 'instant' });
    await settle();
    const cs = getComputedStyle(bar), r = bar.getBoundingClientRect();
    const br = btn.getBoundingClientRect(), fr = foot.getBoundingClientRect();
    const shown = cs.display !== 'none' && cs.visibility !== 'hidden';
    let topmost = null;
    if (shown) {
      const el = document.elementFromPoint(Math.round(br.x + br.width / 2),
                                           Math.round(br.y + br.height / 2));
      topmost = el && btn.contains(el) ? 'bar-button' : (el ? (el.className || el.tagName) : 'none');
    }
    out.stops.push({
      label, scrollY: Math.round(scrollY), gates: gatesOnScreen(),
      tucked: bar.classList.contains('is-tucked'),
      animated: bar.classList.contains('is-animated'),
      shown,
      barBottomGap: +(innerHeight - r.bottom).toFixed(1),   // 0 when seated on the viewport floor
      barH: +r.height.toFixed(1),
      btnW: +br.width.toFixed(1), btnH: +br.height.toFixed(1),
      btnOverflows: btn.scrollWidth > Math.ceil(br.width),
      topmost,
      footerObscured: shown && fr.bottom > r.top && fr.top < r.bottom
    });
  }
  scrollTo({ top: 0, left: 0, behavior: 'instant' });
  return out;
})()
"""


def check(width, reduce_motion=False):
    """Run the probe at one width and return its report."""
    c = Chrome()
    try:
        c.send("Page.enable")
        c.send("Runtime.enable")
        if reduce_motion:
            # The bar drops its transition entirely here, so this also proves the
            # gating does not depend on the slide running.
            c.send("Emulation.setEmulatedMedia",
                   features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
        c.send("Emulation.setDeviceMetricsOverride", width=width, height=VIEWPORT_H,
               deviceScaleFactor=2, mobile=True)
        c.send("Page.navigate", url=TARGET)
        deadline = time.time() + 20
        while time.time() < deadline:
            if c.eval("document.readyState") == "complete":
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("page never reached readyState complete")
        time.sleep(0.4)
        return c.eval(PROBE, await_promise=True)
    finally:
        c.close()


def failures(width, rep):
    """Expectations, stated once, for both sides of the 640px boundary."""
    bad = []
    mobile = width < 640
    if rep.get("fatal"):
        return [rep["fatal"]]
    if rep["widthCSS"] != width:
        bad.append(f"emulated viewport is {rep['widthCSS']}px, expected {width}px")
    if rep["hOverflow"]:
        bad.append(f"page scrolls horizontally ({rep['scrollW']}px in a {width}px viewport)")

    want_bar = "block" if mobile else "none"
    # The header CTA is a flex item, so the computed value of inline-flex is flex.
    hdr_ok = rep["headerCta"] == "none" if mobile else rep["headerCta"] in ("flex", "inline-flex")
    if not hdr_ok:
        bad.append(f".header-cta display is {rep['headerCta']}, "
                   f"expected {'none' if mobile else 'flex/inline-flex'}")
    if rep["barDisplay"] != want_bar:
        bad.append(f".book-bar display is {rep['barDisplay']}, expected {want_bar}")

    seen_gated = seen_open = False
    for s in rep["stops"]:
        at = s["label"]
        if not mobile:
            if s["shown"]:
                bad.append(f"{at}: bar is on screen above the 640px boundary")
            continue
        # The contract: the bar is on screen exactly when none of the page's own
        # booking CTAs are. Read the gates rather than assume where they land, so
        # the check survives the copy growing or shrinking.
        gated = bool(s["gates"])
        seen_gated = seen_gated or gated
        seen_open = seen_open or not gated
        if gated and s["shown"]:
            bad.append(f"{at}: bar is on screen while {', '.join(s['gates'])} is too")
        if not gated and not s["shown"]:
            bad.append(f"{at}: bar is hidden where there is no other way to book")
        if s["shown"]:
            if abs(s["barBottomGap"]) > 0.5:
                bad.append(f"{at}: bar is {s['barBottomGap']}px off the viewport floor")
            if s["topmost"] != "bar-button":
                bad.append(f"{at}: something covers the bar button ({s['topmost']})")
            if s["footerObscured"]:
                bad.append(f"{at}: bar covers the footer")
        if s["btnOverflows"]:
            bad.append(f"{at}: button text overflows its pill ({s['btnW']}px wide)")
        if s["btnH"] < 44:
            bad.append(f"{at}: button is {s['btnH']}px tall, under the 44px touch target")

    # Guard against a vacuous pass: the stops have to exercise both states.
    if mobile and not (seen_gated and seen_open):
        bad.append("stops never exercised both states; the gating is untested here")
    return bad


def main():
    global TARGET
    if len(sys.argv) > 1:
        TARGET = sys.argv[1]
    print(f"Target: {TARGET}")
    if not Path(CHROME).exists():
        sys.exit(f"Chrome not found at {CHROME}")
    all_bad = 0
    runs = [(w, False) for w in WIDTHS] + [(390, True)]
    for w, reduce_motion in runs:
        rep = check(w, reduce_motion)
        bad = failures(w, rep)
        side = "phone" if w < 640 else "wide"
        if reduce_motion:
            side += ", reduced-motion"
        print(f"\n=== {w}px ({side}) — header-cta:{rep.get('headerCta')} "
              f"book-bar:{rep.get('barDisplay')} hOverflow:{rep.get('hOverflow')}")
        for s in rep.get("stops", []):
            state = "shown" if s["shown"] else ("tucked" if s["tucked"] else "off")
            gates = ','.join(s.get('gates') or []) or '-'
            print(f"    {s['label']:<12} y={s['scrollY']:<5} {state:<6} gates={gates:<18} "
                  f"barH={s['barH']:<5} btn={s['btnW']}x{s['btnH']} "
                  f"floorGap={s['barBottomGap']} topmost={s['topmost']}")
        for b in bad:
            print(f"    FAIL  {b}")
        all_bad += len(bad)
    print()
    if all_bad:
        sys.exit(f"{all_bad} failure(s)")
    print(f"All {len(runs)} runs pass.")


if __name__ == "__main__":
    main()
