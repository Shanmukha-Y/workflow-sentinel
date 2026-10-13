"""Check only the project's freshly built source/wheel archive contents."""
import argparse
from pathlib import Path
import tarfile
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', type=Path)
args = parser.parse_args()
source = next(args.directory.glob('workflow_sentinel-*.tar.gz'))
wheel = next(args.directory.glob('workflow_sentinel-*.whl'))
with tarfile.open(source) as archive:
    names = archive.getnames()
    root = names[0].split('/')[0]
    for name in ['LICENSE', 'README.md', 'examples/review_demo.py',
                 'fixtures/repairable/findings.zizmor-1.30.1.sarif',
                 'fixtures/repairable/.github/workflows/review.yml',
                 'model_evaluation/manifest.json', 'model_evaluation/holdout-v2/FREEZE.json',
                 'evaluation/manifest.json', 'schemas/report.schema.json',
                 'tests/helpers/agent-script.schema.json',
                 'tests/archives/model-harness-validation/mock-regression.json',
                 'comparison/REPORT.md', 'comparison/results/index.json']:
        assert root + '/' + name in names, 'Missing reproducibility asset: ' + name
    assert not any('/.venv/' in n or '/.git/' in n for n in names)
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    metadata = next(n for n in names if n.endswith('.dist-info/METADATA'))
    assert 'License-Expression: MIT' in archive.read(metadata).decode()
    assert any(n.endswith('.dist-info/licenses/LICENSE') for n in names)
    assert all(n.startswith('workflow_sentinel/') or '.dist-info/' in n for n in names)
print('Source reproducibility assets and wheel license/payload checks passed')
