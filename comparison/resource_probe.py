"""Separate actual local resource probe; no task-performance scoring or simulated outputs."""
import json
from pathlib import Path
import subprocess
import time

from workflow_sentinel.ollama_adapter import OllamaClient
from workflow_sentinel.openai_adapter import deadline

MODELS = ['qwen3.8:27b-q4_K_M', 'gemma4:31b-it-q4_K_M', 'mistral-small3.2:24b']


def rss_snapshot():
    daemon = int(subprocess.check_output(['lsof', '-t', '-iTCP:11434', '-sTCP:LISTEN'],
                                        text=True).strip())
    lines = subprocess.check_output(['ps', '-axo', 'pid,ppid,rss'], text=True).splitlines()[1:]
    rows = [tuple(map(int, line.split())) for line in lines if len(line.split()) == 3]
    selected = {daemon}
    while True:
        children = {pid for pid, parent, rss in rows if parent in selected}
        new = selected | children
        if new == selected:
            break
        selected = new
    return {'process_count': len(selected),
            'summed_rss_bytes': sum(rss * 1024 for pid, parent, rss in rows if pid in selected)}


def main():
    client = OllamaClient()
    records = []
    for model in MODELS:
        if client.call('/api/ps').get('models'):
            raise RuntimeError('Other model residency; refusing probe')
        before = rss_snapshot()
        with deadline(120):
            preload = client.call('/api/generate', {'model': model, 'prompt': '', 'stream': False,
                'keep_alive': '2m', 'options': {'num_ctx': 8192}}, timeout=120)
        after_load = rss_snapshot()
        body = {'model': model, 'messages': [{'role': 'user',
                'content': 'Reply with the single word ready.'}], 'stream': False,
                'options': {'num_ctx': 8192, 'num_predict': 16, 'temperature': 0, 'seed': 0}}
        if 'thinking' in client.model_info(model)['capabilities']:
            body['think'] = False
        with deadline(15):
            response = client.call('/api/chat', body)
        after_inference = rss_snapshot()
        running = next(m for m in client.call('/api/ps')['models'] if m['name'] == model)
        records.append({'model': model, 'before': before, 'after_load': after_load,
            'after_inference': after_inference,
            'ollama_size_bytes': running['size'], 'ollama_size_vram_bytes': running['size_vram'],
            'actual_request': body, 'actual_response': response, 'preload_response': preload})
        client.call('/api/generate', {'model': model, 'prompt': '', 'stream': False,'keep_alive': 0})
        with deadline(30):
            while client.call('/api/ps').get('models'):
                time.sleep(0.25)
    output = Path(__file__).with_name('RESOURCE_PROBE.json')
    with output.open('x') as stream:
        json.dump({'method': 'Separate sequential post-trial probe, one unscored 16-token-capped '
            'actual chat per model. ps RSS sum of loopback daemon and descendants, KiB to bytes; '
            'shared pages may be double-counted, GPU/unified memory may be excluded; not true peak '
            'or isolated model allocation. No PIDs, names, paths or unrelated processes saved.',
            'records': records}, stream, indent=2)
        stream.write('\n')
    print(json.dumps([{k:r[k] for k in ['model','after_load','after_inference',
                                     'ollama_size_bytes','ollama_size_vram_bytes']}
                      for r in records],indent=2))


if __name__ == '__main__':
    main()
