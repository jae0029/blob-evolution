
from __future__ import annotations
import pygame
from evo_sim.ui.renderer import Renderer
from evo_sim.ui.csv_writer import DailyCsvLogger
from evo_sim.sim.config import WORLD, SIM
from evo_sim.sim.models import Creature, Species
from ns_sim.sim.live_ns import LiveSimNS

WIDTH, HEIGHT = 1200, 720

def run_ui():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Natural Selection UI")
    clock = pygame.time.Clock()

    panel_w = int(WIDTH * 0.33)
    world_rect = pygame.Rect(8, 56, WIDTH - panel_w - 16, HEIGHT - 64)
    panel_rect = pygame.Rect(WIDTH - panel_w - 8, 56, panel_w, HEIGHT - 64)

    renderer = Renderer(screen, world_rect, panel_rect)

    sp = Species(1, "NS", (120,160,240), aggression=0.0, bravery=0.0, metabolism=1.0, diet="omnivore")
    init_pop = [Creature(id=i+1, species=sp, speed=2.2, size=1.0, sense=30.0,
                         x=0.0,y=0.0, home=(0.0,0.0), energy=0.0) for i in range(40)]

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
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_t:
                    renderer.panel_mode = "phylo" if renderer.panel_mode == "traits" else "traits"
                elif e.key == pygame.K_g:
                    renderer.glyph_mode = "quads" if renderer.glyph_mode == "rings" else "rings"
                elif e.key == pygame.K_RIGHT or e.key == pygame.K_RIGHTBRACKET:
                    sim_speed = min(50, sim_speed + 1)
                elif e.key == pygame.K_LEFT or e.key == pygame.K_LEFTBRACKET:
                    sim_speed = max(1, sim_speed - 1)

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
        renderer.draw_hud(live, sim_speed, paused, rec_enabled, (live.mutate_speed, live.mutate_size, live.mutate_sense))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
