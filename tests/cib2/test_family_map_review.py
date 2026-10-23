"""Independent regressions from fresh external code review."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('map_review_cases',Path(__file__).parents[2]/'scripts/cib2/family_map.py')
mapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(mapper)


class ReviewCases(unittest.TestCase):
    def scan(self,layers,config_name='config.json',config=None):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            if config is None:config={'model_type':'fixture','architectures':['FixtureModel']}
            (root/config_name).write_text(json.dumps(config))
            (root/'m.bin').write_bytes(bytes(3000))
            (root/'m.xml').write_text('<net version="11"><layers>'+layers+'</layers></net>')
            return mapper.scan_model_dir(root)

    def test_const_without_data_is_invalid_without_exception(self):
        result=self.scan('<layer id="0" name="c0" type="Const"/>')
        self.assertEqual(result['graphs'][0]['status'],'invalid')

    def test_auxiliary_json_does_not_substitute_for_model_config(self):
        result=self.scan('<layer id="0" name="input" type="Parameter"/>','tokenizer_config.json',{'tokenizer_class':'X'})
        self.assertNotEqual(result['model_status'],'complete')

    def test_bad_range_cannot_create_negative_alias_saving(self):
        layers=''.join(f'<layer id="{i}" name="c{i}" type="Const"><data element_type="u8" shape="{size}" offset="{offset}" size="{size}"/></layer>' for i,(offset,size) in enumerate([(0,1000),(500,1000),(1500,2000)]))
        result=self.scan(layers);graph=result['graphs'][0]
        self.assertEqual(graph['status'],'invalid')
        self.assertEqual(graph['byte_accounting']['referenced_unique_bytes'],1500)
        self.assertEqual(graph['byte_accounting']['aliased_shared_bytes_saved'],500)

    def test_missing_node_id_is_not_invented(self):
        result=self.scan('<layer name="input" type="Parameter"/>')
        graph=result['graphs'][0]
        self.assertEqual(graph['status'],'invalid')
        self.assertIsNone(graph['layers'][0]['layer_id'])


if __name__=='__main__':unittest.main(verbosity=2)
