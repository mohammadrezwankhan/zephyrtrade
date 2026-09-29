"""Run an isolated, bounded training smoke; this is not the archived backtest.

Use a new output directory. The Phase 3 grid is deliberately small for a smoke
check; defaults in the library and command-line research pipeline are unchanged.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from zephyrtrade.data_loader import SyntheticDataConfig, generate_synthetic_data, write_data_bundle
from zephyrtrade.preprocessing import PreprocessingConfig, prepare_dataset
from zephyrtrade.phase2 import Phase2Config, run_phase2
from zephyrtrade.phase3 import Phase3Config, run_phase3

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args=parser.parse_args()
root=args.output
if root.exists():
    parser.error('Choose a new directory; this smoke never overwrites saved research.')
root.mkdir(parents=True)
config=SyntheticDataConfig(start='2023-01-01',end='2023-03-01',output_dir=root/'raw')
write_data_bundle(generate_synthetic_data(config),config)
prepare_dataset(PreprocessingConfig(raw_data_dir=root/'raw',output_dir=root/'processed'))
p2=run_phase2(Phase2Config(processed_data_dir=root/'processed',output_dir=root/'phase2',figure_dir=root/'figures'))
p3=run_phase3(Phase3Config(processed_data_dir=root/'processed',phase2_prediction_path=p2['test_predictions'],
                         output_dir=root/'phase3',figure_dir=root/'figures',max_iter=10,
                         regression_quantiles=(.5,),decision_quantiles=(.2,.5,.8),
                         leaf_candidates=(7,),bracket_candidates=(3,),min_samples_leaf=10))
print(json.dumps({'status':'PASS','scope':'New synthetic Jan-Feb 2023; default Phase 2; reduced-grid 10-iteration Phase 3',
                  'original_backtest_retrained':False,
                  'phase2_outputs':{k:str(v) for k,v in p2.items()},
                  'phase3_outputs':{k:str(v) for k,v in p3.items()}},indent=2))
