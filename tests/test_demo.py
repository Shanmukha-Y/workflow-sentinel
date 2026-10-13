"""Output preflight prevents unnecessary model/scanner work."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('review_demo', ROOT / 'examples/review_demo.py')
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


class DemoTests(unittest.TestCase):
    def test_existing_output_stops_before_provider_or_source_work(self):
        with tempfile.TemporaryDirectory() as directory:
            args = ['demo', '--scanner', '/unused/zizmor', '--output-directory', directory,
                    '--local-model', 'qwen3.8:27b-q4_K_M']
            with patch.object(sys, 'argv', args), patch.object(
                    DEMO, 'OllamaClient', side_effect=AssertionError('no inference')), patch.object(
                    DEMO, 'investigate', side_effect=AssertionError('no source work')):
                with self.assertRaises(FileExistsError):
                    DEMO.main()
