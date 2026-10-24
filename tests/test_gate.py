"""Test oracle >= 0.95 and no-op <= 0.05 across seeds 0..49 and all tasks."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from simcore.world import generate, validate_oracle, get_all_task_ids
from simcore.engine import Engine

failures = []
for task_id in get_all_task_ids():
    for seed in range(50):
        oracle_gain, world = validate_oracle(task_id, seed)
        
        # Oracle check
        eng_o = Engine(world)
        for name, args in world["oracle_actions"]:
            getattr(eng_o, name)(**args)
        if not eng_o.is_done():
            eng_o.finish()
        score_o = eng_o.compute_score(oracle_gain)
        if score_o["total"] < 0.95:
            failures.append(f"ORACLE {task_id} seed={seed}: total={score_o['total']:.4f}")
        
        # No-op check
        eng_n = Engine(world)
        eng_n.finish()
        score_n = eng_n.compute_score(oracle_gain)
        if score_n["total"] > 0.05:
            failures.append(f"NOOP {task_id} seed={seed}: total={score_n['total']:.4f}")

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    print(f"\n{len(failures)} failures")
    sys.exit(1)
else:
    print(f"PASS: All {len(get_all_task_ids())*50*2} checks passed (oracle>=0.95, noop<=0.05)")
