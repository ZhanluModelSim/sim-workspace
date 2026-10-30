import unittest
from des import run, prepare, classify

def node(i, resources, duration, preds=(), seq=None):
    return dict(id=i,seq=i if seq is None else seq,resources=resources,duration=duration,predecessors=list(preds))

class TestDES(unittest.TestCase):
    def test_priority_alone_cannot_stop_late_root_but_queue_can(self):
        nodes={1:node(1,('COMM',),10),2:node(2,('CUBE',),3,[1]),3:node(3,('CUBE',),20)}
        unconstrained=run(nodes)
        self.assertEqual(unconstrained[3],(0,20))
        self.assertEqual(unconstrained[2],(20,23))
        nodes[3]['predecessors']=[2]
        ordered=run(nodes)
        self.assertEqual(ordered[2],(10,13))
        self.assertEqual(ordered[3],(13,33))

    def test_independent_compute_overlaps_comm_and_wait_gates_consumer(self):
        nodes={1:node(1,('COMM',),10),2:node(2,('CUBE',),8),3:node(3,(),0,[1,2]),4:node(4,('CUBE',),3,[3])}
        times=run(nodes)
        self.assertEqual(times[1],(0,10))
        self.assertEqual(times[2],(0,8))
        self.assertEqual(times[4],(10,13))
        self.assertEqual(run(nodes,{1:20})[4],(20,23))

    def test_multi_resource_is_atomic_and_does_not_block_free_engine(self):
        nodes={1:node(1,('CUBE',),10),2:node(2,('CUBE','VEC'),4),3:node(3,('VEC',),2)}
        times=run(nodes)
        self.assertEqual(times[3],(0,2))
        self.assertEqual(times[2],(10,14))

    def test_allocation_metadata_and_host_have_no_hardware_cost(self):
        for raw in ('aten.empty.memory_format','aten.view.default','aten.detach.default','profiler._record_function_enter_new.default'):
            category, resources, duration=classify(dict(raw=raw,canonical='unknown'))
            self.assertEqual((resources,duration),((),0))
        self.assertEqual(classify(dict(raw='aten.clone.default',canonical='unknown'))[1],('VEC',))

    def test_prepare_preserves_queue_order_with_missing_data_edge(self):
        payload={'nodes':[dict(id=i,seq=i,raw='aten.mm.default',canonical='matmul',predecessors=[],annotations={'stream_id':0}) for i in (1,2)]}
        nodes,info=prepare(payload)
        self.assertEqual(nodes[2]['predecessors'],[1])
        self.assertEqual(run(nodes)[2],(12,24))
        self.assertEqual(run(dict(reversed(list(nodes.items())))),run(nodes))

    def test_cycle_is_reported(self):
        with self.assertRaisesRegex(ValueError,'deadlock'):
            run({1:node(1,('CUBE',),1,[2]),2:node(2,('VEC',),1,[1])})

if __name__=='__main__': unittest.main()
