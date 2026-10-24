"""Offline integrity, determinism, drop-in and concurrency tests for seal-fast."""
import json
from pathlib import Path
import hashlib
import io
import os
import shutil
import stat
import struct
import sys
import tempfile
from types import SimpleNamespace
from contextlib import redirect_stdout, redirect_stderr
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'cib2'))
import packv2_fast as fast
import verify_pack_v1 as pv


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def write_json(path, value):
    path.write_bytes(canonical(value))


def inspect_json(path):
    return json.loads(path.read_text())


def fake_v2(plan):
    return SimpleNamespace(MANIFEST_SCHEMA='cib2.pack_generation.v2',
                           ACTIVE_SCHEMA='cib2.active_pack_generation.v2',
                           _read_plans=lambda p: plan, _canonical=canonical,
                           _read_json=inspect_json, _atomic_json=write_json)


def make_pack(path, key, n=2, placement=None, broken_record=None):
    placement = placement or list(range(n))
    sizes = [1] * 9
    offsets, payload, stride, checksum_at, records_at = pv.canonical_layout(sizes,n)
    header = pv.HEADER.pack(pv.MAGIC, pv.VERSION, pv.ALIGNMENT, int(key,16),n,stride,
                            records_at,pv.ALIGNMENT,checksum_at,*sizes,*offsets,0)
    header = header[:-8] + struct.pack('<Q',pv.fnv_update(pv.FNV_OFFSET,header))
    content = bytearray(records_at+n*stride)
    content[:len(header)] = header
    content[pv.ALIGNMENT:pv.ALIGNMENT+n*4] = struct.pack('<'+'I'*n, *placement)
    sums=[]
    for ex in range(n):
        record = bytearray(payload)
        for off in offsets: record[off]=ex+1
        start=records_at + placement[ex]*stride
        content[start:start+payload]=record
        sums.append(pv.fnv_update(pv.FNV_OFFSET,record))
    content[checksum_at:checksum_at+n*8] = struct.pack('<'+'Q'*n,*sums)
    if broken_record is not None:
        content[records_at+placement[broken_record]*stride+offsets[0]] ^= 1
    path.write_bytes(content)
    return len(content)


class FastTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root/'source';self.src.mkdir()
        self.out = self.root/'out';self.out.mkdir()
        self.plans = self.root/'plans';self.plans.mkdir()
        keys=['00000000000000ab','00000000000000cd','00000000000000ef']
        self.entries=[]
        for key in keys:
            self.entries.append({'pack_layer_key':key,'expert_count':2,'placement':[1,0],
                                 'profile_sha256':'1'*64,'native_plan_sha256':'2'*64,
                                 'native_residency_sha256':'3'*64,'resident_tiers':[1,2]})
            make_pack(self.src/f'otd-{key}.pack',key,placement=[1,0])
        self.plan={'source':{'checkpoint_sha':'a'*64},'trace_sha256':'4'*64,'layers':self.entries}
        self.v2=fake_v2(self.plan)

    def seal(self,**kwargs):
        with redirect_stderr(io.StringIO()):
            return fast.seal_generation(self.v2,self.plans,self.src,self.out,progress='off',**kwargs)

    def verify(self,target,mode='full',**kwargs):
        with redirect_stderr(io.StringIO()):
            return fast.verify_generation(self.v2,target,mode=mode,workers=2,progress='off',**kwargs)

    def test_copy_deterministic_workers_1_vs_4(self):
        a=self.seal(workers=1)
        manifest = (a/'manifest.v2.json').read_bytes()
        shutil.rmtree(a)
        b=self.seal(workers=4)
        self.assertEqual(a,b)
        self.assertEqual((b/'manifest.v2.json').read_bytes(),manifest)
        self.assertEqual(self.verify(b)['payload_integrity_checked'],True)
        self.assertEqual(self.verify(b,mode='fast')['payload_integrity_checked'],False)
        self.assertEqual(self.out.joinpath('active.v2.json').exists(),True)
        self.assertEqual(set(x.name for x in b.iterdir()), {'manifest.v2.json'} | {f'otd-{x["pack_layer_key"]}.pack' for x in self.entries})

    def test_idempotent_and_legacy_stdout_shape(self):
        a=self.seal(workers=2)
        b=self.seal(workers=3)
        self.assertEqual(a,b)
        z=fast.seal_result(self.v2,a)
        for key in ('status','generation','pack_count','runtime_acceptance','promotion_authorized','pack_dir'):
            self.assertIn(key,z)
        self.assertEqual(z['status'],'VERIFIED_OFFLINE')
        self.assertFalse(z['payload_integrity_checked'])

    def test_full_rejects_bad_record_fast_does_not_claim_payload_verification(self):
        a=self.seal(workers=1)
        name=f'otd-{self.entries[0]["pack_layer_key"]}.pack'
        with (a/name).open('r+b') as file:
            file.seek(pv.ALIGNMENT*2)
            old=file.read(1);file.seek(pv.ALIGNMENT*2);file.write(bytes([old[0]^0x02]))
        self.assertEqual(self.verify(a,mode='fast')['verification_mode'],'fast')
        with self.assertRaisesRegex(fast.SealError,'payload checksum mismatch'):
            self.verify(a,mode='full')

    def test_default_fast_may_not_reject_pre_corrupted_source_but_full_does(self):
        pack = self.src/f'otd-{self.entries[0]["pack_layer_key"]}.pack'
        with pack.open('r+b') as f:
            f.seek(pv.ALIGNMENT*2)
            v=f.read(1);f.seek(pv.ALIGNMENT*2);f.write(bytes([v[0]^1]))
        # Invalid pre-existing payload: fast is structural only; full must reject.
        a=self.seal(workers=2)
        with self.assertRaises(fast.SealError):
            self.verify(a,mode='full')

    def test_reject_broken_placement_no_active(self):
        key=self.entries[0]['pack_layer_key']
        make_pack(self.src/f'otd-{key}.pack',key,placement=[0,1])
        with self.assertRaisesRegex(fast.SealError,'placement differs'):
            self.seal(workers=4)
        self.assertFalse((self.out/'active.v2.json').exists())
        self.assertFalse(list(self.out.glob('.generation-*')))

    def test_hardlink_policies_and_shared_inode(self):
        with self.assertRaisesRegex(fast.SealError,'writable'):
            self.seal(materialize='hardlink',workers=2)
        self.assertFalse((self.out/'active.v2.json').exists())
        a=self.seal(materialize='hardlink',hardlink_policy='chmod-readonly',workers=2)
        first=f'otd-{self.entries[0]["pack_layer_key"]}.pack'
        self.assertEqual(os.stat(self.src/first).st_ino,os.stat(a/first).st_ino)
        self.assertFalse(os.stat(self.src/first).st_mode & stat.S_IWUSR)
        self.assertTrue(self.verify(a,mode='full'))

    def test_jsonl_events_and_metrics_rejected(self):
        log = self.root/'log.jsonl'; metrics = self.root/'metrics.json'
        capture=io.StringIO()
        with redirect_stderr(capture):
            target=fast.seal_generation(self.v2,self.plans,self.src,self.out,workers=4,
                progress='jsonl',log_file=log,metrics_file=metrics)
        self.assertTrue(target.exists())
        self.assertEqual(json.loads(metrics.read_text())['packs_ok'],3)
        events=[json.loads(x) for x in capture.getvalue().splitlines()]
        done=[x for x in events if x['event']=='pack_done']
        self.assertGreaterEqual(len(done),3)
        self.assertEqual({x['pack'] for x in done if x['phase']=='materialize'}, {f'otd-{x["pack_layer_key"]}.pack' for x in self.entries})
        self.assertIn('run_id',events[0])
        # Failure publishes a distinct REJECTED metrics document.
        old_pointer=(self.out/'active.v2.json').read_bytes()
        shutil.rmtree(target)
        key=self.entries[0]['pack_layer_key']
        make_pack(self.src/f'otd-{key}.pack',key,placement=[0,1])
        with self.assertRaises(fast.SealError):
            with redirect_stderr(io.StringIO()):
                fast.seal_generation(self.v2,self.plans,self.src,self.out,workers=1,
                    progress='off',metrics_file=metrics)
        self.assertEqual(json.loads(metrics.read_text())['status'],'REJECTED')
        self.assertEqual((self.out/'active.v2.json').read_bytes(), old_pointer)  # failed run never changes active pointer

    def test_full_at_seal_rejects_corrupt_source_before_publication(self):
        key=self.entries[0]['pack_layer_key']
        make_pack(self.src/f'otd-{key}.pack',key,placement=[1,0],broken_record=0)
        with self.assertRaisesRegex(fast.SealError,'payload checksum mismatch'):
            self.seal(workers=2,post_seal_verify='full')
        self.assertFalse((self.out/'active.v2.json').exists())
        self.assertFalse(list(self.out.glob('.generation-*')))

    def test_none_never_claims_verification(self):
        a=self.seal(workers=1,post_seal_verify='none')
        result=fast.seal_result(self.v2,a,post_seal_verify='none')
        self.assertEqual(result['status'],'SEALED_UNVERIFIED')
        self.assertFalse(result['payload_integrity_checked'])

    def test_manifest_sha_and_total_copy_bytes(self):
        result=self.seal(workers=2)
        z=json.loads((result/'manifest.v2.json').read_text())
        for item in z['packs']:
            h=hashlib.sha256((result/item['file']).read_bytes()).hexdigest()
            self.assertEqual(h,item['pack_sha256'])
        m=next(self.out.glob('receipts/seal-*.json'))
        d=json.loads(m.read_text())
        self.assertGreaterEqual(d['bytes_read'],sum(x['pack_bytes'] for x in z['packs']))  # fast metadata is small extra
        self.assertEqual(d['bytes_written'],sum(x['pack_bytes'] for x in z['packs']))
        self.assertEqual(d['workers_used_max'] <= 2, True)

if __name__ == '__main__':unittest.main()
