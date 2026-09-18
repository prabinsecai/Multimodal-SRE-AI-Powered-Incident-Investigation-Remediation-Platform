import numpy as np
from app.anomaly.detector import AnomalyDetector

def test_anomaly_detector_training_and_scoring():
    # Normal data points with single outlier
    normal_data = [10.0 + np.random.normal(0, 0.5) for _ in range(30)]
    anomalous_data = [10.0, 10.2, 9.8, 10.1, 95.0]

    detector = AnomalyDetector(contamination=0.1)
    detector.fit(normal_data)

    scores = detector.score(anomalous_data)
    assert len(scores) == len(anomalous_data)
    # The extreme outlier (95.0) should have high anomaly score
    assert scores[-1] > scores[0]
    assert scores[-1] >= 0.65

def test_anomaly_detector_small_sample_fallback():
    # When sample count is small (< 10), statistical fallback should still work
    small_data = [5.0, 5.1, 4.9, 5.2, 50.0]
    detector = AnomalyDetector()
    detector.fit(small_data[:4])
    scores = detector.score(small_data)
    assert len(scores) == 5
    assert scores[-1] > scores[0]

def test_anomaly_feature_extraction():
    detector = AnomalyDetector()
    raw = [1.0, 2.0, 3.0, 4.0, 5.0]
    features = detector.extract_features(raw)
    assert features.shape == (5, 3)
