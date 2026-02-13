# evo_sim/ui/renderer.py
from __future__ import annotations
import math, pygame
from collections import Counter
from ..sim.config import WORLD, TRAITS
from ..sim.lineage import LineageTracker

BG_COLOR   = (14,16,20)
GRID_COLOR = (35,40,48)
FOOD_COLOR = (60,200,90)
HOME_COLOR = (150,150,150)
DONE_COLOR = (240,160,60)
DEAD_COLOR = (220,80,80)
PANEL_BG   = (10,12,16)

class Renderer:
    def __init__(self, screen, world_rect: pygame.Rect, panel_rect: pygame.Rect, font_name="Menlo"):
        self.screen = screen
        self.world_rect = world_rect
        self.panel_rect = panel_rect
        self.font = pygame.font.SysFont(font_name, 14)
        self.bigfont = pygame.font.SysFont(font_name, 18, bold=True)
        self.panel_mode = "traits"  # "traits" | "phylo"

    def world_to_screen(self, x, y):
        rx, ry, rw, rh = self.world_rect
        sx = rx + (x / WORLD.width) * rw
        sy = ry + (y / WORLD.height) * rh
        return int(sx), int(sy)

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

    def draw_world(self, live):
        self._draw_grid()
        # food
        for fx, fy in live.food_positions():
            pygame.draw.circle(self.screen, FOOD_COLOR, self.world_to_screen(fx, fy), 3)
        # homes
        for c in live.population:
            pygame.draw.circle(self.screen, HOME_COLOR, self.world_to_screen(c.home[0], c.home[1]), 2)
        # creatures
        for c in live.population:
            if not c.alive:
                col = DEAD_COLOR
            elif c.at_home(WORLD.home_margin) and c.eaten >= 1:
                r,g,b = c.species.color
                col = (int((r+DONE_COLOR[0])//2), int((g+DONE_COLOR[1])//2), int((b+DONE_COLOR[2])//2))
            else:
                col = c.species.color
            r = max(2, int(3 + 3.0 * (c.size ** 1.3)))
            pygame.draw.circle(self.screen, col, self.world_to_screen(c.x, c.y), r)

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

    def _draw_trait_axes(self, box: pygame.Rect, mins, maxs):
        """
        Draw X and Y axes with ticks and labels inside the given plotting box.
        X = Speed, Y = Size. Color = Species (legend elsewhere).
        """
        # axis lines
        axis_color = (160,165,175)
        # margins inside box
        left = box.x; right = box.x + box.w
        bottom = box.y + box.h; top = box.y
        # draw axes (bottom and left)
        pygame.draw.line(self.screen, axis_color, (left, bottom), (right, bottom), 1)  # X axis
        pygame.draw.line(self.screen, axis_color, (left, bottom), (left, top), 1)      # Y axis

        # ticks and labels
        # Using true ranges from TRAITS to ensure accuracy
        smin, zmin, _ = mins
        smax, zmax, _ = maxs

        # choose tick positions: min, mid, max
        def ticks(vmin, vmax):
            mid = 0.5*(vmin+vmax)
            return [(vmin, f"{vmin:.1f}"), (mid, f"{mid:.1f}"), (vmax, f"{vmax:.1f}")]

        # X ticks (Speed)
        xticks = ticks(TRAITS.min_speed, TRAITS.max_speed)
        for xv, label in xticks:
            t = (xv - TRAITS.min_speed) / max(1e-9, (TRAITS.max_speed - TRAITS.min_speed))
            xpix = int(left + t * box.w)
            pygame.draw.line(self.screen, axis_color, (xpix, bottom), (xpix, bottom-6), 1)
            txt = self.font.render(label, True, axis_color)
            self.screen.blit(txt, (xpix - txt.get_width()//2, bottom + 4))

        # Y ticks (Size)
        yticks = ticks(TRAITS.min_size, TRAITS.max_size)
        for yv, label in yticks:
            t = (yv - TRAITS.min_size) / max(1e-9, (TRAITS.max_size - TRAITS.min_size))
            ypix = int(bottom - t * box.h)
            pygame.draw.line(self.screen, axis_color, (left, ypix), (left+6, ypix), 1)
            txt = self.font.render(label, True, axis_color)
            self.screen.blit(txt, (left - txt.get_width() - 6, ypix - txt.get_height()//2))

        # axis titles
        x_title = self.font.render("Speed", True, (220,220,230))
        y_title = self.font.render("Size",  True, (220,220,230))
        self.screen.blit(x_title, (left + (box.w - x_title.get_width())//2, bottom + 22))
        # rotate Y label (simple vertical text using surfaces)
        y_surf = pygame.transform.rotate(y_title, 90)
        self.screen.blit(y_surf, (left - y_surf.get_width() - 12, top + (box.h - y_surf.get_height())//2))

    def draw_trait_panel(self, live):
        pr = self.panel_rect
        pygame.draw.rect(self.screen, PANEL_BG, pr)
        pygame.draw.rect(self.screen, (70,75,85), pr, 2)
        self.screen.blit(self.bigfont.render("Trait Cloud (Speed, Size, Sense)", True, (220,220,230)), (pr.x+10, pr.y+10))
        self.screen.blit(self.font.render("Color = Species | x~Speed, y~Size (proj.)", True, (160,165,175)), (pr.x+10, pr.y+36))
        box = pygame.Rect(pr.x+56, pr.y+60, pr.w - 68, pr.h - 180)  # widened left pad for y-axis labels
        pygame.draw.rect(self.screen, (25,30,36), box)

        pop = live.population
        if not pop:
            self.screen.blit(self.font.render("Extinct", True, (220,80,80)), (box.x + 10, box.y + 10))
            return

        # Use TRAITS bounds for axes; projection is the same as before
        mins = (TRAITS.min_speed, TRAITS.min_size, TRAITS.min_sense)
        maxs = (TRAITS.max_speed, TRAITS.max_size, TRAITS.max_sense)

        # points
        for c in pop:
            px, py = self._project(c.speed, c.size, c.sense, mins, maxs)
            sx = box.x + box.w * (0.5 + 0.75 * px)
            sy = box.y + box.h * (0.5 - 0.75 * py)
            r = 2 + int(2.0 * (c.size ** 0.8))
            pygame.draw.circle(self.screen, c.species.color, (int(sx), int(sy)), r)

        # axes on top of the plot
        self._draw_trait_axes(box, mins, maxs)

        # species legend under the plot
        legend = pygame.Rect(pr.x+12, box.bottom+8, pr.w-24, pr.h - (box.bottom - pr.y) - 20)
        pygame.draw.rect(self.screen, (25,30,36), legend)
        counts = Counter((c.species.name, c.species.color) for c in pop)
        x, y = legend.x + 10, legend.y + 8
        for (name, col), cnt in sorted(counts.items(), key=lambda kv: kv[0][0]):
            pygame.draw.rect(self.screen, col, (x, y+4, 16, 10))
            self.screen.blit(self.font.render(f"{name}: {cnt}", True, (190,195,205)), (x+24, y))
            y += 18

    # ---------- Phylogeny panel (IMPLEMENTED) ----------
    def draw_phylogeny_panel(self, lineage: LineageTracker, current_day: int):
        pr = self.panel_rect
        pygame.draw.rect(self.screen, PANEL_BG, pr)
        pygame.draw.rect(self.screen, (70,75,85), pr, 2)

        title = "Phylogenetic Tree (Species)"
        self.screen.blit(self.bigfont.render(title, True, (220,220,230)), (pr.x+10, pr.y+10))
        self.screen.blit(self.font.render("Y = time (days), X = branch layout | press T to toggle", True, (160,165,175)), (pr.x+10, pr.y+36))

        box = pygame.Rect(pr.x+12, pr.y+60, pr.w-24, pr.h-80)
        pygame.draw.rect(self.screen, (25,30,36), box)

        if (not lineage) or (not lineage.has_data()):
            self.screen.blit(self.font.render("No lineage data yet", True, (190,195,205)), (box.x+10, box.y+10))
            return

        # Stable columns by creation order
        cols = lineage.compute_layout_columns()
        segs = lineage.segments(current_day)

        # Plot area margins
        left, top, w, h = box.x+10, box.y+10, box.w-20, box.h-20

        # Helpers to map to pixels
        col_values = sorted(set(cols.values()))
        def x_of(species_id: int) -> int:
            col_idx = cols.get(species_id, 0)
            if len(col_values) <= 1:
                return left + w // 2
            t = (col_idx - min(col_values)) / max(1, (max(col_values) - min(col_values)))
            return int(left + t * w)
        def y_of(day: int) -> int:
            if current_day <= 1:
                return top + h
            # day 1 near top, current_day at bottom
            return int(top + h - (day / current_day) * h)

        # Connectors (parent -> child at child's birth day)
        for sid, y0, _, parent_id, _color in segs:
            if parent_id is not None and parent_id != -1:
                yb = y_of(y0)
                xp, xc = x_of(parent_id), x_of(sid)
                pygame.draw.line(self.screen, (180,180,190), (xp, yb), (xc, yb), 1)

        # Vertical lifelines
        for sid, y0, y1, _parent_id, color in segs:
            x  = x_of(sid)
            yb = y_of(y0)
            ye = y_of(y1)
            pygame.draw.line(self.screen, color, (x, yb), (x, ye), 3)

        # Simple Y axis labels
        self.screen.blit(self.font.render("Day 1", True, (160,165,175)), (box.x+4, y_of(1)-8))
        self.screen.blit(self.font.render(f"Day {current_day}", True, (160,165,175)), (box.x+4, y_of(current_day)-8))

    def draw_panel(self, live, lineage: LineageTracker):
        if self.panel_mode == "traits":
            self.draw_trait_panel(live)
        else:
            self.draw_phylogeny_panel(lineage, current_day=live.day)

    def draw_hud(self, live, sim_speed, paused, rec_enabled, mutate_flags):
        lines = [
            f"Day: {live.day} Step: {live.step_in_day}/{int(WORLD.day_steps)}",
            f"Population: {len(live.population)}",
            f"Food/day: {int(WORLD.n_food)}  Sim speed: {sim_speed} steps/frame  {'PAUSED' if paused else ''}  {'REC ON' if rec_enabled else 'REC OFF'}",
            f"Mutations: speed[{mutate_flags[0]}] size[{mutate_flags[1]}] sense[{mutate_flags[2]}]   Panel: {self.panel_mode} (press T)",
            "Controls:",
            " Space Pause   R Reset   +/- Food   [ ] SimSpeed   1/2/3 toggle mut   M toggle all",
            " V toggle record   C clear record   S save NPZ   T toggle panel (Traits/Phylo)   Esc quit",
        ]
        y = 8
        for i, s in enumerate(lines):
            col = (225,225,235) if i < 3 else (170,175,185)
            self.screen.blit(self.font.render(s, True, col), (10, y))
            y += 18


