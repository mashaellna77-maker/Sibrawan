"""Frozen synthetic experiment; never optimize this generator against models."""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 20261014

def generate():
    rng = np.random.default_rng(SEED)
    t = np.arange(72)
    # Assumed gradual increase, fixed annual profile, noise and isolated shocks.
    profile = np.array([-10, -7, 1, 5, 8, -3, -12, -9, 4, 17, 13, -7])
    values = 65 + 0.85*t + profile[t % 12] + rng.normal(0, 7, 72)
    values[[16, 34, 51, 66]] += [24, 31, 35, 29]
    return pd.DataFrame({'month': pd.date_range('2020-01-01', periods=72, freq='MS').strftime('%Y-%m'),
                         'confirmed_phishing_incidents': np.maximum(0, np.rint(values)).astype(int)})

if __name__ == '__main__':
    path = Path(__file__).parent / 'data' / 'synthetic_phishing.csv'
    path.parent.mkdir(exist_ok=True)
    generate().to_csv(path, index=False)
    print(path)
