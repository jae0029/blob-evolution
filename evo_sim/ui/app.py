# evo_sim/ui/app.py
from __future__ import annotations
import pygame, random
from .renderer import Renderer, BG_COLOR
from .recorder import Recorder
from ..sim.live import LiveSim
from ..sim.models import Creature, Species
from ..sim.rng import RNG
from ..sim.config import WORLD, SIM
from ..sim.lineage import LineageTracker
from .csv_writer import DailyCsvLogger
    
def _seed_species():
    return [
        Species(id=1, name="Omnivore",   color=(70,140,240), aggression=0.35, bravery=0.55, metabolism=1.00, diet="omnivore"),
        Species(id=2, name="Herbivore",   color=(240,160,60), aggression=0.10, bravery=0.80, metabolism=0.95, diet="herbivore"),
        Species(id=3, name="Carnivore",color=(60,200,120), aggression=0.65, bravery=0.40, metabolism=1.05, diet="carnivore"),
    ]

def _init_population(n: int, start_id: int = 1):
    pop = []
    RNG.seed(SIM.seed)
    species = _seed_species()
    for i in range(n):
        sp = species[i % len(species)]
        pop.append(Creature(
            id=start_id + i,
            species=sp,
            speed=random.uniform(0.5, 5.0),
            size=random.uniform(0.5, 3.0),
            sense=random.uniform(15.0, 50.0),
            x=0.0, y=0.0,
            home=(0.0,0.0),
            energy=0.0,
        ))
    return pop

def run_ui():
    pygame.init()
    pygame.display.set_caption("Evolution (Rules of Survival) — Live (Species + Phylogeny)")
    W, H = 1280, 720
    screen = pygame.display.set_mode((W, H), pygame.RESIZABLE | pygame.SCALED)
    clock = pygame.time.Clock()

    def layout():
        w, h = screen.get_size()
        panel_w = int(w * 0.32)
        world_rect = pygame.Rect(10, 120, w - panel_w - 30, h - 140)
        panel_rect = pygame.Rect(w - panel_w - 10, 120, panel_w, h - 140)
        return world_rect, panel_rect

    world_rect, panel_rect = layout()

    # lineage tracker (shared across days)
    lineage = LineageTracker()
    init_pop = _init_population(SIM.initial_population)
    for c in init_pop:
        lineage.register_root_species(c.species, birth_day=1)

    live = LiveSim(init_pop, seed=SIM.seed, lineage=lineage)
    logger = DailyCsvLogger(overall_path="runs/ui_daily.csv",
                        species_path="runs/ui_species_daily.csv",
                        enable_species=True)
    # old_panel = renderer.panel_mode
    # old_glyph = renderer.glyph_mode
    renderer = Renderer(screen, world_rect, panel_rect)
    # renderer.panel_mode = old_panel
    # renderer.glyph_mode = old_glyph

    recorder = Recorder(enabled=False, stride_steps=2, world_size=WORLD.width, dt=WORLD.dt, steps_per_day=WORLD.day_steps)

    paused = False
    sim_speed = 20  # steps/frame
    running = True

    while running:
        clock.tick(60)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(e.size, pygame.RESIZABLE | pygame.SCALED)
                world_rect, panel_rect = layout()
                renderer = Renderer(screen, world_rect, panel_rect)
                renderer.panel_mode = "traits"
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: running = False
                elif e.key == pygame.K_SPACE: paused = not paused
                elif e.key == pygame.K_r:
                    lineage = LineageTracker()
                    init_pop = _init_population(SIM.initial_population)
                    for c in init_pop:
                        lineage.register_root_species(c.species, birth_day=1)
                    live = LiveSim(init_pop, seed=random.randint(0, 1_000_000), lineage=lineage)
                    paused = False
                elif e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    WORLD.n_food = min(1000, int(WORLD.n_food) + 5)
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    WORLD.n_food = max(0, int(WORLD.n_food) - 5)
                elif e.key == pygame.K_LEFTBRACKET:
                    sim_speed = max(1, sim_speed - 1)
                elif e.key == pygame.K_RIGHTBRACKET:
                    sim_speed = min(40, sim_speed + 1)
                elif e.key == pygame.K_1: live.mutate_speed = not live.mutate_speed
                elif e.key == pygame.K_2: live.mutate_size  = not live.mutate_size
                elif e.key == pygame.K_3: live.mutate_sense = not live.mutate_sense
                elif e.key == pygame.K_m:
                    on = not (live.mutate_speed and live.mutate_size and live.mutate_sense)
                    live.mutate_speed = live.mutate_size = live.mutate_sense = on
                elif e.key == pygame.K_v: recorder.toggle()
                elif e.key == pygame.K_c: recorder.clear()
                elif e.key == pygame.K_s: recorder.save_npz()
                elif e.key == pygame.K_l:  # 'L' toggles species CSV
                    logger.enable_species = not logger.enable_species
                elif e.key == pygame.K_t:
                    renderer.panel_mode = "phylo" if renderer.panel_mode == "traits" else "traits"
                    # --- inside the main event loop ---
                elif e.key == pygame.K_t:
                    renderer.panel_mode = "phylo" if renderer.panel_mode == "traits" else "traits"
                elif e.key == pygame.K_g:
                    renderer.glyph_mode = "quads" if renderer.glyph_mode == "rings" else "rings"

        if not paused:
            for _ in range(sim_speed):
                new_day_started = live.step()
                if new_day_started:
                    logger.append_day(
                        day=live.day - 1,
                        pop=live.last_population_snapshot or live.population,  # prefer the snapshot of the day that just ran
                        food_per_day=int(WORLD.n_food),
                        day_steps=int(WORLD.day_steps),
                        notes=""
                    )
            recorder.maybe_capture(live)

        screen.fill(BG_COLOR)
        renderer.world_rect = world_rect
        renderer.panel_rect = panel_rect
        renderer.draw_hud(live, sim_speed, paused, recorder.enabled,
                          (live.mutate_speed, live.mutate_size, live.mutate_sense))
        renderer.draw_world(live)
        renderer.draw_panel(live, lineage)
        pygame.display.flip()

    pygame.quit()