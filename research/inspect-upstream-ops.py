import json
from pathlib import Path
import onnx
from onnx import numpy_helper
m=onnx.load('/mnt/g/Heroes3-AI-Lab/models/upstream-v15/attacker.onnx')
rows=[dict(name=n.name,op=n.op_type,inputs=list(n.input),outputs=list(n.output),
           attrs={a.name:str(onnx.helper.get_attribute_value(a)) for a in n.attribute})
      for n in m.graph.node if n.op_type in ['MatMul','Gemm','LayerNormalization','LeakyRelu','Mul','Constant','Cast']]
print([(n.name,list(n.input)) for n in m.graph.node if n.op_type=='Mul' and n.name.startswith('/gnn/convs.2.0/')])
Path('/mnt/g/Heroes3-AI-Lab/research/upstream-weight-ops.json').write_text(json.dumps(rows,indent=2))
