"""Pinned R1 output contract and bounded cleanup for an owned process only."""
import re
import subprocess

# id -> (desired acceptance, expected schema error, known inherited defect)
EXPECTED_ROWS = {
    'empty_min0_epsilon': (1, 0, 0),
    'empty_min0_space': (0, 0, 0),
    'empty_min0_tab': (0, 0, 0),
    'empty_min0_lf': (0, 0, 0),
    'closed_min1_unsatisfiable': (0, 1, 0),
    'open_min1_parameter': (1, 0, 0),
    'open_min1_empty': (0, 0, 0),
    'open_min1_space': (0, 0, 0),
    'declared_min1_parameter': (1, 0, 0),
    'declared_min1_empty': (0, 0, 0),
    'required_declared_unset_max_parameter': (1, 0, 0),
    'required_declared_unset_max_empty': (0, 0, 0),
    'explicit_max0_epsilon': (1, 0, 0),
    'explicit_max0_parameter': (0, 0, 0),
    'explicit_max0_space': (0, 0, 0),
    'required_max0_unsatisfiable': (0, 1, 0),
    'required_empty_props_empty_OPEN': (0, 0, 1),
    'required_empty_props_spaces_OPEN': (0, 0, 1),
    'required_undeclared_open_empty_OPEN': (0, 0, 1),
    'required_undeclared_open_parameter': (1, 0, 0),
    'nested_empty_braces': (1, 0, 0),
    'json_empty_braces': (1, 0, 0),
    'json_empty_spaced_braces': (1, 0, 0),
    'json_no_bare_epsilon': (0, 0, 0),
    'json_closed_min1_unsatisfiable': (0, 1, 0),
    'json_declared_min1_empty': (0, 0, 0),
    'json_declared_min1_value': (1, 0, 0),
    'json_required_empty_props_OPEN': (0, 0, 1),
}
ROW = re.compile(r'ROW (\S+) status=(\S+) compile_error=([01]) accepted=([01]) '
                 r'desired=([01]) phase=(\S+) schema_specific_error=([01])')
SUMMARY = 'SUMMARY rows=28 passed=24 open=4 unexpected=0 ACCEPTED=NO'


def validate_matrix_log(log, exit_code):
    """Return OPEN only for the exact pinned selection and its known residuals."""
    errors, seen = [], set()
    row_lines = [line for line in log.splitlines() if line.startswith('ROW ')]
    if exit_code != 2:
        errors.append('Expected native OPEN exit2')
    if len(row_lines) != len(EXPECTED_ROWS):
        errors.append('Wrong row count')
    for line in row_lines:
        match = ROW.fullmatch(line)
        if not match:
            errors.append('Malformed ROW line')
            continue
        name, status, compile_error, accepted, desired, phase, schema_error = match.groups()
        if name in seen:
            errors.append('Duplicate row: ' + name)
        seen.add(name)
        if name not in EXPECTED_ROWS:
            errors.append('Unexpected row: ' + name)
            continue
        want, compilation_failure, opened = EXPECTED_ROWS[name]
        actual = (int(desired), int(compile_error), int(accepted), phase, int(schema_error), status)
        expected = (want, compilation_failure, 1 if opened else want,
                    'schema_conversion' if compilation_failure else 'matching',
                    compilation_failure, 'EXPECTED_FAIL_OPEN' if opened else 'PASS')
        if actual != expected:
            errors.append('Inconsistent row semantics: ' + name)
    if seen != set(EXPECTED_ROWS):
        errors.append('Selected row names differ from pinned contract')
    summaries = [line for line in log.splitlines() if line.startswith('SUMMARY')]
    if summaries != [SUMMARY]:
        errors.append('Missing, duplicate or inconsistent SUMMARY')
    return {'valid': not errors, 'status': 'OPEN_EXPECTED_FAILURES' if not errors else 'FAILED_OR_CHANGED_REVIEW',
            'errors': errors, 'accepted': False}


def terminate_owned_process(proc, stream, cleanup_timeout=30, wait_timeout=5):
    """Bound both taskkill and reaping; uncertainty never proves tree cleanup."""
    result = {'timed_out': True, 'exit_code': None, 'cleanup_error': None}
    errors = []
    if proc.poll() is not None:
        result['cleanup_skipped_parent_exited'] = True
        errors.append('Parent already exited; descendant cleanup unconfirmed')
    else:
        try:
            killed = subprocess.run(['rtk', 'proxy', 'taskkill', '/PID', str(proc.pid), '/T', '/F'],
                                    stdout=stream, stderr=subprocess.STDOUT, check=False,
                                    timeout=cleanup_timeout)
            result['cleanup_exit_code'] = killed.returncode
            if killed.returncode != 0:
                errors.append('Owned-tree cleanup returned nonzero')
        except (subprocess.TimeoutExpired, OSError) as error:
            errors.append('Owned-tree cleanup failed: ' + str(error))
    try:
        result['exit_code'] = proc.wait(timeout=wait_timeout)
    except (subprocess.TimeoutExpired, OSError):
        errors.append('Owned process exit not confirmed')
    result['cleanup_error'] = '; '.join(errors) or None
    return result


def validate_original_log(log, exit_code):
    """Require one exact summary and one mask observation for each lazy mode."""
    summaries=[line for line in log.splitlines() if line.startswith('SUMMARY')]
    masks=[line for line in log.splitlines() if line.startswith('ACTUAL_MASK')]
    expected=['ACTUAL_MASK lazy=0 whitespace_tokens=425 allowed=0',
              'ACTUAL_MASK lazy=1 whitespace_tokens=425 allowed=0']
    return exit_code==0 and summaries==['SUMMARY failures=0'] and sorted(masks)==expected
