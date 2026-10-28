"""Compare raw pre-sampler target logits at P0's first divergent token."""
import array
import json
from pathlib import Path
ROOT = Path(r"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca")
def events(mode):
    directory = ROOT / "traces-v2" / f"P0-{mode}"
    for path in sorted(directory.glob("event-*-before.txt"), key=lambda p:int(p.name.split('-')[1])):
        lines = path.read_text().splitlines()
        header = lines[0].split()
        if mode == "mtp" and header[3] != "1": continue
        assert header[5] == "f32", header
        shape = list(map(int, header[7:]))
        assert len(shape) == 3
        request = lines[1].split()
        if request[1] != "0": continue
        output_len, validate = int(request[7]), int(request[9])
        prompt = list(map(int, request[11:]))
        generated = list(map(int, lines[2].split()[1:]))
        base_position = len(generated) - validate
        # Sampler::_get_logit_vector counts offsets backwards from sequence end.
        num_to_process = min(validate, output_len - 1)
        for i in range(num_to_process + 1):
            position = base_position + i
            row = output_len - 1 - (num_to_process-i)
            yield position, row, shape, prompt, generated, path
def capture(mode, position):
    reference = json.loads((ROOT / f"P0-{mode}-rep0.json").read_text())["ids"]
    for pos,row,shape,prompt,generated,path in events(mode):
        if pos != position: continue
        assert generated[:position] == reference[:position], (path,generated,reference)
        data = array.array('f')
        binary = path.with_name(path.name.replace("-before.txt", ".bin"))
        assert binary.stat().st_size == 4*shape[0]*shape[1]*shape[2]
        with binary.open('rb') as stream:
            stream.seek(row*shape[2]*4)
            data.fromfile(stream, shape[2])
        top1 = max(range(len(data)), key=data.__getitem__)
        top2 = max((i for i in range(len(data)) if i != top1), key=data.__getitem__)
        return data, {"meta":str(path), "row":row, "position":pos, "prompt_ids":prompt, "generated_before":generated, "top1_id":top1, "top1_logit":data[top1], "top2_id":top2, "top2_logit":data[top2], "margin":data[top1]-data[top2]}
    raise AssertionError((mode, position, "target logits event not found"))
for mode in ("baseline", "mtp"):
    for rep in (0,1):
        original = json.loads((ROOT / f"P0-{mode}-rep{rep}.json").read_text())["ids"]
        traced = json.loads((ROOT / "trace-runs-v2" / f"P0-{mode}-rep{rep}.json").read_text())["ids"]
        assert original == traced, f"trace build fails reference reproduction: {mode} {rep}"
a, am = capture("baseline", 3)
b, bm = capture("mtp", 3)
assert am["prompt_ids"] == bm["prompt_ids"], "INTERNAL INPUT DRIFT"
assert am["generated_before"][:3] == bm["generated_before"][:3], "CONTEXT DRIFT"
expected_input = list(map(int, (ROOT / "input-ids.txt").read_text().split()))
for mode in ("baseline", "mtp"):
    for rep in (0,1):
        internal = list(map(int, (ROOT / "traces-v2" / f"P0-{mode}" / f"input-{rep}.txt").read_text().split()))
        assert internal == expected_input, (mode,rep,"INTERNAL INPUT DRIFT")
result = {"reference_outputs_reproduced":True, "internal_prompt_ids_equal":True, "internal_prompt_token_count":len(expected_input), "internal_prompt_ids":expected_input, "same_prior_generated_ids":am["generated_before"][:3], "baseline":am, "mtp":bm, "max_abs_logit_difference": max(abs(x-y) for x,y in zip(a,b)), "candidate_logits":{str(t):{"baseline":a[t],"mtp":b[t]} for t in (33793,11602)}, "warning":"Raw-logit argmax evidence does not by itself identify KV kernel versus GDN-state root cause."}
event = Path(bm["meta"])
event_number = int(event.name.split('-')[1])
previous_verifications = []
for meta in event.parent.glob("event-*-before.txt"):
    if int(meta.name.split('-')[1]) >= event_number: continue
    lines = meta.read_text().splitlines()
    if lines[0].split()[3] == "1" and int(lines[1].split()[9]) > 0:
        previous_verifications.append(meta.name)
assert not previous_verifications
after = event.with_name(event.name.replace("before", "after-sample")).read_text().splitlines()
after_ids = list(map(int,after[2].split()[1:]))
assert bm["generated_before"][3] == 33793 and after_ids[3] == bm["top1_id"] == 11602
result["chronology"] = {"previous_target_verifications":previous_verifications, "draft_candidate_at_difference":33793, "after_sampling":after_ids, "interpretation":"Argmax flip occurs in first target verification, triggers candidate rejection; not an effect of earlier rejection/rollback."}
(ROOT / "logit-comparison.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
