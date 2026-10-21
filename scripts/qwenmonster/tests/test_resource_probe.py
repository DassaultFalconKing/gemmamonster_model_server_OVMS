import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    import resource_probe as probe
except ModuleNotFoundError:
    probe=None


def snapshot(**changes):
    value=dict(created_before=1234.5,created_after=1234.5,total_bytes=10000,
               available_bytes=4000,rss_bytes=1000,private_bytes=1500)
    value.update(changes)
    return value


class ResourceProbeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(probe,'Resource probe is not implemented')
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)/'samples.jsonl'

    def collect(self,reader,**options):
        options={'samples':3,'interval':0,**options}
        return probe.collect(self.output,reader,pid=77,expected_created=1234.5,**options)

    def rows(self):
        return [json.loads(line) for line in self.output.read_text(encoding='utf-8').splitlines()]

    def test_exact_sample_count_and_complete_summary(self):
        reader=Mock(return_value=snapshot())
        result=self.collect(reader)
        self.assertEqual(result['status'],'COMPLETE')
        self.assertEqual(reader.call_count,3)
        self.assertEqual([r['kind'] for r in self.rows()],['header','sample','sample','sample','summary'])
        self.assertEqual(result['collected'],3)

    def test_missing_private_bytes_are_unknown_not_zero(self):
        result=self.collect(Mock(return_value=snapshot(private_bytes=None)))
        self.assertIsNone(result['private_delta_bytes'])
        self.assertTrue(all(r['private_bytes'] is None for r in self.rows() if r['kind']=='sample'))

    def test_pid_reuse_before_sampling_fails_without_metric_row(self):
        result=self.collect(Mock(return_value=snapshot(created_before=9999,created_after=9999)))
        self.assertEqual(result['status'],'FAILED')
        self.assertEqual(result['collected'],0)
        self.assertEqual(self.rows()[-2]['kind'],'error')

    def test_mid_sample_identity_change_fails(self):
        result=self.collect(Mock(return_value=snapshot(created_after=1235)))
        self.assertEqual(result['status'],'FAILED')
        self.assertEqual(result['collected'],0)

    def test_reader_failure_leaves_durable_error_and_summary(self):
        result=self.collect(Mock(side_effect=[snapshot(),RuntimeError('fixture process exited')]))
        self.assertEqual(result['status'],'FAILED')
        self.assertEqual(result['collected'],1)
        self.assertEqual([r['kind'] for r in self.rows()][-2:],['error','summary'])

    def test_existing_output_is_untouched_and_reader_not_called(self):
        self.output.write_bytes(b'preserve me')
        reader=Mock(return_value=snapshot())
        with self.assertRaises(FileExistsError):
            self.collect(reader)
        self.assertEqual(self.output.read_bytes(),b'preserve me')
        reader.assert_not_called()

    def test_low_headroom_stops_without_more_reads_or_sleep(self):
        reader=Mock(return_value=snapshot(available_bytes=500))
        sleep=Mock()
        result=self.collect(reader,interval=1,stop_below_bytes=1000,sleep=sleep)
        self.assertEqual(result['status'],'RESOURCE_LIMIT')
        self.assertEqual(result['exit_code'],2)
        self.assertEqual(reader.call_count,1)
        sleep.assert_not_called()

    def test_invalid_bounds_do_not_create_output(self):
        for options in [{'samples':0},{'samples':1001},{'interval':-1},{'interval':float('nan')},{'samples':4,'interval':101}]:
            with self.subTest(options=options),self.assertRaises(ValueError):
                self.collect(Mock(),**options)
            self.assertFalse(self.output.exists())

    def test_negative_or_inconsistent_metrics_fail(self):
        for value in [snapshot(rss_bytes=-1),snapshot(available_bytes=10001),snapshot(private_bytes=-1),snapshot(total_bytes=0,available_bytes=0)]:
            with self.subTest(value=value):
                result=self.collect(Mock(return_value=value))
                self.assertEqual(result['status'],'FAILED')
                self.assertEqual(result['collected'],0)
                self.output.unlink()

    def test_summary_deltas_are_descriptive_not_leak_attribution(self):
        reader=Mock(side_effect=[snapshot(),snapshot(rss_bytes=1800,private_bytes=1600),snapshot(rss_bytes=2000,private_bytes=1700)])
        result=self.collect(reader)
        self.assertEqual(result['rss_delta_bytes'],1000)
        self.assertEqual(result['private_delta_bytes'],200)
        self.assertEqual(result['leak_status'],'NOT_DETERMINED')


if __name__=='__main__': unittest.main()
