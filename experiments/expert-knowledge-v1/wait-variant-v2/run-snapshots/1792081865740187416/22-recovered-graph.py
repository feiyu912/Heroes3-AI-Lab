"""Differentiable v15 GENConv forward recovered from official ONNX parameters.

Matches rl/v15/export.py. Conversion is accepted only after ONNX equivalence.
No PyG/scatter extensions required; uses Torch's native scatter operations.
"""
import json
import re
import os
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


def extract(path):
    import onnx
    from onnx import numpy_helper
    model=onnx.load(path)
    constants={x.name:numpy_helper.to_array(x).copy() for x in model.graph.initializer}
    for node in model.graph.node:
        if node.op_type=='Identity' and node.input[0] in constants:
            constants[node.output[0]]=constants[node.input[0]]
    weights={name:torch.tensor(value) for name,value in constants.items()
             if name.startswith(('gnn.','policy_head.','value_head.'))}
    for node in model.graph.node:
        if node.op_type=='MatMul' and node.name.startswith('/gnn/convs.'):
            assert node.input[1] in constants,node.name
            match=re.match(r'/gnn/(convs\.\d+\.\d+)/(.*)/MatMul',node.name)
            assert match,node.name
            suffix=match[2].replace('mlp/mlp.','mlp.')
            key='gnn.'+match[1]+'.'+suffix+'.weight'
            weights[key]=torch.tensor(constants[node.input[1]].T.copy())
    metadata={m.key:m.value for m in model.metadata_props}
    return weights,metadata


class RecoveredGraph(nn.Module):
    def __init__(self,weights,metadata,freeze_graph=True):
        super().__init__()
        self.metadata=metadata
        self.nodes=json.loads(metadata['node_order'])
        self.edges=[tuple(e) for e in json.loads(metadata['edge_order'])]
        self.side=int(metadata['side'])
        self.weights=nn.ParameterDict({k.replace('.','__'):nn.Parameter(v.float().clone(),requires_grad=not freeze_graph or k.startswith(('policy_head.','value_head.')))
                                      for k,v in weights.items()})
        self.layers=max(int(k.split('.')[2]) for k in weights if k.startswith('gnn.convs.'))+1
        self.names=set(weights)

    def weight(self,key):
        return self.weights[key.replace('.','__')]

    def linear(self,x,key):
        if key+'.weight' not in self.names:return x
        bias=self.weights.get((key+'.bias').replace('.','__'))
        return F.linear(x,self.weight(key+'.weight'),bias)

    def head(self,x,name):
        x=F.layer_norm(x,(x.shape[-1],),self.weight(name+'.0.weight'),self.weight(name+'.0.bias'),1e-5)
        x=F.leaky_relu(self.linear(x,name+'.1'),0.01)
        x=F.leaky_relu(self.linear(x,name+'.3'),0.01)
        return self.linear(x,name+'.5')

    def encode(self,nodes,edges):
        h={n:self.linear(nodes[n],'gnn.node_encoder.modules_by_key.'+n) for n in self.nodes}
        for layer in range(self.layers):
            old=h;new={}
            for edge_number,(relation,edge) in enumerate(zip(self.edges,edges)):
                src,_,dst=relation
                index,attrs=edge
                key=f'gnn.convs.{layer}.{edge_number}'
                # ONNX prunes final outputs other than Action and Global.
                if key+'.mlp.0.weight' not in self.names:continue
                xs=self.linear(old[src],key+'.lin_src')
                xd=self.linear(old[dst],key+'.lin_dst')
                msg=xs[index[0]]
                edge_key=(key+'.lin_edge.weight').replace('.','__')
                if edge_key in self.weights:
                    msg=msg+self.linear(attrs,key+'.lin_edge')
                msg=F.relu(msg)+1e-7
                score=msg*self.weight(key+'.softmax_t')
                ids=index[1,None].T.expand_as(score)
                maximum=score.new_full(xd.shape,-torch.finfo(score.dtype).max)
                maximum.scatter_reduce_(0,ids,score,reduce='amax',include_self=True)
                exp=(score-maximum[index[1]]).exp()
                total=exp.new_zeros(xd.shape).scatter_add_(0,ids,exp)
                alpha=exp/(total[index[1]]+1e-16)
                aggregate=msg.new_zeros(xd.shape).scatter_add_(0,ids,msg*alpha)+xd
                out=self.linear(F.relu(self.linear(aggregate,key+'.mlp.0')),key+'.mlp.3')
                new[dst]=new[dst]+out if dst in new else out
            h={}
            for n in self.nodes:
                if n not in new:continue
                x=new[n]
                norm=f'gnn.norms.{layer}.norms.{n}'
                if (norm+'.weight').replace('.','__') in self.weights:
                    x=F.layer_norm(old[n]+x,(x.shape[-1],),self.weight(norm+'.weight'),self.weight(norm+'.bias'),1e-5)
                if layer<self.layers-1:x=F.leaky_relu(x,0.01)
                h[n]=x
        return h

    def tensors(self,obs,device):
        nodes={n:torch.as_tensor(obs['nodes'][n],device=device,dtype=torch.float32) for n in self.nodes}
        edges=[(torch.as_tensor(obs['edges'][e]['index'],device=device,dtype=torch.long),
                torch.as_tensor(obs['edges'][e]['attrs'],device=device,dtype=torch.float32)) for e in self.edges]
        return nodes,edges

    def forward(self,obs):
        device=next(self.parameters()).device
        h=self.encode(*self.tensors(obs,device))
        ids=torch.as_tensor(obs['active_action_ids'],device=device,dtype=torch.long)
        logits=self.head(h['Action'][ids],'policy_head').squeeze(-1)
        value=self.head(h['Global'],'value_head').reshape(())
        return logits,value

    def encode_batch(self,observations):
        device=next(self.parameters()).device
        offsets={n:np.cumsum([0]+[len(o['nodes'][n]) for o in observations]) for n in self.nodes}
        nodes={n:torch.as_tensor(np.concatenate([o['nodes'][n] for o in observations]),device=device) for n in self.nodes}
        edges=[]
        for key in self.edges:
            indices=[];attrs=[]
            for i,obs in enumerate(observations):
                index=obs['edges'][key]['index'].astype(np.int64).copy()
                index[0]+=offsets[key[0]][i];index[1]+=offsets[key[2]][i]
                indices.append(index);attrs.append(obs['edges'][key]['attrs'])
            edges.append((torch.as_tensor(np.concatenate(indices,1),device=device),
                          torch.as_tensor(np.concatenate(attrs),device=device)))
        h=self.encode(nodes,edges)
        samples=[]
        for i,obs in enumerate(observations):
            ids=np.asarray(obs['active_action_ids'],np.int64)
            index=torch.as_tensor(ids+offsets['Action'][i],device=device)
            samples.append((h['Action'][index].cpu().numpy().copy(),h['Global'][i].cpu().numpy().copy(),ids.copy(),self.side))
        return samples


class RecoveredPair(nn.Module):
    def __init__(self,checkpoint=None):
        super().__init__()
        self.models=nn.ModuleDict()
        bundle=torch.load(checkpoint,map_location='cpu',weights_only=True) if checkpoint else None
        for role in ['attacker','defender']:
            data=bundle['models'][role] if bundle else torch.load('/root/heroes3-ai-lab/models/recovered-v15/'+role+'.pt',map_location='cpu',weights_only=True)
            self.models[role]=RecoveredGraph(data['weights'],data['metadata'])

    def encode_features(self,observations):
        samples=[None]*len(observations)
        with torch.inference_mode():
            for side,role in enumerate(['attacker','defender']):
                indices=[i for i,o in enumerate(observations) if o['lab_side']==side]
                if indices:
                    encoded=self.models[role].encode_batch([observations[i] for i in indices])
                    for i,sample in zip(indices,encoded):samples[i]=sample
        return samples

    def forward(self,embeddings,globals_,roles,mask):
        logits=embeddings.new_zeros(embeddings.shape[:2]);values=globals_.new_zeros(len(globals_))
        for side,role in enumerate(['attacker','defender']):
            indices=roles==side
            if bool(indices.any()):
                logits[indices]=self.models[role].head(embeddings[indices],'policy_head').squeeze(-1)
                values[indices]=self.models[role].head(globals_[indices],'value_head').squeeze(-1)
        return logits.masked_fill(~mask,-torch.inf),values

    def save(self,path,**metadata):
        Path=__import__('pathlib').Path
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        models={role:dict(weights={k.replace('__','.'):v.detach().cpu() for k,v in model.weights.items()},metadata=model.metadata)
                for role,model in self.models.items()}
        source=('Official v15 weights, PPO fine-tuning mode: '+metadata['finetuning_mode']
                if 'finetuning_mode' in metadata else 'Official v15 weights, frozen typed graph encoder, PPO adapted actor/value heads')
        destination=Path(path)
        temporary=destination.with_name(destination.name+'.tmp-'+str(os.getpid()))
        try:
            torch.save(dict(models=models,source=source,**metadata),temporary)
            with temporary.open('rb') as stream:os.fsync(stream.fileno())
            os.replace(temporary,destination)
        finally:
            if temporary.exists():temporary.unlink()


def head_collate(samples,device='cpu'):
    n=max(len(s[0]) for s in samples)
    embeddings=np.zeros((len(samples),n,64),np.float32)
    globals_=np.zeros((len(samples),64),np.float32)
    roles=np.zeros(len(samples),np.int64);mask=np.zeros((len(samples),n),bool)
    for i,(actions,global_,ids,role) in enumerate(samples):
        embeddings[i,:len(actions)]=actions;globals_[i]=global_;roles[i]=role;mask[i,:len(actions)]=True
    return tuple(torch.as_tensor(v,device=device) for v in [embeddings,globals_,roles,mask])
