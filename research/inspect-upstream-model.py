import json
from pathlib import Path
import onnx
from onnx import numpy_helper

r=Path('/mnt/g/Heroes3-AI-Lab/research')
model=onnx.load('/mnt/g/Heroes3-AI-Lab/models/upstream-v15/attacker.onnx')
metadata={m.key:m.value for m in model.metadata_props}
initializers=[dict(name=x.name,shape=list(x.dims),dtype=int(x.data_type)) for x in model.graph.initializer]
report=dict(metadata=metadata,initializers=initializers,nodes=len(model.graph.node))
(r/'upstream-onnx-structure.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(metadata=metadata,first_initializers=initializers[:18],nodes=len(model.graph.node)),indent=2))
