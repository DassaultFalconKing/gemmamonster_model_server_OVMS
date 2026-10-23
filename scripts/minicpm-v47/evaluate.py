"""Read-only model inventory and isolated SDK compatibility probes.

All output is private by default. Publication requires path/process sanitization.
"""
import argparse
import collections
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import xml.etree.ElementTree as ET


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')


def inventory(model):
    files = []
    for p in sorted(model.iterdir()):
        if p.is_file():
            entry = dict(name=p.name, bytes=p.stat().st_size, sha256=digest(p))
            meta = model / '.cache/huggingface/download' / (p.name + '.metadata')
            if meta.exists():
                entry['download_metadata'] = meta.read_text().splitlines()
            if p.suffix == '.xml':
                root = ET.parse(p).getroot()
                layers = root.findall('./layers/layer')
                entry['ir_version'] = root.get('version')
                entry['ops'] = dict(collections.Counter(x.get('type') + ':' + str(x.get('version')) for x in layers))
                entry['interfaces'] = [ET.tostring(x, encoding='unicode') for x in layers if x.get('type') in ('Parameter', 'Result', 'ReadValue', 'Assign')]
                entry['rt_info'] = ET.tostring(root.find('rt_info'), encoding='unicode') if root.find('rt_info') is not None else None
            files.append(entry)
    return dict(files=files, total_bytes=sum(x['bytes'] for x in files),
                bin_bytes=sum(x['bytes'] for x in files if x['name'].endswith('.bin')),
                configs={p.name: json.loads(p.read_text()) for p in model.glob('*config.json')})


def dlls():
    import psutil
    result = []
    for item in psutil.Process().memory_maps():
        p = Path(item.path)
        if p.suffix.lower() in ('.dll', '.pyd') and any(s in p.name.lower() for s in ('openvino', 'tbb', 'ze_', 'igdrcl')):
            result.append(dict(path=str(p), bytes=p.stat().st_size, sha256=digest(p)))
    return result


def probe(args):
    import psutil
    out = dict(stages={}, python=sys.version, executable=sys.executable, model=str(args.model),
               available_ram=psutil.virtual_memory().available)
    handles = []
    if args.sdk:
        sys.path.insert(0, str(args.sdk / 'python'))
        runtime = args.sdk / 'runtime/bin/intel64/Release'
        handles.append(os.add_dll_directory(str(runtime)))
        handles.append(os.add_dll_directory(str(args.sdk / 'runtime/3rdparty/tbb/bin')))
        os.environ['PATH'] = str(runtime) + os.pathsep + os.environ['PATH']
        os.environ['OPENVINO_LIB_PATHS'] = str(runtime)
        os.environ['OPENVINO_TOKENIZERS_PATH'] = str(runtime / 'openvino_tokenizers.dll')
    def stage(name, fn):
        start = time.perf_counter()
        try:
            value = fn()
            out['stages'][name] = dict(status='PASS', seconds=time.perf_counter()-start, result=value)
        except Exception:
            out['stages'][name] = dict(status='FAIL', seconds=time.perf_counter()-start, exception=traceback.format_exc())
        save(args.output, out)
        print(name, out['stages'][name]['status'], flush=True)
    try:
        import openvino as ov
        import openvino_genai as genai
        out['openvino_version'] = ov.get_version()
        out['genai_version'] = genai.get_version()
        core = ov.Core()
        if args.sdk:
            core.add_extension(str(runtime / 'openvino_tokenizers.dll'))
        else:
            import openvino_tokenizers
            core.add_extension(str(openvino_tokenizers._ext_path))
        def gpu():
            assert 'GPU' in core.available_devices, core.available_devices
            result = dict(devices=core.available_devices, versions={k: str(v) for k,v in core.get_versions('GPU').items()})
            for key in ('FULL_DEVICE_NAME','DEVICE_TOTAL_MEM_SIZE','GPU_DEVICE_TOTAL_MEM_SIZE','GPU_MEMORY_STATISTICS','SUPPORTED_PROPERTIES'):
                try:
                    result[key] = str(core.get_property('GPU', key))
                except Exception as e:
                    result[key] = str(e)
            return result
        stage('core_gpu', gpu)
        for p in sorted(args.model.glob('*.xml')):
            def read(p=p):
                m = core.read_model(p)
                return dict(inputs=[str(x) for x in m.inputs], outputs=[str(x) for x in m.outputs], ops=len(m.get_ops()))
            stage('read_' + p.stem, read)
        required = sum(p.stat().st_size for p in args.model.glob('*.bin')) + 3*1024**3
        out['admission'] = dict(required_ram=required, available_ram=psutil.virtual_memory().available,
                                policy='BIN bytes + 3 GiB, conservative safety gate')
        # This option is exclusively for the pinned version whose source dispatch
        # rejects model_type before any graph compilation. Never use on a newer SDK.
        if args.reject_only and not (args.sdk and genai.get_version().startswith('2026.4.0.0-3401-5f7f1278107')):
            raise RuntimeError('reject-only requires the exact pinned SDK build')
        if args.reject_only or (args.compile and out['admission']['available_ram'] >= required):
            workers = [p.info for p in psutil.process_iter(['pid','name']) if p.info['pid'] != os.getpid() and p.info['name'] and p.info['name'].lower() in ('ovms.exe','model_server.exe','benchmark_app.exe')]
            if workers:
                out['stages']['pipeline'] = dict(status='BLOCKED', reason='Other inference process', workers=workers)
            else:
                stage('pipeline', lambda: str(genai.VLMPipeline(str(args.model), 'GPU')))
        else:
            out['stages']['pipeline'] = dict(status='BLOCKED', reason='Insufficient memory admission headroom' if out['admission']['available_ram'] < required else 'Compile not requested')
        out['loaded_modules'] = dlls()
    except Exception:
        out['fatal_exception'] = traceback.format_exc()
    save(args.output, out)


def fixtures(destination):
    from PIL import Image, ImageDraw, ImageFont
    destination.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 40)
    items = []
    for name in ('IMG-01','IMG-02','IMG-03'):
        img = Image.new('RGB', (768,512), 'white'); draw = ImageDraw.Draw(img)
        if name == 'IMG-01':
            draw.ellipse((50,100,210,260), fill='red'); draw.ellipse((260,100,420,260), fill='red')
            draw.rectangle((500,100,660,260), fill='blue')
            prompt = 'Count the red circles and blue squares. Reply with their counts.'
            expected = {'red_circles':2,'blue_squares':1}
        elif name == 'IMG-02':
            draw.multiline_text((35,35), 'INVENTORY 42\nItem    Count\nApples  7\nPears   3', font=font, fill='black', spacing=25)
            prompt = 'Extract the title, inventory number, and table rows as JSON.'
            expected = {'title':'INVENTORY','number':42,'Apples':7,'Pears':3}
        else:
            draw.rectangle((10,10,758,80), fill='navy'); draw.text((30,20), 'Demo Dashboard', font=font, fill='white')
            draw.rectangle((50,150,350,240), fill='green'); draw.text((80,170), 'Start', font=font, fill='white')
            draw.rectangle((400,150,700,240), fill='gray'); draw.text((430,170), 'Cancel', font=font, fill='white')
            draw.text((50,340), 'Status: Ready', font=font, fill='black')
            prompt = 'Name the two buttons and the current status.'
            expected = {'buttons':['Start','Cancel'],'status':'Ready'}
        p = destination / (name + '.png'); img.save(p)
        items.append(dict(id=name,file=p.name,sha256=digest(p),prompt=prompt,expected=expected,status='NOT_RUN'))
    items.extend([dict(id='TEXT-01',prompt='Answer in one sentence: what is a compiler?',max_new_tokens=32,expected='translates source code',status='NOT_RUN'),dict(id='TEXT-02',prompt='Write only a Python function add(a, b) that returns their sum.',max_new_tokens=32,expected='def add(a, b): return a + b',status='NOT_RUN')])
    for item in items:
        item['prompt_sha256'] = hashlib.sha256(item['prompt'].encode('utf-8')).hexdigest()
        item['output'] = None
        item['generated_tokens'] = None
    save(destination / 'manifest.json', items)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inventory','probe','fixtures'])
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sdk', type=Path)
    parser.add_argument('--compile', action='store_true')
    parser.add_argument('--reject-only', action='store_true')
    args = parser.parse_args()
    if args.action == 'inventory': save(args.output, inventory(args.model))
    elif args.action == 'fixtures': fixtures(args.output)
    else: probe(args)
