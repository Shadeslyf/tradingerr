import os
import joblib
import pandas as pd
import numpy as np
from loguru import logger
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, confusion_matrix

class ModelTrainer:
    def __init__(self, n_splits=5):
        self.n_splits = n_splits
        self.params = {
            'objective': 'multi:softprob',
            'num_class': 7, # 0 to 6 (Regimes 1-7 mapped to 0-6)
            'eval_metric': 'mlogloss',
            'max_depth': 5,
            'learning_rate': 0.05,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42
        }
        self.model = xgb.XGBClassifier(**self.params)

    def prepare_data(self, df: pd.DataFrame, target_col='label'):
        # Drop rows with missing labels or essential features
        df = df.dropna(subset=[target_col]).copy()
        
        # In a real pipeline, we'd drop non-feature columns
        cols_to_drop = [target_col, 'timestamp', 'symbol', 'token', 'exchange']
        drop_cols = [c for c in cols_to_drop if c in df.columns]
        
        X = df.drop(columns=drop_cols)
        # Map labels 1-7 to 0-6
        y = df[target_col].astype(int) - 1
        
        # Inject one dummy row per class (0 to 6) to prevent XGBoost errors on small/dummy datasets
        dummy_rows = [X.mean().to_dict() for _ in range(7)]
        dummy_X = pd.DataFrame(dummy_rows, columns=X.columns)
        dummy_X = dummy_X.astype(X.dtypes) # Ensure types match
        
        dummy_y = pd.Series(range(7), index=dummy_X.index)
        
        X = pd.concat([dummy_X, X], ignore_index=True)
        y = pd.concat([dummy_y, y], ignore_index=True)
        
        return X, y

    def train_with_cv(self, X: pd.DataFrame, y: pd.Series):
        """
        Uses TimeSeriesSplit to do walk-forward validation and evaluate metrics.
        Returns the trained model on the full dataset.
        """
        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        
        precisions = []
        recalls = []
        f1_scores = []
        
        logger.info(f"Starting Walk-Forward Cross Validation (splits={self.n_splits})...")
        
        for fold, (train_index, test_index) in enumerate(tscv.split(X)):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            # Use early stopping if desired, but for basic CV we just fit
            model = xgb.XGBClassifier(**self.params)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            
            # We use 'macro' to get unweighted average across classes 0, 1, 2
            # because class imbalance is common in regime labeling.
            p = precision_score(y_test, y_pred, average='macro', zero_division=0)
            r = recall_score(y_test, y_pred, average='macro', zero_division=0)
            f1 = f1_score(y_test, y_pred, average='macro', zero_division=0)
            
            precisions.append(p)
            recalls.append(r)
            f1_scores.append(f1)
            
            logger.debug(f"Fold {fold+1} - Precision: {p:.4f}, Recall: {r:.4f}, F1: {f1:.4f}")
            
        logger.info(f"CV Complete. Avg Precision: {np.mean(precisions):.4f}, Avg F1: {np.mean(f1_scores):.4f}")
        
        # Train on entire dataset after CV
        logger.info("Training final model on full dataset...")
        self.model.fit(X, y)
        logger.info("Final model training complete.")
        
        # Print final confusion matrix on the training set just for a quick sanity check
        # (It will be overfitted, but good to see if it predicts all classes)
        y_train_pred = self.model.predict(X)
        logger.info(f"Final Model Confusion Matrix (In-Sample):\n{confusion_matrix(y, y_train_pred)}")
        
        return self.model

    def save_model(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.model, filepath)
        logger.info(f"Model saved to {filepath}")
        
    def load_model(self, filepath: str):
        self.model = joblib.load(filepath)
        logger.info(f"Model loaded from {filepath}")
