"""Render the unmodified native template; record real tokenizer IDs, not parser acceptance."""
import argparse
import json
from pathlib import Path
import traceback
from jinja2 import Environment, StrictUndefined
import openvino_genai as genai


def run(model):
    env = Environment()  # match Transformers' permissive missing optional fields
    env.filters['items'] = lambda x: x.items()
    env.globals['raise_exception'] = lambda message: (_ for _ in ()).throw(ValueError(message))
    template = env.from_string((model / 'chat_template.jinja').read_text(encoding='utf-8'))
    tokenizer = genai.Tokenizer(str(model))
    user = dict(role='user', content='Use the ping function.')
    tool = dict(type='function', function=dict(name='ping', description='Return a pong.', parameters=dict(type='object', properties={})))
    def call(arguments):
        return dict(function=dict(name='ping', arguments=arguments))
    cases = [
        ('thinking_default', [user], {}),
        ('thinking_disabled', [user], {'enable_thinking': False}),
        ('empty_arguments', [user, dict(role='assistant',content='',tool_calls=[call({})])], {}),
        ('multi_calls', [user, dict(role='assistant',content='',tool_calls=[call({}),call({'value':42})])], {}),
        ('tool_response', [user,dict(role='assistant',content='',tool_calls=[call({})]),dict(role='tool',content='pong')], {}),
        ('reasoning', [user,dict(role='assistant',content='<think>check</think>done')], {}),
        ('json_string_arguments', [user,dict(role='assistant',content='',tool_calls=[call('{}')])], {}),
    ]
    out = {'scope':'Native template rendering and tokenizer only; no C++ parser, streaming, matcher or inference acceptance.', 'cases':[]}
    for name, messages, kwargs in cases:
        row = dict(name=name, messages=messages, kwargs=kwargs)
        try:
            rendered = template.render(messages=messages, tools=[tool], add_generation_prompt=True, **kwargs)
            ids = tokenizer.encode(rendered, add_special_tokens=False).input_ids.data.tolist()
            row.update(render_status='PASS', rendered=rendered, token_ids=ids)
        except Exception:
            row.update(render_status='FAIL',exception=traceback.format_exc())
        out['cases'].append(row)
    markers = ['<think>','</think>','<tool_call>','</tool_call>','<function=ping>','<parameter=value>','<|im_end|>','<|im_start|>','<tool_response>']
    out['marker_ids'] = {s: tokenizer.encode(s, add_special_tokens=False).input_ids.data.tolist() for s in markers}
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path, required=True)
    p.add_argument('--output',type=Path, required=True)
    args=p.parse_args()
    args.output.write_text(json.dumps(run(args.model),indent=2),encoding='utf-8')
