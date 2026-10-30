"""Standalone deterministic DES, standard library only. Time unit: synthetic tick."""
import argparse
import csv
import heapq
import json
from collections import Counter, defaultdict
from pathlib import Path

META = ('view','reshape','permute','transpose','t','slice','select','narrow','as_strided','squeeze','unsqueeze','expand','alias','detach','split','split_with_sizes','unbind','_unsafe_view','lift_fresh')
ALLOC = ('empty','empty_like','empty_strided','new_empty','new_empty_strided')
COMM = {'allgather','reduce_scatter','allreduce','all_to_all','broadcast','p2p_send','p2p_recv'}
CUBE = {'matmul','bmm','grouped_mm','einsum'}
FUSED = {'sdpa','flash_attention_fwd','fusion_attention','chunk_kda'}

def classify(n):
    raw, canonical = n['raw'], n['canonical']
    name = raw.split('.')[1] if raw.startswith('aten.') else ''
    if raw.startswith('profiler.'):
        return 'host_instrumentation', (), 0
    if raw == '_c10d_functional._wrap_tensor_autograd.default':
        return 'metadata', (), 0
    if canonical == 'stream_wait' or 'wait_tensor' in raw:
        return 'control', (), 0
    if name in ALLOC:
        return 'allocation', (), 0
    if name in META:
        return 'metadata', (), 0
    operands = n.get('inputs', []) + n.get('outputs', [])
    if operands and all(t['device'].split(':')[0] == 'cpu' for t in operands):
        return 'host', (), 0
    if canonical in COMM:
        return 'communication', ('COMM',), 8
    if canonical in CUBE:
        return 'matrix', ('CUBE',), 12
    if canonical in FUSED or any(s in raw for s in ('attention','mhc','hc_pre','hc_post','sparse_flash','lightning_indexer','convolution')):
        return 'mixed_fusion_assumption', ('CUBE','VEC'), 12
    if raw.startswith(('fsdp.all_gather_copy_in.', 'fsdp.chunk_cat.', 'fsdp.split_with_sizes_copy.')):
        return 'fsdp_copy_assumption', ('VEC',), 2
    if canonical != 'unknown' or name in ('copy_','clone','_to_copy','add','add_','mul','mul_','div','div_','sum','mean','pow','sqrt','rsqrt','neg','exp','log','eq','ne','gt','lt','where','zeros','zeros_like','ones','ones_like','full','full_like','fill_','zero_','arange','index','index_select','scatter_','scatter_add_','gather','masked_fill','masked_fill_'):
        return 'vector_or_copy_assumption', ('VEC',), 2
    return 'unclassified_vec_fallback', ('VEC',), 2

def prepare(payload):
    nodes = {}
    previous = {}
    added = 0
    fallback = 0
    for n in sorted(payload['nodes'], key=lambda n:(n['seq'], n['id'])):
        kind, resources, duration = classify(n)
        ann = n['annotations']
        stream = ann.get('stream_id')
        # Unknown device work joins a dedicated conservative fallback queue.
        # Do not pretend this is a known native default stream.
        if stream is None and resources:
            stream = 'unknown-device'
            fallback += 1
        preds = set(n['predecessors'])
        if stream is not None:
            if stream in previous and previous[stream] not in preds:
                preds.add(previous[stream]); added += 1
            previous[stream] = n['id']
        nodes[n['id']] = dict(n, predecessors=sorted(preds), kind=kind,
            resources=resources, duration=duration, queue=stream)
    for n in nodes.values():
        assert all(p in nodes for p in n['predecessors']), 'missing dependency'
    return nodes, dict(added_queue_edges=added, fallback_nodes=fallback)

def run(nodes, durations=None, serial=False):
    durations = durations or {}
    successors = defaultdict(list)
    remaining = {}
    ready = defaultdict(list)
    running = []
    occupied = set()
    intervals = {}
    now = 0
    def resource(n):
        return ('SERIAL',) if serial and n['resources'] else tuple(n['resources'])
    def enqueue(key):
        n=nodes[key]
        heapq.heappush(ready[resource(n)], (n['seq'], key))
    def finish(key):
        for child in successors[key]:
            remaining[child] -= 1
            if remaining[child] == 0: enqueue(child)
    for key,n in nodes.items():
        remaining[key] = len(n['predecessors'])
        for p in n['predecessors']: successors[p].append(key)
    for key in nodes:
        if remaining[key] == 0: enqueue(key)
    while len(intervals) < len(nodes) or running:
        # Process all same-time completions before arbitration.
        while running and running[0][0] == now:
            end,key,resources=heapq.heappop(running)
            occupied.difference_update(resources)
            finish(key)
        # Propagate zero-resource nodes to a fixed point.
        while ready[()]:
            _,key=heapq.heappop(ready[()])
            intervals[key]=(now,now)
            finish(key)
        while True:
            candidates = [(queue[0], resources) for resources,queue in ready.items()
                if resources and queue and not occupied.intersection(resources)]
            if not candidates: break
            (_,key), resources = min(candidates)
            heapq.heappop(ready[resources])
            duration = durations.get(key,nodes[key]['duration'])
            assert duration > 0
            intervals[key]=(now,now+duration)
            occupied.update(resources)
            heapq.heappush(running,(now+duration,key,resources))
        if running:
            now=running[0][0]
        elif len(intervals)<len(nodes):
            raise ValueError('deadlock or cyclic graph')
    validate(nodes, intervals, serial)
    return intervals

def validate(nodes, intervals, serial=False):
    assert set(nodes)==set(intervals)
    lanes=defaultdict(list)
    for key,n in nodes.items():
        start,end=intervals[key]
        assert all(intervals[p][1]<=start for p in n['predecessors'])
        if not n['resources']: assert start==end
        for r in (('SERIAL',) if serial and n['resources'] else n['resources']):
            lanes[r].append((start,end,key))
    for values in lanes.values():
        values.sort()
        assert all(a[1]<=b[0] for a,b in zip(values,values[1:]))

def union(intervals):
    result=[]
    for s,e in sorted(intervals):
        if e<=s: continue
        if result and s<=result[-1][1]: result[-1]=(result[-1][0],max(e,result[-1][1]))
        else: result.append((s,e))
    return result

def intersection(a,b):
    a,b=union(a),union(b); i=j=0; total=0
    while i<len(a) and j<len(b):
        total+=max(0,min(a[i][1],b[j][1])-max(a[i][0],b[j][0]))
        if a[i][1]<b[j][1]: i+=1
        else: j+=1
    return total

def analyze(nodes, times):
    comm=[k for k,n in nodes.items() if n['kind']=='communication' and n['annotations'].get('fsdp_group_id')]
    # Count model compute separately from FSDP packing/copy work.
    model=[k for k,n in nodes.items() if set(n['resources']) & {'CUBE','VEC'} and not n['annotations'].get('framework_scopes')]
    busy=sum(times[k][1]-times[k][0] for k in comm)
    overlap=intersection([times[k] for k in comm],[times[k] for k in model])
    examples=[]
    for a in comm:
        for b in model:
            s,e=max(times[a][0],times[b][0]),min(times[a][1],times[b][1])
            if e>s and nodes[a]['queue']!=nodes[b]['queue']:
                examples.append(dict(comm=a,compute=b,comm_raw=nodes[a]['raw'],compute_raw=nodes[b]['raw'],
                    comm_queue=nodes[a]['queue'],compute_queue=nodes[b]['queue'],overlap_ticks=e-s))
                break
        if len(examples)==5: break
    # Delay AG/RS/AR and prove at least one dependent model operation moves.
    delay_checks=[]
    for primitive in ('allgather','reduce_scatter','allreduce'):
        for k in comm:
            if nodes[k]['canonical']!=primitive: continue
            descendants=set(); pending=[k]
            children=defaultdict(list)
            for child,n in nodes.items():
                for p in n['predecessors']: children[p].append(child)
            while pending:
                for child in children[pending.pop()]:
                    if child not in descendants: descendants.add(child); pending.append(child)
            targets=descendants.intersection(model)
            if not targets: continue
            delayed=run(nodes,{k:nodes[k]['duration']+1000})
            changed=[t for t in targets if delayed[t][0]>times[t][0]]
            assert changed, f'{primitive} delay failed to reach a model consumer'
            target=min(changed,key=lambda t:nodes[t]['seq'])
            delay_checks.append(dict(primitive=primitive,comm=k,consumer=target,
                start_before=times[target][0],start_after=delayed[target][0]))
            break
    return dict(makespan_ticks=max(e for s,e in times.values()),fsdp_comm_busy_ticks=busy,
        fsdp_model_overlap_ticks=overlap,fsdp_overlap_fraction=overlap/busy if busy else 0,
        examples=examples,delay_checks=delay_checks)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('input'); parser.add_argument('output')
    args=parser.parse_args(); out=Path(args.output); out.mkdir(exist_ok=True,parents=True)
    reports=[]
    for path in sorted(Path(args.input).glob('*.json')):
        payload=json.loads(path.read_text()); nodes,info=prepare(payload)
        times=run(nodes); report=analyze(nodes,times)
        report.update(case=payload['case'],nodes=len(nodes),queues=len({n['queue'] for n in nodes.values() if n['queue'] is not None}),
            categories=dict(Counter(n['kind'] for n in nodes.values())),**info)
        report['serialized_reference_ticks']=max(e for s,e in run(nodes,serial=True).values())
        report['duration_sensitivity']={}
        for scale in (0.5,2):
            altered=run(nodes,{k:max(1,int(n['duration']*scale)) for k,n in nodes.items() if n['kind']=='communication'})
            report['duration_sensitivity'][str(scale)]=dict(makespan_ticks=max(e for s,e in altered.values()),
                fsdp_model_overlap_ticks=intersection([altered[k] for k,n in nodes.items() if n['kind']=='communication' and n['annotations'].get('fsdp_group_id')],
                [altered[k] for k,n in nodes.items() if set(n['resources']) & {'CUBE','VEC'} and not n['annotations'].get('framework_scopes')]))
        records=[dict(id=k,seq=n['seq'],raw=n['raw'],kind=n['kind'],queue=n['queue'],resources='+'.join(n['resources']),start=times[k][0],end=times[k][1],
            fsdp=bool(n['annotations'].get('fsdp_group_id')),framework=bool(n['annotations'].get('framework_scopes')),module=n['annotations'].get('module_path','')) for k,n in nodes.items()]
        with (out/f'{path.stem}.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
        (out/f'{path.stem}.timeline.json').write_text(json.dumps(records))
        counts=Counter((n['raw'],n['kind'],'+'.join(n['resources'])) for n in nodes.values())
        with (out/f'{path.stem}.classification.csv').open('w') as f:
            w=csv.writer(f);w.writerow(['raw','category','resources','count']);w.writerows((*key,count) for key,count in sorted(counts.items()))
        reports.append(report)
        print(json.dumps(report),flush=True)
    (out/'summary.json').write_text(json.dumps(reports,indent=2))

if __name__=='__main__': main()
