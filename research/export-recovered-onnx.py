"""Update public v15 ONNX graphs with fine-tuned parameters, preserving the API.

Exporter deduplication can express equal original parameters as Identity aliases.
Fine-tuning can separate these values, so materialize each learned alias and
each transposed MatMul parameter rather than updating shared constants in place.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import onnx
from onnx import numpy_helper
import torch


def export(checkpoint,destination):
    checkpoint=Path(checkpoint);destination=Path(destination)
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    destination.mkdir(parents=True,exist_ok=True)
    source=Path('/mnt/g/Heroes3-AI-Lab/models/upstream-v15')
    checksum=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    records=[]
    for side,role in enumerate(['attacker','defender']):
        template=source/(role+'.onnx');model=onnx.load(template)
        parameters={k:v.detach().cpu().float().numpy() for k,v in state['models'][role]['weights'].items()}
        initializers={item.name:item for item in model.graph.initializer}
        assigned=set()
        for name in list(initializers):
            if name in parameters:
                assert numpy_helper.to_array(initializers[name]).shape==parameters[name].shape
                initializers[name]=numpy_helper.from_array(parameters[name],name);assigned.add(name)
        nodes=[];materialized=0;matrices=0
        for node in model.graph.node:
            if node.op_type=='Identity' and node.output[0] in parameters:
                name=node.output[0]
                initializers[name]=numpy_helper.from_array(parameters[name],name)
                assigned.add(name);materialized+=1
                continue
            if node.op_type=='MatMul' and node.name.startswith('/gnn/convs.'):
                match=re.match(r'/gnn/(convs\.\d+\.\d+)/(.*)/MatMul',node.name)
                assert match,node.name
                key='gnn.'+match[1]+'.'+match[2].replace('mlp/mlp.','mlp.')+'.weight'
                assert key in parameters,key
                name='lab_finetuned.'+str(matrices)+'.'+key
                initializers[name]=numpy_helper.from_array(parameters[key].T.copy(),name)
                node.input[1]=name;assigned.add(key);matrices+=1
            nodes.append(node)
        assert set(parameters)<=assigned,sorted(set(parameters)-assigned)
        used=set(model.graph.output[i].name for i in range(len(model.graph.output)))
        def collect(graph_nodes):
            for node in graph_nodes:
                used.update(node.input)
                for attr in node.attribute:
                    if attr.type==onnx.AttributeProto.GRAPH:collect(attr.g.node)
                    elif attr.type==onnx.AttributeProto.GRAPHS:
                        for subgraph in attr.graphs:collect(subgraph.node)
        collect(nodes)
        model.graph.ClearField('node');model.graph.node.extend(nodes)
        model.graph.ClearField('initializer');model.graph.initializer.extend(v for k,v in initializers.items() if k in used)
        metadata={m.key:m.value for m in model.metadata_props}
        assert int(metadata['version'])==15 and int(metadata['side'])==side
        metadata.update(lab_checkpoint_sha256=checksum(checkpoint),lab_original_model_sha256=checksum(template),
            lab_finetuning_mode=state.get('finetuning_mode','heads'),
            lab_export_note='Fine-tuned values in original public graph; deduplicated learned aliases materialized independently')
        model.ClearField('metadata_props')
        for key,value in metadata.items():entry=model.metadata_props.add();entry.key=key;entry.value=str(value)
        onnx.checker.check_model(model)
        path=destination/(role+'.onnx');onnx.save(model,path)
        records.append(dict(role=role,path=str(path),sha256=checksum(path),parameter_arrays=len(parameters),
            materialized_aliases=materialized,transposed_matrices=matrices))
    manifest=dict(checkpoint=str(checkpoint),checkpoint_sha256=checksum(checkpoint),models=records,
        interface='Original v15 typed graph inputs and action/probabilities/value/legal-ID outputs',
        needs_numeric_and_live_validation=True)
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--checkpoint',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();print(json.dumps(export(args.checkpoint,args.output_dir),indent=2))
