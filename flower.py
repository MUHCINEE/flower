"""
RORU - Blooming Flower
======================
An animated, glowing flower that blooms from a tiny bud on a dark
gradient background, with the name "RORU" glowing beneath it.

INSTALL
    pip install pygame

RUN
    python blooming_flower.py

CONTROLS
    SPACE / R  -> replay the bloom animation
    ESC / Q    -> quit
"""

import math
import random
import sys

import pygame

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
WIDTH, HEIGHT = 900, 860
FPS = 60
CENTER = (WIDTH // 2, 340)          # flower centre
TEXT_Y = 735                         # vertical centre of the "RORU" text
BLOOM_DURATION = 6.0                 # seconds for the full bloom
NAME = "RORU"

# Each layer: petal count, length, half-width, base colour, tip colour,
# start delay (0..1 of the bloom), twist (radians) and angular offset.
# Layers are drawn back-to-front (outer first).
LAYERS = [
    dict(n=10, length=255, width=64, base=(45, 0, 95),   tip=(255, 45, 170),
         delay=0.00, twist=1.1,  offset=0.0),
    dict(n=9,  length=205, width=56, base=(110, 0, 90),  tip=(255, 60, 120),
         delay=0.10, twist=-1.0, offset=0.18),
    dict(n=8,  length=150, width=46, base=(190, 15, 70), tip=(255, 120, 95),
         delay=0.20, twist=0.9,  offset=0.40),
    dict(n=6,  length=100, width=36, base=(230, 60, 60), tip=(255, 205, 130),
         delay=0.30, twist=-0.8, offset=0.10),
    dict(n=5,  length=58,  width=26, base=(255, 130, 70), tip=(255, 240, 170),
         delay=0.40, twist=0.7,  offset=0.60),
]

SLICES = 9   # number of colour slices per petal (gradient smoothness)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def ease_out_back(x, s=1.1):
    """Smooth ease-out with a tiny overshoot (gives a soft 'pop' to the bloom)."""
    x = clamp(x) - 1.0
    return 1.0 + x * x * ((s + 1.0) * x + s)


def smoothstep(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


# --------------------------------------------------------------------------
# Pre-rendered assets (built once so the main loop stays fast)
# --------------------------------------------------------------------------
def make_background():
    """Vertical dark gradient with a soft purple vignette glow behind the flower."""
    bg = pygame.Surface((WIDTH, HEIGHT))
    top, bottom = (6, 2, 16), (14, 4, 30)
    for y in range(HEIGHT):
        bg.fill(lerp_color(top, bottom, y / HEIGHT), (0, y, WIDTH, 1))

    # Soft radial haze centred on the flower
    haze = radial_glow(520, (70, 10, 110), max_alpha=90, power=2.2)
    bg.blit(haze, haze.get_rect(center=CENTER))

    # A few faint static stars
    rng = random.Random(7)
    for _ in range(90):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        b = rng.randint(40, 110)
        bg.set_at((x, y), (b, b - 10, b + 40 if b + 40 < 255 else 255))
    return bg.convert()


def radial_glow(size, color, max_alpha=255, power=2.0):
    """A square surface with a radial alpha falloff, used for all glow effects."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    r = size / 2
    steps = int(r)
    for i in range(steps, 0, -1):
        t = i / steps                        # 1 at the edge, 0 at the centre
        a = int(max_alpha * (1 - t) ** power)
        pygame.draw.circle(surf, (*color, a), (int(r), int(r)), i)
    return surf


def make_unit_petal(steps=SLICES):
    """
    Petal outline in unit coordinates (length 1, half-width 1).
    Returns a list of (t, left_point, right_point) along the petal axis.
    """
    pts = []
    for k in range(steps + 1):
        t = k / steps
        # Rounded-teardrop profile: narrow base, fullest near 45%, pointed tip
        w = math.sin(math.pi * (t ** 0.72)) ** 0.85
        # Slight curl so the tip bends gracefully
        curl = 0.10 * t * t
        pts.append((t, (t, -w + curl), (t, w + curl)))
    return pts


def make_title(font_size=84):
    """Pre-render 'RORU' with letter-spacing, a gradient fill and a soft glow."""
    font = None
    for name in ("montserrat", "poppins", "arialblack", "segoeui", "helveticaneue", "arial"):
        path = pygame.font.match_font(name, bold=True)
        if path:
            font = pygame.font.Font(path, font_size)
            font.set_bold(True)
            break
    if font is None:
        font = pygame.font.SysFont(None, font_size, bold=True)

    spacing = 26
    glyphs = [font.render(ch, True, (255, 255, 255)) for ch in NAME]
    total_w = sum(g.get_width() for g in glyphs) + spacing * (len(glyphs) - 1)
    h = glyphs[0].get_height()

    pad = 90
    canvas = pygame.Surface((total_w + pad * 2, h + pad * 2), pygame.SRCALPHA)

    # Draw letters, tinting each with a vertical pink -> soft-white gradient
    x = pad
    for g in glyphs:
        tinted = g.copy()
        grad = pygame.Surface(g.get_size(), pygame.SRCALPHA)
        for yy in range(g.get_height()):
            c = lerp_color((255, 245, 252), (255, 120, 205), yy / g.get_height())
            pygame.draw.line(grad, (*[int(v) for v in c], 255), (0, yy), (g.get_width(), yy))
        tinted.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        canvas.blit(tinted, (x, pad))
        x += g.get_width() + spacing

    # Glow: shrink + enlarge the text to blur it, then tint it magenta
    w, hh = canvas.get_size()
    glow = pygame.transform.smoothscale(canvas, (w // 7, hh // 7))
    glow = pygame.transform.smoothscale(glow, (w, hh))
    tint = pygame.Surface((w, hh), pygame.SRCALPHA)
    tint.fill((255, 40, 190, 255))
    glow.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    final = pygame.Surface((w, hh), pygame.SRCALPHA)
    for _ in range(3):                       # stack for a stronger halo
        final.blit(glow, (0, 0))
    final.blit(canvas, (0, 0))
    return final.convert_alpha()


# --------------------------------------------------------------------------
# Sparkle particles
# --------------------------------------------------------------------------
class Sparkle:
    def __init__(self):
        self.reset()

    def reset(self):
        ang = random.uniform(0, math.tau)
        dist = random.uniform(20, 120)
        self.x = CENTER[0] + math.cos(ang) * dist
        self.y = CENTER[1] + math.sin(ang) * dist
        speed = random.uniform(10, 38)
        self.vx = math.cos(ang) * speed * 0.6
        self.vy = math.sin(ang) * speed * 0.6 - random.uniform(8, 24)  # drift upward
        self.life = 0.0
        self.max_life = random.uniform(2.5, 5.5)
        self.size = random.choice((10, 14, 18, 24))
        self.color = random.choice(((255, 90, 190), (255, 150, 90), (190, 110, 255), (255, 220, 170)))

    def update(self, dt):
        self.life += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.life >= self.max_life:
            self.reset()

    @property
    def intensity(self):
        t = self.life / self.max_life
        return math.sin(math.pi * t)         # fade in, fade out


# --------------------------------------------------------------------------
# Flower rendering
# --------------------------------------------------------------------------
UNIT_PETAL = make_unit_petal()


def draw_petal(surface, cx, cy, angle, length, half_w, base, tip, shade):
    """Draw one petal as a stack of gradient slices plus a soft highlight edge."""
    ca, sa = math.cos(angle), math.sin(angle)

    def tr(p):
        # unit coords -> screen (scale, rotate, translate)
        lx, ly = p[0] * length, p[1] * half_w
        return (cx + lx * ca - ly * sa, cy + lx * sa + ly * ca)

    left = [tr(l) for _, l, _ in UNIT_PETAL]
    right = [tr(r) for _, _, r in UNIT_PETAL]

    for k in range(SLICES):
        t = (k + 0.5) / SLICES
        col = lerp_color(base, tip, t ** 0.9)
        col = tuple(int(clamp(c * shade, 0, 255)) for c in col)
        poly = [left[k], left[k + 1], right[k + 1], right[k]]
        pygame.draw.polygon(surface, col, poly)

    outline = left + right[::-1]
    edge = tuple(int(clamp(c * shade * 1.25 + 25, 0, 255)) for c in tip)
    pygame.draw.aalines(surface, edge, True, outline)

    # Soft centre vein
    vein = tuple(int(clamp(c * 0.8, 0, 255)) for c in base)
    pygame.draw.aaline(surface, vein, tr((0.05, 0)), tr((0.75, 0.05)))


def draw_flower(surface, t, petal_shades):
    """Render the whole flower for animation time t (seconds)."""
    p = clamp(t / BLOOM_DURATION)                       # overall progress 0..1
    cx, cy = CENTER

    # Whole-flower scale: starts as a small bud and grows
    grow = ease_out_back(clamp(p * 1.1), 0.9)
    scale = 0.30 + 0.70 * grow

    # Gentle "breathing" and slow rotation once the flower is open
    settled = smoothstep((p - 0.85) / 0.15)
    scale *= 1.0 + 0.018 * math.sin(t * 1.7) * settled
    spin = t * 0.06

    for li, layer in enumerate(LAYERS):
        # Per-layer local progress (outer layers open first)
        lp = clamp((p - layer["delay"]) / (1.0 - layer["delay"] * 0.9))
        e = ease_out_back(lp, 1.0)
        e = max(e, 0.0)

        length = layer["length"] * scale * (0.18 + 0.82 * e)
        half_w = layer["width"] * scale * (1.35 - 0.35 * e)
        twist = layer["twist"] * (1.0 - clamp(e))        # petals unwind as they open

        n = layer["n"]
        for i in range(n):
            ang = (i / n) * math.tau + layer["offset"] + twist + spin * (1 if li % 2 == 0 else -1)
            shade = petal_shades[li][i]
            draw_petal(surface, cx, cy, ang, length, half_w,
                       layer["base"], layer["tip"], shade)


def draw_core(surface, t, glow_core):
    """Glowing centre with golden stamens that appear late in the bloom."""
    p = clamp(t / BLOOM_DURATION)
    cx, cy = CENTER
    k = smoothstep((p - 0.45) / 0.45)
    if k <= 0:
        return

    # Warm glow in the heart of the flower
    g = glow_core.copy()
    g.set_alpha(int(255 * k))
    surface.blit(g, g.get_rect(center=CENTER))

    # Stamens
    count = 22
    for i in range(count):
        a = (i / count) * math.tau + t * 0.15
        r = (16 + 10 * math.sin(i * 2.3 + t * 1.2)) * (0.5 + 0.5 * k) + 6
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        pygame.draw.circle(surface, (255, 225, 140), (int(x), int(y)), 3)
        pygame.draw.circle(surface, (255, 255, 230), (int(x), int(y)), 1)

    pygame.draw.circle(surface, (255, 190, 90), CENTER, int(9 * k) + 1)
    pygame.draw.circle(surface, (255, 245, 200), CENTER, int(4 * k) + 1)


# --------------------------------------------------------------------------
# Main program
# --------------------------------------------------------------------------
def main(max_frames=None, snapshot=None):
    pygame.init()
    pygame.display.set_caption("RORU - Blooming Flower")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # --- Pre-rendered assets ---
    background = make_background()
    big_glow = radial_glow(720, (200, 30, 190), max_alpha=170, power=2.4)
    glow_cache = {}                                        # size -> scaled glow
    glow_core = radial_glow(130, (255, 170, 80), max_alpha=230, power=1.6)
    sparkle_glows = {c: radial_glow(26, c, 255, 2.0) for c in
                     ((255, 90, 190), (255, 150, 90), (190, 110, 255), (255, 220, 170))}
    title = make_title()
    title_rect = title.get_rect(center=(WIDTH // 2, TEXT_Y))

    # Slight random brightness per petal for a natural look
    rng = random.Random(3)
    petal_shades = [[rng.uniform(0.88, 1.12) for _ in range(l["n"])] for l in LAYERS]

    sparkles = [Sparkle() for _ in range(36)]
    for s in sparkles:                                     # de-sync their lifetimes
        s.life = random.uniform(0, s.max_life)

    t = 0.0
    frame = 0
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        if max_frames is not None:
            dt = 1.0 / FPS                                 # deterministic when testing
        t += dt
        frame += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key in (pygame.K_SPACE, pygame.K_r):
                    t = 0.0                                # replay the bloom

        p = clamp(t / BLOOM_DURATION)

        # --- Draw ---
        screen.blit(background, (0, 0))

        # Large pulsing halo behind the flower (grows with the bloom)
        halo_size = int(260 + 460 * smoothstep(p * 1.2))
        halo_size = (halo_size // 16) * 16 or 16           # quantise for caching
        if halo_size not in glow_cache:
            glow_cache[halo_size] = pygame.transform.smoothscale(big_glow, (halo_size, halo_size))
        halo = glow_cache[halo_size]
        pulse = 0.85 + 0.15 * math.sin(t * 2.0)
        halo.set_alpha(int(255 * clamp(0.25 + p) * pulse))
        screen.blit(halo, halo.get_rect(center=CENTER))

        draw_flower(screen, t, petal_shades)
        draw_core(screen, t, glow_core)

        # Floating sparkles (only once the flower starts to open)
        if p > 0.3:
            for s in sparkles:
                s.update(dt)
                g = sparkle_glows[s.color]
                g.set_alpha(int(255 * s.intensity * smoothstep((p - 0.3) / 0.4)))
                screen.blit(g, g.get_rect(center=(int(s.x), int(s.y))))

        # Title fades in during the second half of the bloom
        title_alpha = smoothstep((p - 0.55) / 0.35)
        if title_alpha > 0:
            title.set_alpha(int(255 * title_alpha))
            # a tiny upward float as it appears
            offset = int((1 - title_alpha) * 18)
            screen.blit(title, title_rect.move(0, offset))

        pygame.display.flip()

        if max_frames is not None and frame >= max_frames:
            if snapshot:
                pygame.image.save(screen, snapshot)
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()