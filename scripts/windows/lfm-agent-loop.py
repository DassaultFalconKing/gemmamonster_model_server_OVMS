"""Bounded real host-tool loop. Generated shell commands are never executed."""
import argparse
import json
from pathlib import Path
import urllib.request
import urllib.error


def execute_tool(sandbox, name, params):
    if name == 'cwd' and params == {}:
        return {'cwd': str(sandbox.resolve())}
    if name not in ('write', 'read'):
        raise ValueError('unregistered tool or wrong arguments')
    target = sandbox / 'hello.txt'
    # Accept Windows and forward-slash spellings of the same exact allowed file.
    if (sandbox / params['path']).resolve() != target.resolve():
        raise ValueError('out-of-scope file path; use relative path hello.txt')
    if name == 'write':
        target.write_text(params['content'], encoding='utf-8')
        return {'written': 'hello.txt', 'bytes': target.stat().st_size}
    return {'path': 'hello.txt', 'content': target.read_text(encoding='utf-8')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True)
    ap.add_argument('--model', default='lfm25-8b-a1b-int4')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--repeats', type=int, default=3)
    ap.add_argument('--max-tokens', type=int, default=2048)
    ap.add_argument('--profile', choices=['deterministic', 'official', 'native'], default='deterministic')
    ap.add_argument('--tool-policy', choices=['auto', 'action-required', 'action-named'], default='auto')
    ap.add_argument('--conversation-rounds', type=int, default=1)
    # Staff mode matches OpenAI/OVMS default (omit or true). false remains an explicit opt-in.
    ap.add_argument('--parallel-tool-calls', dest='parallel_tool_calls', action='store_true', default=True)
    ap.add_argument('--no-parallel-tool-calls', dest='parallel_tool_calls', action='store_false')
    args = ap.parse_args()
    if args.conversation_rounds < 1:
        ap.error('--conversation-rounds must be positive')
    args.output.mkdir(parents=True, exist_ok=True)
    tools = []
    for name, description, props, required in [
        ('cwd', 'Get the actual working directory.', {}, []),
        ('write', 'Create hello.txt in the working directory. Use relative path hello.txt.', {'path': {'type': 'string'}, 'content': {'type': 'string'}}, ['path', 'content']),
        ('read', 'Read hello.txt in the working directory. Use relative path hello.txt.', {'path': {'type': 'string'}}, ['path']),
    ]:
        tools.append({'type': 'function', 'function': {'name': name, 'description': description,
            'parameters': {'type': 'object', 'properties': props, 'required': required, 'additionalProperties': False}}})
    results = []
    for stream in [False, True]:
        for repeat in range(args.repeats):
            root = args.output / ('sse' if stream else 'unary') / str(repeat)
            sandbox = root / 'sandbox'
            sandbox.mkdir(parents=True, exist_ok=True)
            # Avoid JSON/Python single-backslash traps (\t/\n/\b) that silently alter Windows paths.
            payload = "O'Brien C:/llm/lfm-test 1.10"
            messages = [{'role': 'system', 'content': (
                'You are an agent with executable tools. Perform requested file actions using tools, '
                'inspect their results, then report. Never claim an action occurred before its result. '
                'A text description of an action does not execute it. Do not invent tool output. '
                'You may emit one or more native tool calls in a turn when needed; use structured tool calls only.'
            )},
                {'role': 'user', 'content': 'Узнай текущий каталог инструментом cwd, создай hello.txt с точным содержимым ' + json.dumps(payload, ensure_ascii=False) + ', затем прочитай файл инструментом read и сообщи результат. Выполни действия сам.'}]
            if args.profile == 'native':
                messages[0]['content'] += (
                    ' Invoke tools with native calls, for example '
                    '<|tool_call_start|>[cwd()]<|tool_call_end|> '
                    'or multiple calls in one envelope: '
                    '<|tool_call_start|>[cwd(), write(path="hello.txt", content="...")]<|tool_call_end|>.'
                )
            if not args.parallel_tool_calls:
                messages[0]['content'] += ' Emit exactly one tool call per assistant turn, then wait for its result.'
            executed = []
            tool_errors = []
            error = None
            round_index = 0
            round_start = 0
            round_results = []
            finish_reason = None
            expected = ['cwd', 'write', 'read']
            for turn in range(8 * args.conversation_rounds):
                body = {'model': args.model, 'messages': messages, 'tools': tools, 'tool_choice': 'auto',
                    'parallel_tool_calls': bool(args.parallel_tool_calls),
                    'temperature': 0, 'seed': 1234 + repeat, 'max_tokens': args.max_tokens, 'stream': stream}
                if args.profile == 'official':
                    body.update(temperature=0.2, top_k=80, repetition_penalty=1.05)
                if args.profile == 'native':
                    body.update(temperature=0.2, top_k=80, repetition_penalty=1.05)
                completed = [x['tool'] for x in executed[round_start:]]
                if completed != expected[:len(completed)]:
                    error = 'unexpected successful tool sequence: ' + repr(completed)
                    break
                if args.tool_policy in ('action-required', 'action-named'):
                    body['tool_choice'] = 'none' if completed == expected else 'required'
                    if args.tool_policy == 'action-named' and completed != expected:
                        body['tool_choice'] = {'type': 'function', 'function': {'name': expected[len(completed)]}}
                (root / f'{turn}.request.json').write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding='utf-8')
                try:
                    req = urllib.request.Request(args.url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(req, timeout=180) as response:
                        raw = response.read()
                    (root / f'{turn}.response.txt').write_bytes(raw)
                    if not stream:
                        choice = json.loads(raw)['choices'][0]
                        assistant = choice['message']
                        finish_reason = choice.get('finish_reason')
                    else:
                        assistant = {'role': 'assistant', 'content': '', 'reasoning_content': '', 'tool_calls': []}
                        indexed = {}
                        finish_reason = None
                        if b'data: [DONE]' not in raw:
                            raise ValueError('SSE missing DONE')
                        for line in raw.splitlines():
                            if not line.startswith(b'data:') or line[5:].strip() == b'[DONE]': continue
                            for choice in json.loads(line[5:]).get('choices', []):
                                if choice.get('finish_reason') is not None:
                                    finish_reason = choice['finish_reason']
                                delta = choice.get('delta', {})
                                for key in ['content', 'reasoning_content']:
                                    assistant[key] += delta.get(key) or ''
                                for call in delta.get('tool_calls', []):
                                    saved = indexed.setdefault(call['index'], {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                                    saved['id'] += call.get('id') or ''
                                    for key in ['name', 'arguments']:
                                        saved['function'][key] += call.get('function', {}).get(key) or ''
                        assistant['tool_calls'] = list(indexed.values())
                    messages.append(assistant)
                    calls = assistant.get('tool_calls') or []
                    if not calls:
                        final_ok = (completed == expected and finish_reason == 'stop'
                                    and payload in (assistant.get('content') or ''))
                        round_results.append({'round': round_index, 'passed': final_ok,
                                              'finish_reason': finish_reason, 'final': assistant})
                        if not final_ok or round_index + 1 == args.conversation_rounds:
                            break
                        round_index += 1
                        round_start = len(executed)
                        # Keep the entire real conversation, including previous tool results.
                        # Read before editing to make the next task depend on prior file state.
                        expected = ['read', 'write', 'read']
                        payload = "O'Brien C:/llm/lfm-test 1.10 revision " + str(round_index)
                        messages.append({'role': 'user', 'content': (
                            'Continue in the same directory. Read hello.txt using read, then replace its content with '
                            + json.dumps(payload) + '. Read it back and report its exact new content. Use relative path hello.txt.')})
                        continue
                    if not args.parallel_tool_calls and len(calls) != 1:
                        raise ValueError('parallel_tool_calls=false violated: got %d calls' % len(calls))
                    for call in calls:
                        name = call['function']['name']
                        try:
                            params = json.loads(call['function']['arguments'])
                            value = execute_tool(sandbox, name, params)
                            executed.append({'tool': name, 'arguments': params, 'result': value})
                        except (ValueError, KeyError, TypeError, OSError) as exc:
                            # Real agent harnesses return execution errors to the model,
                            # preserving call IDs and allowing bounded correction next turn.
                            value = {'error': str(exc)}
                            tool_errors.append({'turn': turn, 'id': call['id'], 'tool': name, **value})
                        messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(value, ensure_ascii=False)})
                except Exception as exc:
                    if isinstance(exc, urllib.error.HTTPError):
                        (root / f'{turn}.error-response.txt').write_bytes(exc.read())
                    error = repr(exc)
                    break
            names = [x['tool'] for x in executed]
            target = sandbox / 'hello.txt'
            passed = (not error and len(round_results) == args.conversation_rounds
                      and all(r['passed'] for r in round_results) and target.exists()
                      and target.read_text(encoding='utf-8') == payload)
            results.append({'stream': stream, 'repeat': repeat, 'profile': args.profile, 'tool_policy': args.tool_policy,
                            'parallel_tool_calls': bool(args.parallel_tool_calls),
                            'verdict': 'PASS' if passed else 'FAIL', 'executed': executed, 'error': error,
                            'tool_errors': tool_errors,
                            'rounds': round_results, 'finish_reason': finish_reason, 'final': messages[-1]})
            (args.output / 'RESULT.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            print('stream', stream, 'repeat', repeat, 'PASS' if passed else 'FAIL', names, error, flush=True)
    return 0 if results and all(r['verdict'] == 'PASS' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
