# evo_sim/ui/recorder.py
from __future__ import annotations
import os, time
from typing import Optional
import numpy as np

class Recorder:
    """
    Capture snapshots every `stride_steps` for Blender playback (NPZ).
    Stores: pos, traits, alive, 'done' mask, day/step, and food positions.
    """
    def __init__(self, enabled=False, stride_steps=2, world_size=200.0, dt=0.05, steps_per_day=2000):
        self.enabled = enabled
        self.stride_steps = max(1, int(stride_steps))
        self.world_size = float(world_size)
        self.dt = float(dt)
        self.steps_per_day = int(steps_per_day)
        self._tstep = 0
        self.pos_list = []
        self.traits_list = []
        self.alive_list = []
        self.done_list = []
        self.day_step_list = []
        self.food_xy_list = []
        self.maxN = 0
        self.maxF = 0

    def toggle(self): self.enabled = not self.enabled; print(f"[Recorder] {'ON' if self.enabled else 'OFF'}")
    def clear(self):
        self._tstep = 0
        self.pos_list.clear(); self.traits_list.clear(); self.alive_list.clear(); self.done_list.clear()
        self.day_step_list.clear(); self.food_xy_list.clear()
        self.maxN = self.maxF = 0
        print("[Recorder] cleared")

    def maybe_capture(self, live):
        if not self.enabled: return
        self._tstep += 1
        if (self._tstep % self.stride_steps) != 0: return

        pop = live.population
        N = len(pop); self.maxN = max(self.maxN, N)
        pos = np.zeros((N,2), np.float32)
        tr  = np.zeros((N,3), np.float32)
        alive = np.zeros((N,), np.bool_)
        done  = np.zeros((N,), np.bool_)

        for i, c in enumerate(pop):
            pos[i] = (c.x, c.y)
            tr[i]  = (c.speed, c.size, c.sense)
            alive[i] = c.alive
            done[i]  = (c.alive and c.eaten >= 1 and c.at_home(live.world.home_margin))

        self.pos_list.append(pos); self.traits_list.append(tr)
        self.alive_list.append(alive); self.done_list.append(done)
        self.day_step_list.append((live.day, live.step_in_day))

        fxy = np.array(live.food_positions(), np.float32)
        self.food_xy_list.append(fxy)
        self.maxF = max(self.maxF, len(fxy))

    def save_npz(self, out_path: Optional[str]=None):
        if not self.pos_list:
            print("[Recorder] nothing to save"); return None

        T = len(self.pos_list); maxN = self.maxN; maxF = self.maxF
        pos  = np.full((T, maxN, 2), np.nan, np.float32)
        tr   = np.full((T, maxN, 3), np.nan, np.float32)
        alive= np.zeros((T, maxN), np.bool_)
        done = np.zeros((T, maxN), np.bool_)
        day_step = np.zeros((T, 2), np.int32)
        fxy  = np.full((T, maxF, 2), np.nan, np.float32)
        fcnt = np.zeros((T,), np.int32)

        for t in range(T):
            N = self.pos_list[t].shape[0]
            pos[t, :N] = self.pos_list[t]
            tr[t, :N]  = self.traits_list[t]
            alive[t, :N] = self.alive_list[t]
            done[t, :N]  = self.done_list[t]
            day_step[t] = self.day_step_list[t]
            F = self.food_xy_list[t].shape[0]
            fcnt[t] = F
            if F: fxy[t, :F] = self.food_xy_list[t]

        os.makedirs("recordings", exist_ok=True)
        if out_path is None:
            stamp = time.strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join("recordings", f"evo_run_{stamp}.npz")

        np.savez_compressed(
            out_path,
            world_size=np.float32(self.world_size),
            dt=np.float32(self.dt),
            steps_per_day=np.int32(self.steps_per_day),
            stride_steps=np.int32(self.stride_steps),
            pos=pos, traits=tr,
            alive=alive, done=done,
            day_step=day_step,
            food_xy=fxy, food_count=fcnt,
        )
        print(f"[Recorder] saved: {out_path} (T={T}, maxN={maxN})")
        return out_path
