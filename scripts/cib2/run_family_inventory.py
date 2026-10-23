"""Run the static mapper over real local checkpoint configs; never loads model weights."""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def compact(mapping,config,label):
    text=config.get('text_config') or config
    result=dict(label=label,model_status=mapping.get('model_status'),model_type=config.get('model_type'),architectures=config.get('architectures'),
                text_model_type=text.get('model_type'),text_fields={k:v for k,v in text.items() if k in ('num_hidden_layers','hidden_size','num_experts','num_local_experts','num_experts_per_tok','num_experts_per_token','moe_intermediate_size','shared_expert_intermediate_size','max_position_embeddings')},
                layer_types=dict(collections.Counter(text.get('layer_types') or [])),compiled_otd='NOT_RUN',runtime_acceptance='NO',graphs=[])
    result['bin_file_bytes']=sum(x.get('file_size_bytes',0) for x in mapping.get('binaries',[]))
    result['expert_fields']={k:v for k,v in text.items() if 'expert' in k.lower() or 'moe' in k.lower()}
    result['referenced_unique_bytes']=sum(x.get('referenced_unique_bytes') or 0 for x in mapping.get('binaries',[]))
    for graph in mapping.get('graphs',[]):
        nodes=graph.get('layers',[]);roles=collections.Counter(x.get('role','unknown') for x in nodes)
        blocks={}
        for node in nodes:
            block=node.get('transformer_block_index')
            if block is None:continue
            entry=blocks.setdefault(block,dict(observed_node_count=0,role_counts=collections.Counter()))
            entry['observed_node_count']+=1;entry['role_counts'][node.get('role','unknown')]+=1
        result['graphs'].append(dict(file=graph.get('file'),sha256=graph.get('sha256'),status=graph.get('status'),graph_name=graph.get('graph_name'),node_count=len(nodes),role_counts=dict(roles),
                                     observed_transformer_blocks={str(k):dict(observed_node_count=v['observed_node_count'],role_counts=dict(v['role_counts'])) for k,v in sorted(blocks.items())},
                                     accounting=graph.get('byte_accounting'),errors=graph.get('errors')))
    result['scope']='Static inventory only. Transformer block IDs are parsed from actual names; node IDs are separate. No hotness, compiled fusion, resident-byte or physical NVMe claim.'
    return result


def run(root,out):
    out.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).with_name('family_map.py')
    spec=importlib.util.spec_from_file_location('cib2_family_inventory_mapper',source)
    mapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(mapper)
    result=dict(schema='cib2.family_inventory/1',mapper_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),inventory_runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),model_root=str(root),models=[],skipped_configs=[])
    assigned_targets=set()
    for path in sorted(root.rglob('config.json')):
        try:config=json.loads(path.read_text(encoding='utf-8-sig'))
        except Exception as e:
            result['skipped_configs'].append(dict(path=str(path),reason=str(e)));continue
        if not (config.get('architectures') or config.get('model_type')):
            result['skipped_configs'].append(dict(path=str(path),reason='Serving/non-model config: no architecture/model_type'));continue
        label=str(path.parent.relative_to(root)).replace('\\','/')
        slug=re.sub('[^a-zA-Z0-9_-]+','_',label)[:40]+'-'+hashlib.sha256(label.encode('utf-8')).hexdigest()[:16]
        target=out/(slug+'.json')
        if target.name.casefold() in assigned_targets:
            raise ValueError('Inventory output filename collision: '+label)
        assigned_targets.add(target.name.casefold())
        mapping=mapper.scan_model_dir(path.parent)
        target.write_text(json.dumps(mapping,indent=2),encoding='utf-8')
        summary=compact(mapping,config,label);summary['private_full_map']=str(target)
        summary['config_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        result['models'].append(summary)
        print(label,summary['model_status'],len(summary['graphs']),flush=True)
    result['unavailable_families']=['LFM: no matching config/IR found in this bounded root','GLM: no matching config/IR found in this bounded root']
    # Do not assert absence if a newly discovered model actually belongs to that family.
    types=' '.join(str(x.get('model_type','')) for x in result['models']).lower()
    if 'lfm' in types:result['unavailable_families']=[x for x in result['unavailable_families'] if not x.startswith('LFM:')]
    if 'glm' in types:result['unavailable_families']=[x for x in result['unavailable_families'] if not x.startswith('GLM:')]
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--models-root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args();run(args.models_root,args.output_dir)
