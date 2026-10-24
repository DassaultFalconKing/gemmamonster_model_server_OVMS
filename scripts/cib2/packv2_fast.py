"""Fast, offline-only CIB2 generation seal/verify implementation.

A compatible implementation of packv2_pipeline.py seal/verify. Does not alter
OTDPACK1, placement, model IR, native OTD readers or C6 runtime. Fast mode
is structural-only: release gates MUST use verify --mode full.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import struct
import sys
import tempfile
import threading
import time
from uuid import uuid4

try:
    from . import verify_pack_v1 as pv
except ImportError:
    import verify_pack_v1 as pv

MIB = 1 << 20
PROGRESS_STEP = 64 * MIB
MAX_WORKERS = 64
MAX_PACKS = 512
WRITE_MASK = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


class SealError(ValueError):
    pass


def _workers(value):
    n = min(8, os.cpu_count() or 4) if value is None else value
    if type(n) is not int or not 1 <= n <= MAX_WORKERS:
        raise SealError("workers must be 1..64")
    return n


def _validate_opt(value, choices, name):
    if value not in choices:
        raise SealError(f"invalid {name}: {value}")
    return value


def _safe_file(path):
    if path.is_symlink() or not path.is_file():
        raise SealError(f"missing/unsafe pack: {path.name}")


def _snapshot(fh):
    st = os.fstat(fh.fileno())
    if not stat.S_ISREG(st.st_mode):
        raise SealError("not a regular pack file")
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)


def _structure(fh, name, entry):
    """Check exact native pack geometry, header, placement, tables, length.

    No payload record verification. This is an *explicitly weaker* fast mode.
    """
    before = _snapshot(fh)
    if before[2] < pv.ALIGNMENT:
        raise SealError(f"truncated pack: {name}")
    fh.seek(0)
    header_raw = fh.read(pv.HEADER.size)
    if len(header_raw) != pv.HEADER.size:
        raise SealError("truncated native header")
    fields = pv.HEADER.unpack(header_raw)
    magic, version, header_size = fields[:3]
    key, n, stride, records_at, placement_at, checksums_at = fields[3:9]
    sizes, offsets, digest = list(fields[9:18]), list(fields[18:27]), fields[27]
    if (magic, version, header_size) != (pv.MAGIC, pv.VERSION, pv.ALIGNMENT):
        raise SealError(f"bad OTDPACK1 header: {name}")
    if pv.fnv_update(pv.FNV_OFFSET, header_raw[:-8] + b"\0" * 8) != digest:
        raise SealError(f"header checksum invalid: {name}")
    if not (1 <= n <= pv.DEFAULT_MAX_EXPERTS) or key != int(entry['pack_layer_key'], 16) or n != entry['expert_count']:
        raise SealError(f"wrong pack identity/experts: {name}")
    if name != f"otd-{key:016x}.pack":
        raise SealError("pack basename/key mismatch")
    expected_offsets, payload, expected_stride, expected_checksums, expected_records = pv.canonical_layout(sizes, n)
    if (offsets != expected_offsets or stride != expected_stride or placement_at != pv.ALIGNMENT or
            checksums_at != expected_checksums or records_at != expected_records):
        raise SealError(f"noncanonical pack geometry: {name}")
    expected_size = records_at + n * stride
    if before[2] < expected_size:
        raise SealError(f"truncated native records: {name}")
    # Native allows trailing bytes; retain its existing semantics.
    fh.seek(placement_at)
    placement_raw = fh.read(n * 4)
    if len(placement_raw) != n * 4:
        raise SealError("truncated placement table")
    positions = list(struct.unpack('<' + 'I' * n, placement_raw))
    if sorted(positions) != list(range(n)) or positions != entry['placement']:
        raise SealError(f"pack placement differs from compiled build plan: {name}")
    fh.seek(checksums_at)
    checksum_raw = fh.read(n * 8)
    if len(checksum_raw) != n * 8:
        raise SealError("truncated record checksums")
    checksums = struct.unpack('<' + 'Q' * n, checksum_raw)
    if _snapshot(fh) != before:
        raise SealError(f"pack mutated during header check: {name}")
    return dict(snapshot=before, header=header_raw, placement_raw=placement_raw,
                checksum_raw=checksum_raw, checksums=checksums, stride=stride, n=n,
                records_at=records_at, payload=payload, size=before[2])


def _check_still(fh, info, name):
    if _snapshot(fh) != info['snapshot']:
        raise SealError(f"source pack changed during seal: {name}")
    fh.seek(0)
    if fh.read(len(info['header'])) != info['header']:
        raise SealError(f"source header changed: {name}")
    fh.seek(pv.ALIGNMENT)
    if fh.read(len(info['placement_raw'])) != info['placement_raw']:
        raise SealError(f"source placement changed: {name}")
    fh.seek(pv.ALIGNMENT + pv.align_up(info['n'] * 4, 8))
    if fh.read(len(info['checksum_raw'])) != info['checksum_raw']:
        raise SealError(f"source checksums changed: {name}")


def _read_full(fh, info, progress=None):
    """Compute SHA256 and payload FNV over one sequential physical-file pass."""
    fh.seek(0)
    overall = hashlib.sha256()
    n = info['n']
    inverse = [None] * n
    for logical, physical in enumerate(struct.unpack('<' + 'I' * n, info['placement_raw'])):
        inverse[physical] = logical
    calculated = [pv.FNV_OFFSET] * n
    pos = 0
    while pos < info['size']:
        part = fh.read(min(MIB, info['size'] - pos))
        if not part:
            raise SealError("short full verification read")
        overall.update(part)
        start, end = pos, pos + len(part)
        while start < end:
            if start < info['records_at']:
                start = min(end, info['records_at'])
                continue
            relative = start - info['records_at']
            physical, rem = divmod(relative, info['stride'])
            if physical >= n:
                break  # trailing bytes are included in SHA but not in record checksum
            length = min(end - start, info['stride'] - rem)
            if rem < info['payload']:
                valid = min(length, info['payload'] - rem)
                logical = inverse[physical]
                calculated[logical] = pv.fnv_update(
                    calculated[logical], part[start - pos:start - pos + valid]
                )
            start += length
        pos += len(part)
        if progress is not None:
            progress(len(part))
    if calculated != list(info['checksums']):
        raise SealError("native expert payload checksum mismatch")
    return overall.hexdigest()


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


class Recorder:
    """Single writer for JSONL events, deterministic metrics and throttled progress."""

    def __init__(self, op, *, root, workers, progress='auto', log_file=None, metrics_file=None,
                 materialize=None, hardlink_policy=None, fsync_policy=None, verify_mode=None):
        self.op = op
        self.run_id = str(uuid4())
        self.workers = _workers(workers)
        self.mode = _validate_opt(progress, ('auto', 'tty', 'jsonl', 'off'), 'progress')
        if self.mode == 'auto':
            self.mode = 'tty' if sys.stderr.isatty() else 'jsonl'
        self.root = Path(root)
        self.log_file = Path(log_file) if log_file else None
        self.metrics_file = Path(metrics_file) if metrics_file else self.root / 'receipts' / f'{op}-{self.run_id}.json'
        self.metrics = {
            'schema': 'cib2.packv2_seal_metrics.v1', 'run_id': self.run_id,
            'op': op, 'status': 'REJECTED', 'wall_s': 0, 'cpu_s': 0,
            'workers': self.workers, 'workers_used_max': 0,
            'materialize': materialize, 'hardlink_policy': hardlink_policy if materialize == 'hardlink' else None,
            'fsync_policy': fsync_policy, 'post_seal_verify': verify_mode if op == 'seal' else None,
            'verification_mode': verify_mode, 'pack_count': 0, 'bytes_total': 0,
            'bytes_read': 0, 'bytes_written': 0, 'packs_ok': 0, 'packs_failed': 0,
            'phase_timings_s': {'materialize': 0, 'post_seal_verify': 0, 'rename': 0, 'verify': 0},
            'rate_bps_avg': 0, 'rate_bps_peak': 0, 'eta_last_s': None,
            'generation': None, 'generation_sha256': None, 'progress_mode': self.mode,
            'host': {'python': platform.python_version(), 'platform': sys.platform, 'cpu_count': os.cpu_count() or 0},
        }
        self.lock = threading.RLock()
        self.t0 = time.perf_counter()
        self.cpu0 = time.process_time()
        self.bytes_done = 0
        self.last_emit = 0.0
        self.last_mark = 0
        self.active = 0
        self.logstream = None
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self.logstream = self.log_file.open('a', encoding='utf-8', newline='\n')

    def emit(self, event, *, stderr=False, **kwargs):
        record = {'ts': _utc(), 'event': event, 'op': self.op, 'run_id': self.run_id, **kwargs}
        line = json.dumps(record, ensure_ascii=True, sort_keys=True)
        with self.lock:
            if self.logstream is not None:
                self.logstream.write(line + '\n')
                self.logstream.flush()
            if stderr and self.mode == 'jsonl':
                print(line, file=sys.stderr, flush=True)

    def begin(self, count, total, *, phase, **kwargs):
        with self.lock:
            self.metrics['pack_count'] = count
            self.metrics['packs_ok'] = 0  # each phase reports its own completed pack count
            self.metrics['bytes_total'] = total
            self.bytes_done = 0
            self.last_emit = 0.0
            self.last_mark = 0
            self.emit('start', stderr=True, pack_count=count, bytes_total=total, phase=phase,
                      workers=self.workers, **kwargs)
            if self.mode == 'tty':
                print(f'{self.op}: {count} packs, {total/MIB/1024:.2f} GiB, workers={self.workers}', file=sys.stderr)

    def worker_enter(self, pack, phase):
        with self.lock:
            self.active += 1
            self.metrics['workers_used_max'] = max(self.metrics['workers_used_max'], self.active)
            self.emit('pack_start', stderr=False, pack=pack, phase=phase)

    def worker_exit(self):
        with self.lock:
            self.active -= 1

    def advance(self, count, phase, *, force=False):
        with self.lock:
            self.bytes_done += count
            now = time.perf_counter()
            if not force and (self.bytes_done - self.last_mark < PROGRESS_STEP or now - self.last_emit < 0.1):
                return
            self.last_emit = now
            self.last_mark = self.bytes_done
            elapsed = max(now - self.t0, 0.001)
            speed = self.bytes_done / elapsed
            total = self.metrics['bytes_total']
            eta = max(0, (total - self.bytes_done) / speed) if speed else None
            self.metrics['rate_bps_peak'] = max(self.metrics['rate_bps_peak'], speed)
            self.metrics['eta_last_s'] = eta
            if self.mode == 'tty':
                print(f'\r{self.op} {self.bytes_done/MIB/1024:.2f}/{total/MIB/1024:.2f} GiB '
                      f'{speed/MIB:.1f} MiB/s ETA {eta:.0f}s workers={self.workers}    ',
                      file=sys.stderr, end='', flush=True)
            else:
                self.emit('progress', stderr=True, phase=phase, bytes_done=self.bytes_done,
                          bytes_total=total, rate_bps=int(speed), eta_s=round(eta or 0, 2), workers=self.workers)

    def pack_done(self, pack, phase, *, logical_bytes, bytes_read, bytes_written):
        with self.lock:
            self.metrics['packs_ok'] += 1
            self.metrics['bytes_read'] += bytes_read
            self.metrics['bytes_written'] += bytes_written
            self.advance(0, phase, force=True)
            elapsed = max(time.perf_counter() - self.t0, 0.001)
            self.emit('pack_done', stderr=True, pack=pack, phase=phase, i=self.metrics['packs_ok'],
                      n=self.metrics['pack_count'], bytes_done=self.bytes_done,
                      bytes_total=self.metrics['bytes_total'], rate_bps=int(self.bytes_done/elapsed),
                      eta_s=self.metrics['eta_last_s'], workers=self.workers,
                      pack_bytes=logical_bytes)

    def fail(self, exc, *, pack=None):
        with self.lock:
            if pack is not None:
                self.metrics['packs_failed'] += 1
            self.metrics['error'] = f'{type(exc).__name__}: {exc}'
            self.emit('pack_error' if pack else 'reject', stderr=True, pack=pack,
                      exc_type=type(exc).__name__, error=str(exc))

    def finish(self, *, success, generation=None, digest=None):
        with self.lock:
            self.metrics['status'] = 'OK' if success else 'REJECTED'
            self.metrics['wall_s'] = round(time.perf_counter() - self.t0, 4)
            self.metrics['cpu_s'] = round(time.process_time() - self.cpu0, 4)
            self.metrics['rate_bps_avg'] = round(self.metrics['bytes_total'] / max(self.metrics['wall_s'], .001), 2)
            self.metrics['generation'] = generation
            self.metrics['generation_sha256'] = digest
            self.emit('done' if success else 'reject', stderr=True, status=self.metrics['status'], generation=generation)
            if self.mode == 'tty':
                print(file=sys.stderr)
            try:
                self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
                temp = self.metrics_file.with_name(self.metrics_file.name + '.' + self.run_id + '.tmp')
                with temp.open('x', encoding='utf-8') as fh:
                    json.dump(self.metrics, fh, sort_keys=True, indent=2)
                    fh.write('\n')
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(temp, self.metrics_file)
            finally:
                if self.logstream is not None:
                    self.logstream.close()


def _fsync_dir(path):
    if os.name == 'nt':
        return  # Windows directory fsync not portable; atomic rename + manifest fsync.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ordered_jobs(jobs, workers, work):
    # Main thread executes serial case; ThreadPoolExecutor does bounded per-file jobs.
    if workers == 1:
        return [work(j) for j in jobs]
    results = [None] * len(jobs)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, j): idx for idx, j in enumerate(jobs)}
        try:
            for future in as_completed(futures):
                results[futures[future]] = future.result()
        except BaseException:
            for pending in futures:
                pending.cancel()
            raise
    return results


def _materialize_one(job, dest, kind, link_policy, sync, recorder):
    path, entry = job
    name = path.name
    recorder.worker_enter(name, 'materialize')
    try:
        _safe_file(path)
        with path.open('rb') as source:
            info = _structure(source, name, entry)
            if kind == 'hardlink':
                if link_policy in ('require-readonly', 'chmod-readonly') and (os.fstat(source.fileno()).st_mode & WRITE_MASK):
                    if link_policy == 'require-readonly':
                        raise SealError(f'hardlink source is writable: {name}')
                    os.chmod(path, os.fstat(source.fileno()).st_mode & ~WRITE_MASK)
                    info['snapshot'] = _snapshot(source)
                if os.stat(path).st_dev != os.stat(dest.parent).st_dev:
                    raise SealError('hardlink requires the same volume')
                os.link(path, dest)
                if link_policy == 'allow-shared' and os.fstat(source.fileno()).st_mode & WRITE_MASK:
                    recorder.emit('warning', stderr=True, pack=name, message='writable hardlinked source shares inode with generation')
                # This SHA pass protects the manifest identity but does not prove record FNV.
                source.seek(0)
                digest = hashlib.sha256()
                done = 0
                while done < info['size']:
                    block = source.read(min(MIB, info['size'] - done))
                    if not block:
                        raise SealError('short source read during hardlink SHA')
                    digest.update(block)
                    done += len(block)
                    recorder.advance(len(block), 'materialize')
                actual_bytes_read = done
                actual_bytes_written = 0
                if os.stat(dest).st_ino != os.fstat(source.fileno()).st_ino:
                    raise SealError('hardlink inode differs from source')
            else:
                source.seek(0)
                digest = hashlib.sha256()
                done = 0
                with dest.open('xb') as output:
                    while done < info['size']:
                        block = source.read(min(MIB, info['size'] - done))
                        if not block:
                            raise SealError('short source read during copy')
                        digest.update(block)
                        output.write(block)
                        done += len(block)
                        recorder.advance(len(block), 'materialize')
                    output.flush()
                    if sync == 'each':
                        os.fsync(output.fileno())
                actual_bytes_read = actual_bytes_written = done
                if dest.stat().st_size != info['size']:
                    raise SealError('copied pack has wrong size')
            _check_still(source, info, name)
            with dest.open('rb') as generated:
                new_info = _structure(generated, name, entry)
                if new_info['size'] != info['size']:
                    raise SealError('materialized header/size mismatch')
            recorder.pack_done(name, 'materialize', logical_bytes=info['size'],
                               bytes_read=actual_bytes_read, bytes_written=actual_bytes_written)
            return {'file': name, 'pack_layer_key': entry['pack_layer_key'],
                    'pack_sha256': digest.hexdigest(), 'pack_bytes': info['size'],
                    'expert_count': entry['expert_count'], 'profile_sha256': entry['profile_sha256'],
                    'native_plan_sha256': entry['native_plan_sha256'],
                    'native_residency_sha256': entry['native_residency_sha256'],
                    'resident_tiers': entry['resident_tiers'], 'placement': entry['placement'],
                    'native_payload_format': 'OTDPACK1', 'record_stride': info['stride']}
    except BaseException as exc:
        recorder.fail(exc, pack=name)
        raise
    finally:
        recorder.worker_exit()


def _manifest(v2, folder):
    if folder.is_symlink() or not folder.is_dir():
        raise SealError('generation directory missing or symlinked')
    manifest = v2._read_json(folder / 'manifest.v2.json')
    expected_keys = {'schema', 'pack_format', 'v2_features', 'runtime_acceptance',
                     'source', 'trace_sha256', 'plan_sha256', 'packs', 'generation_sha256'}
    if type(manifest) is not dict or set(manifest) != expected_keys or manifest['schema'] != v2.MANIFEST_SCHEMA or manifest['pack_format'] != 'OTDPACK1':
        raise SealError('wrong V2 manifest contract')
    raw = dict(manifest)
    generation_sha = raw.pop('generation_sha256')
    digest = hashlib.sha256(v2._canonical(raw)).hexdigest()
    if generation_sha != digest:
        raise SealError('manifest generation checksum mismatch')
    if folder.name != f'generation-{digest}' and not folder.name.startswith('.generation-'):
        raise SealError('generation directory name mismatch')
    packs = manifest['packs']
    expected_entry = {'file', 'pack_layer_key', 'pack_sha256', 'pack_bytes',
                      'expert_count', 'profile_sha256', 'native_plan_sha256',
                      'native_residency_sha256', 'resident_tiers', 'placement',
                      'native_payload_format', 'record_stride'}
    if type(packs) is not list or not 1 <= len(packs) <= MAX_PACKS:
        raise SealError('invalid V2 pack count')
    seen = set()
    for e in packs:
        if type(e) is not dict or set(e) != expected_entry:
            raise SealError('invalid manifest entry')
        key, name = e['pack_layer_key'], e['file']
        if (type(key) is not str or len(key) != 16 or any(x not in '0123456789abcdef' for x in key) or
                name != f'otd-{key}.pack' or name in seen):
            raise SealError('invalid/duplicate pack name')
        if e['native_payload_format'] != 'OTDPACK1':
            raise SealError('invalid pack format')
        if (type(e['pack_bytes']) is not int or e['pack_bytes'] < 0 or
                type(e['pack_sha256']) is not str or len(e['pack_sha256']) != 64 or
                any(c not in '0123456789abcdef' for c in e['pack_sha256'])):
            raise SealError('invalid pack size/SHA256')
        seen.add(name)
    if {p.name for p in folder.iterdir()} != (seen | {'manifest.v2.json'}):
        raise SealError('unexpected files in generation')
    return manifest, digest


def _verify_pack(job, folder, mode, recorder):
    name, entry = job
    recorder.worker_enter(name, 'verify')
    try:
        path = folder / name
        _safe_file(path)
        with path.open('rb') as source:
            info = _structure(source, name, entry)
            if info['size'] != entry['pack_bytes'] or info['stride'] != entry['record_stride']:
                raise SealError(f'V2 pack size/stride mismatch: {name}')
            digest = _read_full(source, info, lambda n: recorder.advance(n, 'verify')) if mode == 'full' else None
            _check_still(source, info, name)
            if digest is not None and digest != entry['pack_sha256']:
                raise SealError(f'V2 full SHA256 mismatch: {name}')
        if mode == 'fast':
            recorder.advance(info['size'], 'verify', force=True)
        recorder.pack_done(name, 'verify', logical_bytes=info['size'],
                           bytes_read=info['size'] if mode == 'full' else
                           (len(info['header']) + 2*len(info['placement_raw']) + 2*len(info['checksum_raw'])),
                           bytes_written=0)
        return True
    except BaseException as exc:
        recorder.fail(exc, pack=name)
        raise
    finally:
        recorder.worker_exit()


def _verify_impl(v2, folder, mode, recorder):
    manifest, digest = _manifest(v2, folder)
    packs = manifest['packs']
    jobs = [(x['file'], x) for x in packs]
    total = sum(x['pack_bytes'] for x in packs)
    recorder.begin(len(jobs), total, phase='verify', mode=mode)
    start = time.perf_counter()
    _ordered_jobs(jobs, recorder.workers, lambda job: _verify_pack(job, folder, mode, recorder))
    recorder.metrics['phase_timings_s']['verify'] = round(time.perf_counter() - start, 4)
    return {'status': 'VERIFIED_OFFLINE', 'generation': digest, 'pack_count': len(packs),
            'native_payload_format': 'OTDPACK1', 'runtime_acceptance': 'NO',
            'promotion_authorized': False, 'pack_dir': str(folder.resolve()),
            'verification_mode': mode, 'payload_integrity_checked': mode == 'full'}


def verify_generation(v2, generation_dir, *, mode='full', workers=None,
                      progress='auto', log_file=None, metrics_file=None):
    folder = Path(generation_dir)
    _validate_opt(mode, ('fast', 'full'), 'verify mode')
    recorder = Recorder('verify', root=folder.parent, workers=workers, progress=progress,
                        log_file=log_file, metrics_file=metrics_file, verify_mode=mode)
    try:
        result = _verify_impl(v2, folder, mode, recorder)
        recorder.finish(success=True, generation=folder.name, digest=result['generation'])
        return result
    except BaseException as exc:
        recorder.fail(exc)
        recorder.finish(success=False)
        raise


def _result_from_seal(target, digest, n, verify_mode):
    return {'status': 'VERIFIED_OFFLINE' if verify_mode != 'none' else 'SEALED_UNVERIFIED',
            'generation': digest, 'pack_count': n, 'native_payload_format': 'OTDPACK1',
            'runtime_acceptance': 'NO', 'promotion_authorized': False,
            'pack_dir': str(target.resolve()), 'verification_mode': verify_mode,
            'payload_integrity_checked': verify_mode == 'full'}


def seal_generation(v2, plans_dir, native_packs, output_root, *,
                    post_seal_verify='fast', materialize='copy', hardlink_policy='require-readonly',
                    fsync='dir', workers=None, progress='auto', log_file=None, metrics_file=None):
    _validate_opt(post_seal_verify, ('fast', 'full', 'none'), 'post-seal verify')
    _validate_opt(materialize, ('copy', 'hardlink'), 'materialize')
    _validate_opt(hardlink_policy, ('require-readonly', 'chmod-readonly', 'allow-shared'), 'hardlink policy')
    _validate_opt(fsync, ('dir', 'each', 'none'), 'fsync')
    root = Path(output_root)
    recorder = Recorder('seal', root=root, workers=workers, progress=progress,
                        log_file=log_file, metrics_file=metrics_file,
                        materialize=materialize, hardlink_policy=hardlink_policy,
                        fsync_policy=fsync, verify_mode=post_seal_verify)
    temporary = None
    generation = None
    digest = None
    try:
        plan = v2._read_plans(Path(plans_dir))
        input_dir = Path(native_packs)
        if root.is_symlink() or not root.is_dir() or input_dir.is_symlink() or not input_dir.is_dir():
            raise SealError('native packs and generation root must be real directories')
        if root.resolve() == input_dir.resolve():
            raise SealError('native pack source equals generation root')
        jobs = [(input_dir / f"otd-{e['pack_layer_key']}.pack", e) for e in plan['layers']]
        for path, _ in jobs:
            _safe_file(path)
        total = sum(path.stat().st_size for path, _ in jobs)
        recorder.begin(len(jobs), total, phase='materialize', materialize=materialize,
                       post_seal_verify=post_seal_verify)
        temporary = Path(tempfile.mkdtemp(prefix='.generation-', dir=root))
        start = time.perf_counter()
        entries = _ordered_jobs(jobs, recorder.workers, lambda job: _materialize_one(
            job, temporary / job[0].name, materialize, hardlink_policy, fsync, recorder))
        recorder.metrics['phase_timings_s']['materialize'] = round(time.perf_counter() - start, 4)
        inner = {'schema': v2.MANIFEST_SCHEMA, 'pack_format': 'OTDPACK1',
                 'v2_features': ['immutable_generation', 'profile_placement', 'full_pack_digest'],
                 'runtime_acceptance': 'NO', 'source': plan['source'],
                 'trace_sha256': plan['trace_sha256'],
                 'plan_sha256': hashlib.sha256(v2._canonical(plan)).hexdigest(),
                 'packs': sorted(entries, key=lambda x: x['pack_layer_key'])}
        digest = hashlib.sha256(v2._canonical(inner)).hexdigest()
        generation = f'generation-{digest}'
        manifest = {**inner, 'generation_sha256': digest}
        target = root / generation
        v2._atomic_json(temporary / 'manifest.v2.json', manifest)
        if fsync in ('dir', 'each'):
            _fsync_dir(temporary)
        if post_seal_verify != 'none':
            recorder.emit('phase', stderr=True, phase='post_seal_verify', mode=post_seal_verify)
            start = time.perf_counter()
            # Reset logical progress for the verification phase.
            _verify_impl(v2, temporary, post_seal_verify, recorder)
            recorder.metrics['phase_timings_s']['post_seal_verify'] = round(time.perf_counter() - start, 4)
        start = time.perf_counter()
        if target.exists():
            # Never blindly publish a previously damaged generation: full integrity check.
            _verify_impl(v2, target, 'full', recorder)
            if v2._read_json(target / 'manifest.v2.json') != manifest:
                raise SealError('existing generation manifest differs')
        else:
            os.rename(temporary, target)
            temporary = None
        if fsync in ('dir', 'each'):
            _fsync_dir(root)
        pointer = {'schema': v2.ACTIVE_SCHEMA, 'generation': generation,
                   'generation_sha256': digest, 'pack_format': 'OTDPACK1', 'runtime_acceptance': 'NO'}
        v2._atomic_json(root / 'active.v2.json', pointer)
        if fsync in ('dir', 'each'):
            _fsync_dir(root)
        recorder.metrics['phase_timings_s']['rename'] = round(time.perf_counter() - start, 4)
        recorder.finish(success=True, generation=generation, digest=digest)
        return target
    except BaseException as exc:
        recorder.fail(exc)
        recorder.finish(success=False, generation=generation, digest=digest)
        raise
    finally:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)


def seal_result(v2, target, *, post_seal_verify='fast'):
    """Legacy-compatible stdout result after seal; no redundant full scan."""
    manifest, digest = _manifest(v2, Path(target))
    return _result_from_seal(Path(target), digest, len(manifest['packs']), post_seal_verify)
