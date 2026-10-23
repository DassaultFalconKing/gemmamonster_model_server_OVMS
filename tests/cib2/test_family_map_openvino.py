"""Independent acceptance fixtures using actual OpenVINO IR/config syntax."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

source=Path(__file__).parents[2]/'scripts/cib2/family_map.py'
spec=importlib.util.spec_from_file_location('family_map_acceptance',source)
mapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(mapper)


class OpenVINOContractTest(unittest.TestCase):
    def test_json_config_packed_expert_and_actual_data_attributes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'config.json').write_text(json.dumps({'architectures':['Qwen3_5MoeForConditionalGeneration'],'model_type':'qwen3_5_moe','text_config':{'num_hidden_layers':40,'num_experts':256,'num_experts_per_tok':8}}))
            (root/'decoder.bin').write_bytes(bytes(65536))
            (root/'decoder.xml').write_text('''<net name="decoder" version="11"><layers>
<layer id="0" name="model.language_model.layers.7.mlp.experts.down_proj.weight" type="Const" version="opset1">
<data element_type="u4" shape="256,16,32" offset="0" size="65536"/>
<output><port id="0" precision="U4"><dim>256</dim><dim>16</dim><dim>32</dim></port></output></layer>
<layer id="1" name="inputs_embeds" type="Parameter" version="opset1"><data shape="1,?,2048" element_type="f32"/></layer>
<layer id="2" name="logits" type="Result" version="opset1"/>
</layers><edges/></net>''')
            result=mapper.scan_model_dir(root)
            self.assertEqual(result['model_config']['model_type'],'qwen3_5_moe')
            self.assertEqual(result['model_status'],'complete')
            self.assertEqual(result['model_config']['architecture'],'Qwen3_5MoeForConditionalGeneration')
            nodes=result['graphs'][0]['layers']
            weight=next(x for x in nodes if x.get('name','').endswith('down_proj.weight'))
            self.assertEqual(weight['role'],'routed_expert')
            self.assertEqual(weight['const']['element_type'],'u4')
            self.assertEqual(weight['const']['shape'],['256','16','32'])
            self.assertEqual(weight['transformer_block_index'],7)


if __name__=='__main__':unittest.main(verbosity=2)
