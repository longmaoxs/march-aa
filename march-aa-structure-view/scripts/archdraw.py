"""archdraw —— 建筑制图用的 2D 图元层（mm 坐标、超采样、可导出 SVG）。

为什么单独一层：单件详图的成败不在渲染精度，而在**线宽层级 / 剖切填充 / 尺寸与引线**
这三件事。把它们收在一个地方，画一张新图就只剩「描点 + 排布」，不用再操心笔画。
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

# ── 纸与墨 ────────────────────────────────────────────────────────────────
PAPER = (250, 249, 246)
INK = (38, 42, 46)
INK2 = (86, 92, 98)
INK3 = (132, 138, 144)
ACCENT = (174, 52, 47)
GREY = (206, 203, 196)

# 线宽（pt）。1pt = 0.3528mm；在 210mm 宽的图上，1.8pt 是清晰可读的外轮廓
LW_OUT = 1.80      # 构件外轮廓、剖断
LW_MID = 0.90      # 构件分界、面交接
LW_FINE = 0.45     # 斗欹曲线、木纹、次要细节
LW_HID = 0.40      # 被遮挡（虚线）

MM_PER_PT = 0.3528

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'assets', 'fonts')
FONT_KAI = [os.path.join(FONT_DIR, 'LXGWWenKai-Regular.ttf'),
            os.path.expanduser('~/.cache/march-aa/LXGWWenKai-Regular.ttf')]
FONT_HEI = ['/System/Library/Fonts/STHeiti Medium.ttc',
            '/System/Library/Fonts/PingFang.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc']
FONT_NUM = ['/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']


def _font(paths, px):
    for p in paths:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, max(6, int(px)))
            except Exception:
                continue
    return ImageFont.load_default()


class Sheet(object):
    """一张图。坐标单位 mm，原点左上，y 向下（与纸面一致）。"""

    def __init__(self, w_mm=210.0, h_mm=280.0, dpi=580.0, ss=2):
        self.w_mm, self.h_mm = w_mm, h_mm
        self.k = dpi / 25.4                      # px per mm（逻辑像素）
        self.ss = ss
        self.W = int(round(w_mm * self.k))
        self.H = int(round(h_mm * self.k))
        self.img = Image.new('RGB', (self.W * ss, self.H * ss), PAPER)
        self.dr = ImageDraw.Draw(self.img)
        self._svg = []

    # ── 坐标 ────────────────────────────────────────────────────────────
    def px(self, p):
        return (p[0] * self.k * self.ss, p[1] * self.k * self.ss)

    def wpx(self, pt):
        return max(1, int(round(pt * MM_PER_PT * self.k * self.ss)))

    def mm(self, v):
        return v

    # ── 基本图元 ────────────────────────────────────────────────────────
    def line(self, p, q, w=LW_MID, col=INK, dash=None):
        a, b = self.px(p), self.px(q)
        if dash is None:
            self.dr.line([a, b], fill=col, width=self.wpx(w))
        else:
            for (x0, y0), (x1, y1) in self._dash_segments(a, b, dash[0] * self.k * self.ss,
                                                         dash[1] * self.k * self.ss):
                self.dr.line([(x0, y0), (x1, y1)], fill=col, width=self.wpx(w))
        self._svg.append(('line', p, q, w, col, dash))

    def poly(self, pts, close=True, w=LW_MID, col=INK, fill=None, dash=None):
        seq = list(pts) + ([pts[0]] if close and pts else [])
        for i in range(len(seq) - 1):
            self.line(seq[i], seq[i + 1], w=w, col=col, dash=dash)
        if fill is not None:
            self.dr.polygon([self.px(p) for p in pts], fill=fill)
            self._svg.append(('poly_fill', pts, fill))

    def cut(self, pts, w=LW_OUT, spacing_mm=1.1, col=INK):
        """剖到的断面：INK 实填 + 纸色细斜线，和「看得见的面」一眼分开。"""
        self.dr.polygon([self.px(p) for p in pts], fill=col)
        self._svg.append(('poly_fill', pts, col))
        for p, q in self._hatch_segments(pts, 45.0, spacing_mm):
            self.line(p, q, w=LW_FINE, col=PAPER)
        self.poly(pts, close=True, w=w, col=col)

    def hatch(self, pts, angle=45.0, spacing_mm=1.4, w=LW_FINE, col=INK2, cross=False):
        """在多边形内画斜线。剖切面靠它和空白面拉开层次。"""
        angs = [angle, angle + 90.0] if cross else [angle]
        for a in angs:
            for p, q in self._hatch_segments(pts, a, spacing_mm):
                self.line(p, q, w=w, col=col)

    # ── 标注 ────────────────────────────────────────────────────────────
    def dim(self, p, q, text, side=1.0, off=6.0, w=LW_FINE, fs=3.2, col=INK3):
        """尺寸线：两端细引出线 + 45° 斜杠端点 + 数字。side=±1 决定标在哪一侧。"""
        (x0, y0), (x1, y1) = p, q
        horiz = abs(x1 - x0) >= abs(y1 - y0)
        if horiz:
            yy = y0 + side * off
            a, b = (x0, yy), (x1, yy)
            self.line((x0, y0), (x0, yy + side * 2.0), w=w, col=col)
            self.line((x1, y1), (x1, yy + side * 2.0), w=w, col=col)
        else:
            xx = x0 + side * off
            a, b = (xx, y0), (xx, y1)
            self.line((x0, y0), (xx + side * 2.0, y0), w=w, col=col)
            self.line((x1, y1), (xx + side * 2.0, y1), w=w, col=col)
        self.line(a, b, w=w, col=col)
        for t in (a, b):
            self.line((t[0] - 0.9, t[1] + 0.9), (t[0] + 0.9, t[1] - 0.9), w=w, col=col)
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        kind = 'num' if all(ord(ch) < 128 for ch in text) else 'hei'
        if horiz:
            self.text(mid[0], mid[1] - 1.4, text, kind, fs, col, anchor='mb')
        else:
            self.text(mid[0] - 1.2, mid[1], text, kind, fs, col, anchor='rm')

    def axis(self, p, q, w=LW_FINE, col=INK3, dash=(7.0, 1.6, 1.2, 1.6)):
        """点划线：对称轴。分段拼出来。"""
        self.line(p, q, w=w, col=col, dash=(dash[0], dash[1]))
        self.line(p, q, w=w, col=col, dash=(dash[2], 3.0))

    def leader(self, anchor, number, target, side=1.0, r=2.6, fs=4.0,
               w=LW_FINE, col=ACCENT):
        """45° 折线引线 + 端头圆点 + 数字（数字落在 target 点）。"""
        ax, ay = anchor
        tx, ty = target
        elbow = (tx - side * abs(ty - ay) * 0.0 - side * 6.0, ay)
        self.line((ax, ay), elbow, w=w, col=col)
        self.line(elbow, (tx - side * (r + 0.8), ty), w=w, col=col)
        self.dot((ax, ay), 0.7, col)
        self.circle(target, r, fill=PAPER, outline=col, w=w)
        self.text(target[0], target[1], str(number), 'num', fs, col, anchor='mm')

    # ── 文字 / 比例尺 ───────────────────────────────────────────────────
    def text(self, x, y, s, kind='hei', size=4.0, col=INK, anchor='lm'):
        path = {'kai': FONT_KAI, 'hei': FONT_HEI, 'num': FONT_NUM}.get(kind, FONT_HEI)
        f = _font(path, size * self.k * self.ss)
        self.dr.text(self.px((x, y)), s, font=f, fill=col, anchor=anchor)

    def scalebar(self, x, y, total_mm, label, seg=10.0, h=1.6, fs=3.0):
        n = max(1, int(round(total_mm / seg)))
        for i in range(n):
            x0 = x + i * seg
            if i % 2 == 0:
                self.dr.rectangle([self.px((x0, y)), self.px((x0 + seg, y + h))], fill=INK)
            else:
                self.poly([(x0, y), (x0 + seg, y), (x0 + seg, y + h), (x0, y + h)],
                          w=LW_FINE, col=INK)
        self.text(x, y + h + 1.4, '0', 'num', fs, INK3, anchor='ma')
        self.text(x + n * seg, y + h + 1.4, label, 'num', fs, INK3, anchor='ma')

    def dot(self, p, r=0.7, col=INK):
        a = self.px(p)
        rr = r * self.k * self.ss
        self.dr.ellipse([a[0] - rr, a[1] - rr, a[0] + rr, a[1] + rr], fill=col)

    def circle(self, p, r, fill=None, outline=INK, w=LW_FINE):
        a = self.px(p)
        rr = r * self.k * self.ss
        self.dr.ellipse([a[0] - rr, a[1] - rr, a[0] + rr, a[1] + rr],
                        fill=fill, outline=outline, width=self.wpx(w))

    # ── 内部 ────────────────────────────────────────────────────────────
    @staticmethod
    def _dash_segments(a, b, on, off):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L <= 1e-6:
            return []
        ux, uy = dx / L, dy / L
        out, t = [], 0.0
        while t < L:
            e = min(t + on, L)
            out.append(((a[0] + ux * t, a[1] + uy * t), (a[0] + ux * e, a[1] + uy * e)))
            t = e + off
        return out

    def _hatch_segments(self, pts, angle_deg, spacing_mm):
        """扫描线求交：把多边形按 angle 方向的平行线切开，奇偶配对成线段。"""
        a = math.radians(angle_deg)
        ux, uy = math.cos(a), math.sin(a)          # 线方向
        nx, ny = -uy, ux                            # 法向
        proj = [p[0] * nx + p[1] * ny for p in pts]
        lo, hi = min(proj), max(proj)
        t0, t1 = min(p[0] * ux + p[1] * uy for p in pts), max(p[0] * ux + p[1] * uy for p in pts)
        out = []
        c = lo + spacing_mm * 0.5
        while c < hi:
            hits = []
            for i in range(len(pts)):
                p, q = pts[i], pts[(i + 1) % len(pts)]
                d0 = p[0] * nx + p[1] * ny - c
                d1 = q[0] * nx + q[1] * ny - c
                if (d0 > 0) != (d1 > 0):
                    t = d0 / (d0 - d1)
                    hits.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
            hits.sort(key=lambda h: h[0] * ux + h[1] * uy)
            for i in range(0, len(hits) - 1, 2):
                p, q = hits[i], hits[i + 1]
                out.append(((p[0], p[1]), (q[0], q[1])))
            c += spacing_mm
        return out

    # ── 输出 ────────────────────────────────────────────────────────────
    def save(self, path):
        im = self.img
        if self.ss != 1:
            im = im.resize((self.W, self.H), Image.LANCZOS)
        im.save(path)

    def to_svg(self, path):
        import io
        W, H = self.w_mm, self.h_mm
        buf = io.StringIO()
        buf.write('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
                  'viewBox="0 0 %.2f %.2f">\n' % (self.W, self.H, W, H))
        buf.write('<rect width="%.2f" height="%.2f" fill="#%02x%02x%02x"/>\n'
                  % (W, H, *PAPER))
        for rec in self._svg:
            if rec[0] == 'line':
                _, p, q, w, col, dash = rec
                ds = (' stroke-dasharray="%.2f %.2f"' % (dash[0], dash[1])) if dash else ''
                buf.write('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" '
                          'stroke="#%02x%02x%02x" stroke-width="%.2f"%s/>\n'
                          % (p[0], p[1], q[0], q[1], *col, w * MM_PER_PT, ds))
            elif rec[0] == 'poly_fill':
                _, pts, col = rec
                buf.write('<polygon points="%s" fill="#%02x%02x%02x"/>\n'
                          % (' '.join('%.2f,%.2f' % (x, y) for x, y in pts), *col))
        buf.write('</svg>\n')
        open(path, 'w', encoding='utf-8').write(buf.getvalue())
