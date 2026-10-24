"""
Task definitions for the Seasonal Farm Market environment.
"""
import sys
import os
import copy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simcore.world import generate, get_all_task_ids, DEMO_TASK
from simcore.engine import Engine


class TaskInstance:
    """A single task instance with all data needed for a run."""

    def __init__(self, task_id, seed):
        self.task_id = task_id
        self.seed = seed

        # Generate world
        self.world = generate(task_id, seed)
        self.cfg = self.world["cfg"]
        self.oracle_actions = self.world["oracle_actions"]
        self.difficulty = self.cfg.get("difficulty", "unknown")

        # Compute oracle gain
        self._oracle_gain = None

    @property
    def oracle_gain(self):
        if self._oracle_gain is None:
            eng = Engine(copy.deepcopy(self.world))
            for name, args in self.oracle_actions:
                getattr(eng, name)(**args)
            if not eng.is_done():
                eng.finish()
            self._oracle_gain = eng.compute_net_worth() - self.cfg["start_cash"]
        return self._oracle_gain

    @property
    def instructions(self):
        """Generate agent instructions for this task."""
        cfg = self.cfg
        crops = cfg["crops"]
        crop_info = []
        for name in sorted(crops.keys()):
            c = crops[name]
            info = (f"  - {name}: seed cost ${c['seed_cost']/100:.2f}, "
                    f"grows in {c['grow_days']} days, yields {c['yield_units']} units, "
                    f"base price ~${c['base_price']/100:.2f}")
            if c.get("spoil_days") is not None:
                info += f", spoils after {c['spoil_days']} days"
            crop_info.append(info)

        text = f"""You are managing a small farm market for {cfg['horizon']} days.

GOAL: Maximize your net worth (cash + inventory value - debt).

Starting cash: ${cfg['start_cash']/100:.2f}
Plots: {cfg['n_plots']}
Daily land tax: ${cfg['land_tax']/100:.2f} per plot (${cfg['land_tax'] * cfg['n_plots']/100:.2f}/day total)

Available crops:
{chr(10).join(crop_info)}

Key mechanics:
- Plant crops on plots, wait for them to grow, harvest, then sell.
- Selling has slippage: each unit sold slightly lowers the price for the next.
- Time only advances when you call advance_days(n) with n from 1 to 7.
- Daily taxes are charged automatically. If you can't pay, the shortfall becomes debt."""

        if cfg.get("storage_cap") is not None:
            text += f"\n- Storage capacity: {cfg['storage_cap']} units."

        if cfg.get("events_on"):
            text += "\n- Events (droughts, demand spikes) can occur. Use get_news() to check."

        if cfg.get("loans_on"):
            text += (f"\n- Loans available: up to ${cfg['credit_limit']/100:.2f}, "
                     f"daily interest {cfg['daily_interest_permille']}‰, "
                     f"must repay by day {cfg['repay_deadline_day']}.")

        text += """

Strategy tips:
- Use get_status() to check your farm state.
- Use get_market() to see current prices.
- Use get_forecast() for noisy price predictions.
- Plant, harvest, and sell at good prices.
- Call finish() when you're done or want to end early.
- Doing nothing costs you taxes every day, so be active!"""

        return text

    def get_world_for_sandbox(self):
        """Return world data to send to sandbox /reset (stripped of oracle solutions)."""
        w = copy.deepcopy(self.world)
        w.pop("oracle_actions", None)
        return w


from simcore.world import generate, get_all_task_ids, get_primary_task_ids, DEMO_TASK, PRIMARY_TASKS


def build_task(task_id, seed, difficulty=None):
    """Build a TaskInstance, validating the oracle achieves minimum gain."""
    if difficulty:
        if not task_id.endswith(f"_{difficulty}"):
            task_id = f"{task_id}_{difficulty}"
    task = TaskInstance(task_id, seed)
    # Validate oracle gain
    assert task.oracle_gain > 0, (
        f"Oracle gain too low for {task_id} seed={seed}: {task.oracle_gain}"
    )
    return task


def get_demo_task_id():
    """Return the DEMO_TASK id."""
    return DEMO_TASK


def get_task_ids():
    """Return all task IDs."""
    return get_all_task_ids()


def get_primary_tasks():
    """Return the 5 distinct scenario metadata dicts."""
    return PRIMARY_TASKS
