"""Agent acceptance must reject empty/truncated finals and resume a conversation."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('agent', Path(__file__).with_name('lfm-agent-loop.py'))
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class AgentAcceptance(unittest.TestCase):
    def test_forward_slash_absolute_sandbox_path_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            value = agent.execute_tool(sandbox, 'write', {
                'path': (sandbox / 'hello.txt').resolve().as_posix(), 'content': 'one'})
            self.assertEqual(value['bytes'], 3)

    def test_tool_error_can_be_returned_without_executing_outside_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                agent.execute_tool(Path(tmp), 'write', {'path': '../outside.txt', 'content': 'bad'})

    def run_case(self, final, finish='stop', extra=(), invalid_once=False):
        payload = "O'Brien C:/llm/lfm-test 1.10"
        requests = []
        counts = {False: 0, True: 0}
        rejected = set()
        def respond(req, timeout):
            body = json.loads(req.data)
            requests.append(body)
            stream = body['stream']
            turn = counts[stream] % 4
            round_index = counts[stream] // 4
            counts[stream] += 1
            current_payload = payload if round_index == 0 else payload + ' revision ' + str(round_index)
            final_text = current_payload if final == payload else final
            message = {'role': 'assistant', 'content': final_text if turn == 3 else ''}
            reason = finish if turn == 3 else 'tool_calls'
            if turn < 3:
                name = (['cwd', 'write', 'read'] if round_index == 0 else ['read', 'write', 'read'])[turn]
                params = {} if name == 'cwd' else {'path': 'hello.txt'}
                if turn == 1:
                    params['content'] = current_payload
                    if invalid_once and stream not in rejected:
                        rejected.add(stream)
                        params['path'] = '../outside.txt'
                        counts[stream] -= 1
                message['tool_calls'] = [{'id': 'call' + str(turn), 'type': 'function',
                    'function': {'name': name, 'arguments': json.dumps(params)}}]
            if stream:
                for call in message.get('tool_calls', []):
                    call['index'] = 0
                data = 'data: ' + json.dumps({'choices': [{'delta': message, 'finish_reason': reason}]}) + '\n\ndata: [DONE]\n\n'
            else:
                data = json.dumps({'choices': [{'message': message, 'finish_reason': reason}]})
            return io.BytesIO(data.encode())
        with tempfile.TemporaryDirectory() as tmp:
            argv = ['agent', '--url', 'http://unused', '--output', tmp, '--repeats', '1', *extra]
            with patch.object(sys, 'argv', argv), patch.object(agent.urllib.request, 'urlopen', respond), contextlib.redirect_stdout(io.StringIO()):
                status = agent.main()
            rows = json.loads(Path(tmp, 'RESULT.json').read_text())
            self.assertEqual(status, 0 if all(row['verdict'] == 'PASS' for row in rows) else 1)
            return rows, requests

    def test_empty_final_is_failure_after_three_successful_tools(self):
        rows, _ = self.run_case('  ')
        self.assertTrue(all(row['verdict'] == 'FAIL' for row in rows))

    def test_length_final_is_failure_even_with_visible_content(self):
        rows, _ = self.run_case("O'Brien C:/llm/lfm-test 1.10", 'length')
        self.assertTrue(all(row['verdict'] == 'FAIL' for row in rows))

    def test_valid_final_passes(self):
        rows, _ = self.run_case("O'Brien C:/llm/lfm-test 1.10")
        self.assertTrue(all(row['verdict'] == 'PASS' for row in rows))

    def test_three_user_rounds_keep_history_and_release_tool_constraint_for_final(self):
        rows, requests = self.run_case("O'Brien C:/llm/lfm-test 1.10", extra=(
            '--conversation-rounds', '3', '--tool-policy', 'action-named'))
        self.assertTrue(all(row['verdict'] == 'PASS' and len(row['executed']) == 9 for row in rows))
        for stream in (False, True):
            bodies = [body for body in requests if body['stream'] == stream]
            self.assertEqual(len(bodies), 12)
            self.assertEqual([body['tool_choice'] for body in bodies[3::4]], ['none'] * 3)
            self.assertEqual(bodies[4]['tool_choice']['function']['name'], 'read')
            self.assertEqual(sum(m['role'] == 'user' for m in bodies[-1]['messages']), 3)
            self.assertEqual(sum(m['role'] == 'tool' for m in bodies[-1]['messages']), 9)

    def test_bad_path_is_returned_as_tool_result_and_model_can_recover(self):
        rows, requests = self.run_case("O'Brien C:/llm/lfm-test 1.10", invalid_once=True)
        self.assertTrue(all(row['verdict'] == 'PASS' and len(row['tool_errors']) == 1 for row in rows))
        for stream in (False, True):
            bodies = [body for body in requests if body['stream'] == stream]
            returned = bodies[2]['messages'][-1]
            self.assertEqual(returned['role'], 'tool')
            self.assertEqual(returned['tool_call_id'], 'call1')
            self.assertIn('out-of-scope', returned['content'])


if __name__ == '__main__':
    unittest.main()
