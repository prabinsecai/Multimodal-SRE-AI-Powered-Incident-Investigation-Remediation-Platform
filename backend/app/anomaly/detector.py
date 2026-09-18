import numpy as np
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    """
    Multimodal SRE Anomaly Detector using Isolation Forest
    with statistical fallback for small datasets.
    """
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
            warm_start=False
        )
        self.fitted = False
        self.baseline_mean: float = 0.0
        self.baseline_std: float = 1.0

    def extract_features(self, raw_values: list[float] | np.ndarray) -> np.ndarray:
        """
        Extract multivariate time-series features:
        - raw value
        - delta (rate of change from previous step)
        - rolling deviation from local mean (window=5)
        """
        arr = np.asarray(raw_values, dtype=float).ravel()
        if len(arr) == 0:
            return np.empty((0, 3))
        if len(arr) == 1:
            return np.array([[arr[0], 0.0, 0.0]])

        # 1. deltas
        deltas = np.diff(arr, prepend=arr[0])

        # 2. rolling mean difference
        window = min(5, len(arr))
        rolling_means = np.convolve(arr, np.ones(window)/window, mode='same')
        dev_from_mean = arr - rolling_means

        features = np.column_stack([arr, deltas, dev_from_mean])
        return features

    def fit(self, X: list[float] | np.ndarray):
        raw_arr = np.asarray(X, dtype=float).ravel()
        if len(raw_arr) < 2:
            self.baseline_mean = float(raw_arr[0]) if len(raw_arr) == 1 else 0.0
            self.baseline_std = 1.0
            self.fitted = True
            return self

        self.baseline_mean = float(np.mean(raw_arr))
        self.baseline_std = float(np.std(raw_arr)) or 1.0

        features = self.extract_features(raw_arr)
        # If enough samples, train IsolationForest
        if len(features) >= 10:
            self.model.fit(features)
        self.fitted = True
        return self

    def score(self, X: list[float] | np.ndarray) -> np.ndarray:
        """
        Compute anomaly score normalized in [0.0, 1.0].
        Higher score indicates higher probability of anomaly.
        """
        if not self.fitted:
            raise RuntimeError('Detector must be fitted before scoring')

        raw_arr = np.asarray(X, dtype=float).ravel()
        if len(raw_arr) == 0:
            return np.array([])

        features = self.extract_features(raw_arr)

        if len(features) >= 10 and hasattr(self.model, 'estimators_') and len(self.model.estimators_) > 0:
            # IsolationForest decision_function is negative for anomalies, positive for normal
            decision = np.asarray(self.model.decision_function(features), dtype=float)
            # Sigmoid transform centered around zero to map to [0, 1]
            scores = 1.0 / (1.0 + np.exp(8.0 * decision))
        else:
            # Robust statistical Z-score fallback for smaller datasets
            z_scores = np.abs(raw_arr - self.baseline_mean) / (self.baseline_std + 1e-6)
            # Map Z-scores to [0, 1] using standard sigmoid
            scores = 1.0 / (1.0 + np.exp(-1.5 * (z_scores - 2.5)))

        return np.clip(scores, 0.0, 1.0)

    def is_anomaly(self, X: list[float] | np.ndarray, threshold: float = 0.65) -> np.ndarray:
        scores = self.score(X)
        return scores >= threshold
