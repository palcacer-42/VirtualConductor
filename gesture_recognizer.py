"""
Gesture Recognizer — Trains and runs scikit-learn classifiers on landmark data.
"""

import json
import os
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier

GESTURES_DIR = os.path.join(os.path.dirname(__file__), 'gestures')
DATASET_PATH = os.path.join(GESTURES_DIR, 'dataset.json')


class GestureRecognizer:
    def __init__(self, confidence_threshold=0.7):
        self.confidence_threshold = confidence_threshold
        self.models = {}  # source -> trained classifier
        self.labels = {}  # source -> list of label names
        self._load_models()

    def _model_path(self, source):
        return os.path.join(GESTURES_DIR, f'model_{source}.pkl')

    def _load_models(self):
        """Auto-load any saved models on startup."""
        if not os.path.exists(GESTURES_DIR):
            return
        for fname in os.listdir(GESTURES_DIR):
            if fname.startswith('model_') and fname.endswith('.pkl'):
                source = fname[6:-4]  # strip 'model_' and '.pkl'
                path = os.path.join(GESTURES_DIR, fname)
                data = joblib.load(path)
                self.models[source] = data['classifier']
                self.labels[source] = data['labels']

    def train(self, source="right_hand"):
        """Train a classifier for the given source. Returns (success, message)."""
        if not os.path.exists(DATASET_PATH):
            return False, "No dataset found"

        with open(DATASET_PATH, 'r') as f:
            dataset = json.load(f)

        # Filter samples by source
        samples = [s for s in dataset["samples"] if s["source"] == source]
        if len(samples) < 2:
            return False, "Need at least 2 samples"

        # Check we have at least 2 different labels
        unique_labels = list(set(s["label"] for s in samples))
        if len(unique_labels) < 2:
            return False, "Need at least 2 different gestures"

        X = np.array([s["landmarks"] for s in samples])
        y = np.array([s["label"] for s in samples])

        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X, y)

        # Save model + labels
        os.makedirs(GESTURES_DIR, exist_ok=True)
        model_data = {'classifier': clf, 'labels': unique_labels}
        joblib.dump(model_data, self._model_path(source))

        self.models[source] = clf
        self.labels[source] = unique_labels

        return True, f"Trained on {len(samples)} samples, {len(unique_labels)} gestures"

    def predict(self, normalized_landmarks, source="right_hand"):
        """Predict gesture from normalized landmarks. Returns (label, confidence) or (None, 0.0)."""
        if source not in self.models:
            return None, 0.0

        X = np.array(normalized_landmarks).reshape(1, -1)
        clf = self.models[source]

        proba = clf.predict_proba(X)[0]
        max_idx = np.argmax(proba)
        confidence = proba[max_idx]

        if confidence >= self.confidence_threshold:
            label = clf.classes_[max_idx]
            return label, confidence

        return None, confidence

    def get_labels(self, source="right_hand"):
        return self.labels.get(source, [])

    def has_model(self, source="right_hand"):
        return source in self.models
