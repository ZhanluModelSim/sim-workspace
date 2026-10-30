"""Run inside the existing training container; export plain JSON capture facts."""
import json
from dataclasses import asdict
from pathlib import Path
from torchtitan_simulator.config import SimulationConfig
from torchtitan_simulator.runner import simulate
out = Path('/tmp/des-prototype-data')
out.mkdir(exist_ok=True)
for model in ('deepseek_v4_smoketest', 'kimi_k3_smoketest'):
    for ac in ('none', 'selective'):
        name = f'{model}-{ac}'
        options = SimulationConfig(config=model, world_size=4, data_parallel_replicate_degree=2,
            expert_parallel_degree=2, activation_checkpoint_mode=ac, seq_len=128,
            output_dir=str(out / name))
        result = simulate(options)
        source = result.captured_workload or result
        nodes = sorted((n for t in source.step_templates.values() for n in t.nodes.values()), key=lambda n:n.seq_idx)
        payload = dict(case=name, config=asdict(options), nodes=[dict(id=n.op_id, seq=n.seq_idx,
            raw=n.annotations['raw_op_type'], canonical=n.op_type, predecessors=n.predecessors,
            annotations=n.annotations, inputs=[asdict(t) for t in n.inputs], outputs=[asdict(t) for t in n.outputs]) for n in nodes],
            communication=source.iteration.schedule.annotations['communication_events'])
        (out / f'{name}.json').write_text(json.dumps(payload, default=str))
        print('EXPORTED', name, len(nodes), flush=True)
