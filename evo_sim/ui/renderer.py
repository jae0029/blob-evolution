# evo_sim/ui/renderer.py
from __future__ import annotations
import math, pygame
from collections import Counter
from ..sim.config import WORLD, TRAITS

# ---------- Colors / Theme ----------
BG_COLOR     = (14,16,20)
GRID_COLOR   = (35,40,48)
FOOD_COLOR   = (60,200,90)
HOME_COLOR   = (150,150,150)
DONE_COLOR   = (240,160,60)
DEAD_COLOR   = (220,80,80)
PANEL_BG     = (10,12,16)

# Top bar colors
TOPBAR_BG    = (24,26,32)
TOPBAR_LINE  = (54,58,66)

# Diet ring colors
DIET_COLORS = {
    "carnivore": (220, 60, 60),   # red
    "omnivore":  (60, 140, 240),  # blue
    "herbivore": (60, 200, 120),  # green
}

# Trait gradients (low -> high)
SENSE_LOW, SENSE_HIGH         = (60, 60, 180),  (240, 240, 100)  # deep purple -> yellow
AGGR_LOW,  AGGR_HIGH          = (50, 200, 180), (240, 60, 60)    # teal -> red
BRAVE_LOW, BRAVE_HIGH         = (130,130,130),  (90, 220, 120)   # gray -> green

INJURY_COLOR  = (255, 140, 0)  # orange overlay for injury
FOOD_DOT_COLOR= (240, 240, 240)

# ---------- Layout knobs (tweak here) ----------
DRAW_TOPBAR      = True     # set False if you draw a header bar in app.py
TOPBAR_HEIGHT    = 100       # header bar height
HUD_PAD_X        = 12       # HUD left padding
HUD_PAD_Y        = 10       # HUD top padding

PANEL_PADDING    = 12       # inner padding inside the right panel
TITLE_GAP        = 6        # space between title and subtitle
SECTION_GAP      = 10       # space between stacked sections
PLOT_SIDE_PAD    = 36       # extra left/right room around the plot box (for axes labels)
PLOT_TOP_PAD     = 8        # space above the plotted points box (inside content)
PLOT_BOTTOM_PAD  = 36       # room for x-axis labels/title under the plot box

def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1.0 else x)

def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def _col_lerp(c0, c1, t):
    t = _clamp01(t)
    return (int(_lerp(c0[0], c1[0], t)),
            int(_lerp(c0[1], c1[1], t)),
            int(_lerp(c0[2], c1[2], t)))

def _trait_color(val, vmin, vmax, low_col, high_col):
    if vmax <= vmin:
        return low_col
    t = (val - vmin) / (vmax - vmin)
    return _col_lerp(low_col, high_col, t)

class Renderer:
    def __init__(self, screen, world_rect: pygame.Rect, panel_rect: pygame.Rect, font_name="Menlo"):
        self.screen = screen

        # Render-time layout
        self.topbar_height = TOPBAR_HEIGHT

        # Store rects; apply top bar offset to world region
        self.panel_rect_outer = panel_rect
        self.panel_content = self.panel_rect_outer.inflate(-2*PANEL_PADDING, -2*PANEL_PADDING)

        self.world_rect = pygame.Rect(
            world_rect.x,
            world_rect.y + self.topbar_height,
            world_rect.w,
            max(0, world_rect.h - self.topbar_height)
        )

        self.font = pygame.font.SysFont(font_name, 14)
        self.bigfont = pygame.font.SysFont(font_name, 18, bold=True)

        # Modes
        self.panel_mode = "traits"  # "traits" | "phylo"
        self.glyph_mode = "rings"   # "rings" | "quads"
        self.show_legend = True     # toggled by 'L'

    # Public API: call when window resizes
    def resize(self, world_rect: pygame.Rect, panel_rect: pygame.Rect):
        """Update layout rects after a window resize."""
        self.panel_rect_outer = panel_rect
        self.panel_content = self.panel_rect_outer.inflate(-2*PANEL_PADDING, -2*PANEL_PADDING)
        self.world_rect = pygame.Rect(
            world_rect.x,
            world_rect.y + self.topbar_height,
            world_rect.w,
            max(0, world_rect.h - self.topbar_height)
        )

    # ---------- coordinate helpers ----------
    def world_to_screen(self, x, y):
        rx, ry, rw, rh = self.world_rect
        sx = rx + (x / WORLD.width) * rw
        sy = ry + (y / WORLD.height) * rh
        return int(sx), int(sy)

    # ---------- top bar ----------
    def _draw_topbar(self):
        """Draw a subtle header bar behind HUD text."""
        if not DRAW_TOPBAR:
            return
        scr = self.screen.get_rect()
        bar = pygame.Rect(0, 0, scr.w, self.topbar_height)
        pygame.draw.rect(self.screen, TOPBAR_BG, bar)
        # bottom divider line
        pygame.draw.line(self.screen, TOPBAR_LINE, (0, self.topbar_height), (scr.w, self.topbar_height), 1)

    # ---------- grid ----------
    def _draw_grid(self, spacing=20.0):
        rx, ry, rw, rh = self.world_rect
        for k in range(int(WORLD.width // spacing) + 1):
            wx = k * spacing
            sx, _ = self.world_to_screen(wx, 0)
            pygame.draw.line(self.screen, GRID_COLOR, (sx, ry), (sx, ry+rh), 1)
        for k in range(int(WORLD.height // spacing) + 1):
            wy = k * spacing
            _, sy = self.world_to_screen(0, wy)
            pygame.draw.line(self.screen, GRID_COLOR, (rx, sy), (rx+rw, sy), 1)
        pygame.draw.rect(self.screen, (70,75,85), self.world_rect, 2)

    # ---------- blob drawing ----------
    def _draw_blob(self, c):
        """
        Draw one creature with:
         - Diet ring (outer)
         - Trait glyphs inside (rings/quads): sense, aggression, bravery
         - Injury overlay
         - Food markers (1 or 2+)
        """
        sx, sy = self.world_to_screen(c.x, c.y)

        # radius by size (min 3 px)
        SCALE = 1.5              # global enlargement
        GROW  = 3.5              # growth factor
        EXP   = 1.4              # exponent

        base_r = max(3, int(SCALE * (3 + GROW * (c.size ** EXP))))

        # Base fill (alive/dead, done)
        if not c.alive:
            fill = DEAD_COLOR
        elif c.at_home(WORLD.home_margin) and c.eaten >= 1:
            r,g,b = (180,180,180)
            fill = (r,g,b)
        else:
            fill = (25, 28, 34)

        # Diet outer ring color
        diet = c.species.diet.lower()
        diet_col = DIET_COLORS.get(diet, (180,180,180))

        # Draw base fill
        pygame.draw.circle(self.screen, fill, (sx, sy), base_r)

        # Draw diet outer ring
        ring_thick = max(2, base_r // 4)
        pygame.draw.circle(self.screen, diet_col, (sx, sy), base_r, ring_thick)

        # Inner glyph area radius
        inner_r = base_r - ring_thick - 1
        if inner_r <= 1:
            inner_r = base_r - 1

        # --- Trait glyphs ---
        sense_col = _trait_color(c.sense, TRAITS.min_sense, TRAITS.max_sense, SENSE_LOW, SENSE_HIGH)
        aggr_col  = _trait_color(c.species.aggression, 0.0, 1.0, AGGR_LOW, AGGR_HIGH)
        brave_col = _trait_color(c.species.bravery,   0.0, 1.0, BRAVE_LOW, BRAVE_HIGH)

        if self.glyph_mode == "rings":
            # 3 concentric rings: sense (outer), aggression (mid), bravery (inner)
            band = max(2, inner_r // 4)
            pygame.draw.circle(self.screen, sense_col, (sx, sy), inner_r, band)
            pygame.draw.circle(self.screen, aggr_col,  (sx, sy), inner_r - (band + 1), band)
            pygame.draw.circle(self.screen, brave_col, (sx, sy), inner_r - (2*band + 2), band)
        else:
            # "quads" mode: three filled sector wedges (top, right, bottom)
            self._draw_sector(self.screen, (sx, sy), inner_r, -90-45, -90+45, sense_col)   # top (centered at -90)
            self._draw_sector(self.screen, (sx, sy), inner_r, 0-45,    0+45,  aggr_col)    # right (0 deg)
            self._draw_sector(self.screen, (sx, sy), inner_r, 90-45,   90+45, brave_col)   # bottom (90 deg)

        # --- Food markers ---
        if c.eaten >= 1:
            rdot = max(2, base_r // 5)
            # 12 o'clock
            dot_x = int(sx)
            dot_y = int(sy - inner_r + rdot + 1)
            pygame.draw.circle(self.screen, FOOD_DOT_COLOR, (dot_x, dot_y), rdot)
            if c.eaten >= 2:
                # 4 o'clock (~-60°)
                ang = math.radians(-60)
                dx = int(math.cos(ang) * (inner_r - rdot - 1))
                dy = int(math.sin(ang) * (inner_r - rdot - 1))
                pygame.draw.circle(self.screen, FOOD_DOT_COLOR, (sx + dx, sy + dy), rdot)

        # --- Injury overlay ---
        if getattr(c, "injury_days_left", 0) > 0 and c.alive:
            arm = inner_r
            pygame.draw.line(self.screen, INJURY_COLOR, (sx - arm, sy - arm), (sx + arm, sy + arm), 2)
            pygame.draw.line(self.screen, INJURY_COLOR, (sx - arm, sy + arm), (sx + arm, sy - arm), 2)

        # --- Home “done” halo (soft) ---
        if c.at_home(WORLD.home_margin) and c.eaten >= 1 and c.alive:
            pygame.draw.circle(self.screen, (140,200,220), (sx, sy), base_r + 2, 1)

    def _draw_sector(self, surface, center, radius, deg_start, deg_end, color, steps=12):
        """Approximate a filled circular sector with a polygon fan."""
        cx, cy = center
        a0 = math.radians(deg_start)
        a1 = math.radians(deg_end)
        if a1 < a0:
            a0, a1 = a1, a0
        pts = [(cx, cy)]
        for i in range(steps + 1):
            a = _lerp(a0, a1, i / steps)
            x = int(cx + math.cos(a) * radius)
            y = int(cy + math.sin(a) * radius)
            pts.append((x, y))
        pygame.draw.polygon(surface, color, pts)

    # ---------- legend box ----------
    def _draw_legend(self):
        """Compact legend in the lower-left of the world region."""
        pad = 8
        w, h = 230, 138
        lx = self.world_rect.x + pad
        ly = self.world_rect.bottom - h - pad

        rect = pygame.Rect(lx, ly, w, h)
        pygame.draw.rect(self.screen, (18,20,24), rect)
        pygame.draw.rect(self.screen, (80,85,95), rect, 1)

        y = ly + 6
        # Title
        self.screen.blit(self.bigfont.render("Legend", True, (230,230,235)), (lx+6, y))
        y += 22

        # Diet rows
        def diet_row(label, color):
            nonlocal y
            pygame.draw.rect(self.screen, color, (lx + 8, y + 3, 16, 10))
            self.screen.blit(self.font.render(label, True, (210,210,220)), (lx+30, y))
            y += 16

        diet_row("Carnivore (outer ring)", DIET_COLORS["carnivore"])
        diet_row("Omnivore  (outer ring)", DIET_COLORS["omnivore"])
        diet_row("Herbivore (outer ring)", DIET_COLORS["herbivore"])

        y += 2
        # Status rows
        self.screen.blit(self.font.render("● food dots (1 / 2+)", True, (210,210,220)), (lx+8, y)); y += 16
        self.screen.blit(self.font.render("× injury (orange)", True, (210,210,220)), (lx+8, y)); y += 16
        self.screen.blit(self.font.render("◌ done-at-home halo", True, (210,210,220)), (lx+8, y)); y += 16

        y += 2
        # Glyph mode
        self.screen.blit(self.font.render(f"Glyph: {self.glyph_mode} (G)", True, (210,210,220)), (lx+8, y))

    # ---------- world ----------
    def draw_world(self, live):
        # Draw top bar first so HUD sits on top of it later.
        self._draw_topbar()

        self._draw_grid()
        # food
        for fx, fy in live.food_positions():
            pygame.draw.circle(self.screen, FOOD_COLOR, self.world_to_screen(fx, fy), 3)
        # homes
        for c in live.population:
            pygame.draw.circle(self.screen, HOME_COLOR, self.world_to_screen(c.home[0], c.home[1]), 2)
        # creatures
        for c in live.population:
            self._draw_blob(c)
        # legend (toggleable)
        if self.show_legend:
            self._draw_legend()

    # ---------- Trait panel ----------
    def _project(self, sp, sz, se, mins, maxs):
        smin,zmin,emin = mins; smax,zmax,emax = maxs
        x = (sp - smin)/(smax-smin+1e-9) - 0.5
        y = (sz - zmin)/(zmax-zmin+1e-9) - 0.5
        z = (se - emin)/(emax-emin+1e-9) - 0.5
        ay, ax = 0.85, 0.60
        cx,sx = math.cos(ay), math.sin(ay)
        x2 = cx*x + sx*z
        z2 = -sx*x + cx*z
        cy,sy = math.cos(ax), math.sin(ax)
        y3 = cy*y - sy*z2
        z3 = sy*y + cy*z2
        persp = 1.0/(1.3 + z3)
        return x2*persp, y3*persp

    def draw_trait_panel(self, live):
        pr = self.panel_rect_outer
        pc = self.panel_content  # padded inner content area

        # Panel chrome
        pygame.draw.rect(self.screen, PANEL_BG, pr)
        pygame.draw.rect(self.screen, (70,75,85), pr, 2)

        # Title & subtitle inside padded content
        title_surf = self.bigfont.render("Trait Cloud (Speed, Size, Sense)", True, (220,220,230))
        subtitle_surf = self.font.render("Color = Species | x~Speed, y~Size (proj.)", True, (160,165,175))

        title_pos = (pc.x, pc.y)
        subtitle_pos = (pc.x, pc.y + title_surf.get_height() + TITLE_GAP)
        self.screen.blit(title_surf, title_pos)
        self.screen.blit(subtitle_surf, subtitle_pos)

        # Plot area below subtitle with extra inner padding for axes labels
        y0 = subtitle_pos[1] + subtitle_surf.get_height() + SECTION_GAP
        plot_left   = pc.x + PLOT_SIDE_PAD
        plot_top    = y0 + PLOT_TOP_PAD
        plot_right  = pc.right - PLOT_SIDE_PAD
        # Make the plot box height adaptive but leave room for legend and x-labels
        max_plot_h = pc.bottom - plot_top - (PLOT_BOTTOM_PAD + SECTION_GAP + 100)  # 100px min for legend
        plot_h = max(140, int(min(max_plot_h, pc.h * 0.55)))
        box = pygame.Rect(plot_left, plot_top, max(80, plot_right - plot_left), plot_h)

        pygame.draw.rect(self.screen, (25,30,36), box)

        pop = live.population
        if not pop:
            self.screen.blit(self.font.render("Extinct", True, (220,80,80)), (box.x + 10, box.y + 10))
            return

        mins = (TRAITS.min_speed, TRAITS.min_size, TRAITS.min_sense)
        maxs = (TRAITS.max_speed, TRAITS.max_size, TRAITS.max_sense)

        for c in pop:
            px, py = self._project(c.speed, c.size, c.sense, mins, maxs)
            sx = box.x + box.w * (0.5 + 0.75 * px)
            sy = box.y + box.h * (0.5 - 0.75 * py)
            r = 2 + int(2.0 * (c.size ** 0.8))
            diet = c.species.diet.lower()
            col = DIET_COLORS.get(diet, (180,180,180))
            pygame.draw.circle(self.screen, col, (int(sx), int(sy)), r)

        # axes
        self._draw_trait_axes(box, mins, maxs)

        # legend (species counts) under plot in remaining content area
        legend_top = box.bottom + SECTION_GAP
        legend = pygame.Rect(pc.x, legend_top, pc.w, max(60, pc.bottom - legend_top))
        pygame.draw.rect(self.screen, (25,30,36), legend)
        counts = Counter((c.species.name, c.species.diet.lower()) for c in pop)
        x, y = legend.x + 10, legend.y + 8
        for (name, diet), cnt in sorted(counts.items(), key=lambda kv: kv[0][0]):
            pygame.draw.rect(self.screen, DIET_COLORS.get(diet,(160,160,160)), (x, y+4, 16, 10))
            self.screen.blit(self.font.render(f"{name} ({diet}): {cnt}", True, (190,195,205)), (x+24, y))
            y += 18

    def _draw_trait_axes(self, box: pygame.Rect, mins, maxs):
        axis_color = (160,165,175)
        left = box.x; right = box.x + box.w
        bottom = box.y + box.h; top = box.y
        pygame.draw.line(self.screen, axis_color, (left, bottom), (right, bottom), 1)  # X
        pygame.draw.line(self.screen, axis_color, (left, bottom), (left, top), 1)      # Y

        # ticks
        def ticks(vmin, vmax):
            mid = 0.5*(vmin+vmax)
            return [(vmin, f"{vmin:.1f}"), (mid, f"{mid:.1f}"), (vmax, f"{vmax:.1f}")]
        # X (Speed)
        for xv, label in ticks(TRAITS.min_speed, TRAITS.max_speed):
            t = (xv - TRAITS.min_speed) / max(1e-9, (TRAITS.max_speed - TRAITS.min_speed))
            xpix = int(left + t * box.w)
            pygame.draw.line(self.screen, axis_color, (xpix, bottom), (xpix, bottom-6), 1)
            txt = self.font.render(label, True, axis_color)
            self.screen.blit(txt, (xpix - txt.get_width()//2, bottom + 4))
        # Y (Size)
        for yv, label in ticks(TRAITS.min_size, TRAITS.max_size):
            t = (yv - TRAITS.min_size) / max(1e-9, (TRAITS.max_size - TRAITS.min_size))
            ypix = int(bottom - t * box.h)
            pygame.draw.line(self.screen, axis_color, (left, ypix), (left+6, ypix), 1)
            txt = self.font.render(label, True, axis_color)
            self.screen.blit(txt, (left - txt.get_width() - 6, ypix - txt.get_height()//2))
        # axis titles
        x_title = self.font.render("Speed", True, (220,220,230))
        y_title = self.font.render("Size",  True, (220,220,230))
        self.screen.blit(x_title, (left + (box.w - x_title.get_width())//2, bottom + 22))
        y_surf = pygame.transform.rotate(y_title, 90)
        # destination as a single (x, y) tuple
        self.screen.blit(
            y_surf,
            (left - y_surf.get_width() - 12, top + (box.h - y_surf.get_height()) // 2)
        )

    # ---------- Phylogeny panel ----------
    def draw_phylogeny_panel(self, lineage, current_day: int):
        pr = self.panel_rect_outer
        pc = self.panel_content
        pygame.draw.rect(self.screen, PANEL_BG, pr)
        pygame.draw.rect(self.screen, (70,75,85), pr, 2)
        self.screen.blit(self.bigfont.render("Phylogenetic Tree (Species)", True, (220,220,230)), (pc.x, pc.y))
        self.screen.blit(self.font.render("Y = time (days), X = branch layout | press T to toggle",
                                          True, (160,165,175)),
                         (pc.x, pc.y + 24 + TITLE_GAP))
        # (Your existing phylogeny drawing code here; use pc as the padded content area)

    def draw_panel(self, live, lineage):
        if self.panel_mode == "traits":
            self.draw_trait_panel(live)
        else:
            self.draw_phylogeny_panel(lineage, current_day=live.day)

    def draw_hud(self, live, sim_speed, paused, rec_enabled, mutate_flags):
        lines = [
            f"Day: {live.day} Step: {live.step_in_day}/{int(WORLD.day_steps)}",
            f"Population: {len(live.population)}",
            f"Food/day: {int(WORLD.n_food)}  Sim speed: {sim_speed} steps/frame  {'PAUSED' if paused else ''}  {'REC ON' if rec_enabled else 'REC OFF'}",
            f"Mutations: speed[{mutate_flags[0]}] size[{mutate_flags[1]}] sense[{mutate_flags[2]}]   Panel: {self.panel_mode} (T)   Glyph: {self.glyph_mode} (G)   Legend: {'ON' if self.show_legend else 'OFF'} (L)",
            "Controls:",
            " Space Pause   R Reset   +/- Food   [ ] SimSpeed   1/2/3 toggle mut   M toggle all",
            " V toggle record   C clear record   S save NPZ   T toggle panel (Traits/Phylo)   G toggle glyph (rings/quads)   L toggle legend   Esc quit",
        ]
        x = HUD_PAD_X
        y = HUD_PAD_Y
        for i, s in enumerate(lines):
            col = (225,225,235) if i < 3 else (170,175,185)
            self.screen.blit(self.font.render(s, True, col), (x, y))
            y += 18
