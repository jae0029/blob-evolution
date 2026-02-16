from __future__ import annotations
import pygame
from evo_sim.ui.renderer import Renderer
from evo_sim.ui.csv_writer import DailyCsvLogger
from evo_sim.sim.config import WORLD, SIM
from evo_sim.sim.models import Creature, Species
from ns_sim_2_0.sim.live_ns import LiveSimNS

WIDTH, HEIGHT = 1200, 720

# ------------------------------
# UI layout metrics (tweak these)
# ------------------------------
OUTER_MARGIN = 16        # space from window edges
TOPBAR_HEIGHT = 140       # reserved header/HUD area height (must match renderer's topbar_height for a consistent look)
BOTTOM_MARGIN = 24       # bottom breathing room
PANEL_GUTTER = 12        # gap between world and side panel
PANEL_WIDTH_FRAC = 0.33  # right panel width fraction of total
PANEL_PADDING = 12       # inner padding inside the panel for plots/text (must match renderer's PANEL_PADDING for a consistent look)


def _compute_layout(w: int, h: int):
    """Return (world_rect, panel_outer_rect) using current window size."""
    panel_w = int(w * PANEL_WIDTH_FRAC)

    world_rect = pygame.Rect(
        OUTER_MARGIN,
        OUTER_MARGIN + TOPBAR_HEIGHT,
        w - (OUTER_MARGIN * 2) - panel_w - PANEL_GUTTER,
        h - OUTER_MARGIN - BOTTOM_MARGIN - TOPBAR_HEIGHT
    )



    panel_outer = pygame.Rect(
        w - OUTER_MARGIN - panel_w,
        OUTER_MARGIN,
        panel_w,
        h - OUTER_MARGIN - BOTTOM_MARGIN
    )

    # NOTE: pass the OUTER (not padded) panel rect to Renderer; it applies inner padding.
    return world_rect, panel_outer


def run_ui():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Natural Selection UI")
    clock = pygame.time.Clock()

    world_rect, panel_outer = _compute_layout(WIDTH, HEIGHT)
    renderer = Renderer(screen, world_rect, panel_outer)

    # ---- Sim setup (unchanged) ----
    sp = Species(1, "NS", (120, 160, 240), aggression=0.0, bravery=0.0, metabolism=1.0, diet="omnivore")
    init_pop = [
        Creature(id=i + 1, species=sp, speed=2.2, size=1.0, sense=30.0,
                 x=0.0, y=0.0, home=(0.0, 0.0), energy=0.0)
        for i in range(40)
    ]

    live = LiveSimNS(init_pop, seed=SIM.seed)

    logger = DailyCsvLogger(overall_path="runs_ns/ui_daily.csv",
                            species_path="runs_ns/ui_species_daily.csv",
                            enable_species=True)

    
    sim_speed = 1
    paused = False
    rec_enabled = False

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            # --- Window resize handling (both events for cross-platform robustness) ---
            elif e.type in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED):
                # Always query actual window size instead of trusting event
                w, h = pygame.display.get_window_size()

                screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)

                world_rect, panel_outer = _compute_layout(w, h)
                renderer.screen = screen
                renderer.resize(world_rect, panel_outer)


            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    WORLD.n_food = min(1000, int(WORLD.n_food) + 5)
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    WORLD.n_food = max(0, int(WORLD.n_food) - 5)
                elif e.key == pygame.K_t:
                    renderer.panel_mode = "phylo" if renderer.panel_mode == "traits" else "traits"
                elif e.key == pygame.K_g:
                    renderer.glyph_mode = "quads" if renderer.glyph_mode == "rings" else "rings"
                elif e.key == pygame.K_l:  # <-- NEW: toggle legend
                    renderer.show_legend = not renderer.show_legend
                elif e.key == pygame.K_RIGHT or e.key == pygame.K_RIGHTBRACKET:
                    sim_speed = min(50, sim_speed + 1)
                elif e.key == pygame.K_LEFT or e.key == pygame.K_LEFTBRACKET:
                    sim_speed = max(1, sim_speed - 1)
                elif e.key == pygame.K_r:
                    # recreate species and initial population
                    sp = Species(1, "NS", (120, 160, 240),
                                aggression=0.0, bravery=0.0,
                                metabolism=1.0, diet="omnivore")

                    init_pop = [
                        Creature(id=i + 1, species=sp,
                                speed=2.2, size=1.0, sense=30.0,
                                x=0.0, y=0.0, home=(0.0, 0.0),
                                energy=0.0)
                        for i in range(40)
                    ]

                    live = LiveSimNS(init_pop, seed=SIM.seed)


        if not paused:
            new_day_started = False
            for _ in range(sim_speed):
                if live.step():
                    new_day_started = True
                    break
            if new_day_started:
                logger.append_day(day=live.day - 1,
                                  pop=live.last_population_snapshot or live.population,
                                  food_per_day=int(WORLD.n_food),
                                  day_steps=int(WORLD.day_steps),
                                  notes="NS mode")

        screen.fill((14,16,20))
        renderer.draw_world(live)
        renderer.draw_panel(live, lineage=None)
        renderer.draw_hud(
            live, sim_speed, paused, rec_enabled,
            (live.mutate_speed, live.mutate_size, live.mutate_sense)
        )
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0