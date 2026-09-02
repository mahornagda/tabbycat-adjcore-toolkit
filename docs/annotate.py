"""
annotate.py — a screenshot with numbered pins, arrows and captions.

The arrows are NOT drawn into the image. The screenshot stays a plain PNG and
every mark is SVG laid over it, positioned in percentages, which buys four
things that matter for documentation:

  · it stays sharp at any width, and on a phone;
  · the captions are real text, so they are searchable, selectable and read
    correctly by a screen reader;
  · the marks re-colour for dark mode along with the rest of the page;
  · when the screenshot is retaken, the marks are still where they were, because
    they are described relative to the picture rather than burnt into it.

A figure is data:

    figure("tester-tracking-testing.png",
           caption="The Testing tab",
           pins=[Pin(0.11, 0.27, "Never tested", "Nobody on your core has sat "
                     "with this judge yet.", to=(0.04, 0.24))])

Coordinates are fractions of the image: 0,0 is top left, 1,1 is bottom right.
`to` is where the arrow points; leave it out for a pin with no arrow.
"""
import html
import os
from dataclasses import dataclass, field


@dataclass
class Pin:
    x: float                     # where the label sits
    y: float
    title: str
    text: str = ""
    to: tuple = None             # where the arrow points, if there is one
    side: str = "auto"           # "left" | "right" | "auto"


def _arrow(x1, y1, x2, y2, w, h):
    """A slightly curved arrow, in the image's own pixel coordinates.

    Coordinates arrive as fractions and are multiplied up, because the overlay
    has to use a viewBox with the IMAGE's aspect ratio. A 0-to-1 viewBox with
    `preserveAspectRatio="none"` seems tidier and is a trap: it scales x and y by
    different amounts, so circles come out as ellipses, arrowheads shear, and —
    the one that actually cost time — a text glyph sized in those units becomes
    thousands of pixels wide and quietly blankets the whole screenshot.
    """
    x1, y1, x2, y2 = x1 * w, y1 * h, x2 * w, y2 * h
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    bow = 0.14          # bow away from the straight line, so it reads as an
    cx, cy = mx - dy * bow, my + dx * bow      # arrow rather than a page rule
    return (f'<path class="fig-arrow" d="M {x1:.1f} {y1:.1f} Q {cx:.1f} {cy:.1f} '
            f'{x2:.1f} {y2:.1f}" marker-end="url(#fig-head)"/>')


_FIG_SEQ = [0]


def figure(image, caption="", pins=(), alt="", width=1400, height=900,
           assets="/assets/figures"):
    """Return the HTML for one annotated figure.

    The numbered badges are HTML, absolutely positioned in percentages, not SVG
    text — so they stay the same crisp size whatever width the figure is shown
    at, and they are selectable and readable by a screen reader. Only the arrows
    are SVG, in a viewBox that matches the image's aspect ratio so nothing
    shears.
    """
    _FIG_SEQ[0] += 1
    uid = f"fh{_FIG_SEQ[0]}"
    src = f"{assets}/{image}"
    arrows, badges, labels = [], [], []
    for i, p in enumerate(pins, 1):
        if p.to:
            arrows.append(_arrow(p.x, p.y, p.to[0], p.to[1], width, height))
        badges.append(
            f'<span class="fig-badge" style="left:{p.x * 100:.2f}%;'
            f'top:{p.y * 100:.2f}%" aria-hidden="true">{i}</span>')
        labels.append(
            f'<li><span class="n">{i}</span><div><b>{html.escape(p.title)}</b>'
            + (f'<p>{html.escape(p.text)}</p>' if p.text else "")
            + "</div></li>")
    svg = ""
    if arrows:
        svg = (
            f'<svg class="fig-overlay" viewBox="0 0 {width} {height}" '
            'aria-hidden="true">'
            f'<defs><marker id="{uid}" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" class="fig-arrowhead"/></marker>'
            "</defs>"
            + "".join(a.replace("url(#fig-head)", f"url(#{uid})") for a in arrows)
            + "</svg>")
    return f"""<figure class="fig">
  <div class="fig-frame">
    <img src="{src}" alt="{html.escape(alt or caption)}" loading="lazy"
         width="{width}" height="{height}">
    {svg}
    {''.join(badges)}
  </div>
  {f'<figcaption>{caption}</figcaption>' if caption else ''}
  <ol class="fig-keys">{''.join(labels)}</ol>
</figure>"""


CSS = """
/* ---- annotated figures ---------------------------------------------------- */
.fig{margin:32px 0}
.fig-frame{position:relative;border:1px solid var(--line);border-radius:10px;
  overflow:hidden;background:var(--panel);line-height:0}
.fig-frame img{width:100%;height:auto;display:block}
.fig-overlay{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.fig-arrow{fill:none;stroke:var(--mark);stroke-width:2.2px;
  vector-effect:non-scaling-stroke;stroke-linecap:round}
.fig-arrowhead{fill:var(--mark)}
/* The numbered badge is HTML, so it is one crisp size at every figure width. */
.fig-badge{position:absolute;transform:translate(-50%,-50%);width:22px;height:22px;
  border-radius:50%;background:var(--mark);color:#FFFDF9;
  font:600 12px/22px 'Inter Tight',system-ui,sans-serif;text-align:center;
  box-shadow:0 0 0 2px var(--panel),0 1px 3px rgba(0,0,0,.3);pointer-events:none}
.fig figcaption{margin:12px 0 0;font-size:.94rem;color:var(--dim)}
.fig-keys{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:10px;
  grid-template-columns:repeat(auto-fit,minmax(268px,1fr))}
.fig-keys li{display:flex;gap:10px;align-items:flex-start;font-size:.94rem}
.fig-keys .n{flex:0 0 20px;height:20px;border-radius:50%;background:var(--mark);
  color:var(--panel-strong);font:600 11px 'Inter Tight',system-ui,sans-serif;
  display:grid;place-items:center;margin-top:2px}
.fig-keys b{font-weight:600}
.fig-keys p{margin:3px 0 0;color:var(--dim)}
"""
