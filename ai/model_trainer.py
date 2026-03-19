"""
Machine Learning Model Trainer for BrayoForexBot
Trains and optimizes various ML models for trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import joblib
from typing import Dict, List, Tuple, Optional, Any
import logging
from sklearn.model_selection import train_test_split, TimeSeriesSplit, cross_val_score
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
from sklearn.svm import SVC, SVR
from sklearn.metrics import classification_report, regression_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import lightgbm as lgb
import optuna
from feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Advanced ML model trainer for trading strategies
    Supports multiple algorithms and hyperparameter optimization
    """
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.models = {}
        self.best_models = {}
        self.model_performance = {}
        self.training_history = {}
        
        # Supported models
        self.classification_models = {
            'random_forest': RandomForestClassifier,
            'gradient_boosting': GradientBoostingClassifier,
            'logistic_regression': LogisticRegression,
            'svm': SVC,
            'xgboost': xgb.XGBClassifier,
            'lightgbm': lgb.LGBMClassifier
        }
        
        self.regression_models = {
            'random_forest': RandomForestRegressor,
            'gradient_boosting': GradientBoostingRegressor,
            'linear_regression': LinearRegression,
            'ridge': Ridge,
            'lasso': Lasso,
            'svm': SVR,
            'xgboost': xgb.XGBRegressor,
            'lightgbm': lgb.LGBMRegressor
        }
        
        # Default hyperparameters
        self.default_params = {
            'random_forest': {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'random_state': 42
            },
            'gradient_boosting': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'random_state': 42
            },
            'logistic_regression': {
                'random_state': 42,
                'max_iter': 1000
            },
            'svm': {
                'kernel': 'rbf',
                'C': 1.0,
                'gamma': 'scale'
            },
            'xgboost': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'random_state': 42
            },
            'lightgbm': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'random_state': 42,
                'verbose': -1
            },
            'linear_regression': {},
            'ridge': {
                'alpha': 1.0,
                'random_state': 42
            },
            'lasso': {
                'alpha': 1.0,
                'random_state': 42
            }
        }
    
    def prepare_data(self, data: pd.DataFrame, target_col: str, 
                    test_size: float = 0.2, validation_size: float = 0.2,
                    scale_features: bool = True, reduce_features: bool = False) -> Dict:
        """
        Prepare data for training
        
        Args:
            data: Raw OHLCV data
            target_col: Target column name
            test_size: Test set size
            validation_size: Validation set size
            scale_features: Whether to scale features
            reduce_features: Whether to reduce dimensionality
            
        Returns:
            Dictionary with train/val/test splits
        """
        try:
            logger.info("Preparing data for training...")
            
            # Create features
            df_features = self.feature_engineer.create_features(data)
            
            if df_features.empty:
                raise ValueError("Feature engineering failed")
            
            # Remove rows with NaN targets
            df_features = df_features.dropna(subset=[target_col])
            
            if len(df_features) < 100:
                raise ValueError("Insufficient data after feature engineering")
            
            # Split features and targets
            X = df_features[self.feature_engineer.feature_columns]
            y = df_features[target_col]
            
            logger.info(f"Dataset: {len(X)} samples, {len(X.columns)} features")
            
            # Time series split (maintain temporal order)
            n_samples = len(X)
            
            # Calculate split indices
            test_start = int(n_samples * (1 - test_size))
            val_start = int(test_start * (1 - validation_size))
            
            X_train = X.iloc[:val_start]
            y_train = y.iloc[:val_start]
            
            X_val = X.iloc[val_start:test_start]
            y_val = y.iloc[val_start:test_start]
            
            X_test = X.iloc[test_start:]
            y_test = y.iloc[test_start:]
            
            logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
            
            # Scale features
            if scale_features:
                X_train = self.feature_engineer.scale_features(X_train, method='standard')
                X_val = self.feature_engineer.apply_scaling(X_val, method='standard')
                X_test = self.feature_engineer.apply_scaling(X_test, method='standard')
            
            # Reduce features
            if reduce_features:
                n_components = min(50, len(X_train.columns) // 2)
                X_train = self.feature_engineer.reduce_features(X_train, method='pca', n_components=n_components)
                X_val = self.feature_engineer.apply_scaling(X_val, method='standard')
                X_test = self.feature_engineer.apply_scaling(X_test, method='standard')
            
            return {
                'X_train': X_train,
                'y_train': y_train,
                'X_val': X_val,
                'y_val': y_val,
                'X_test': X_test,
                'y_test': y_test,
                'feature_columns': X_train.columns.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return {}
    
    def train_classification_models(self, data_splits: Dict, models_to_train: List[str] = None) -> Dict:
        """
        Train classification models
        
        Args:
            data_splits: Prepared data splits
            models_to_train: List of model names to train
            
        Returns:
            Dictionary with trained models and performance
        """
        try:
            if models_to_train is None:
                models_to_train = list(self.classification_models.keys())
            
            logger.info(f"Training classification models: {models_to_train}")
            
            results = {}
            
            for model_name in models_to_train:
                try:
                    logger.info(f"Training {model_name}...")
                    
                    # Get model class and parameters
                    model_class = self.classification_models[model_name]
                    params = self.default_params.get(model_name, {})
                    
                    # Create and train model
                    model = model_class(**params)
                    model.fit(data_splits['X_train'], data_splits['y_train'])
                    
                    # Evaluate on validation set
                    y_pred = model.predict(data_splits['X_val'])
                    
                    # Calculate metrics
                    accuracy = accuracy_score(data_splits['y_val'], y_pred)
                    precision = precision_score(data_splits['y_val'], y_pred, average='weighted')
                    recall = recall_score(data_splits['y_val'], y_pred, average='weighted')
                    f1 = f1_score(data_splits['y_val'], y_pred, average='weighted')
                    
                    # Store model and performance
                    self.models[model_name] = model
                    self.model_performance[model_name] = {
                        'accuracy': accuracy,
                        'precision': precision,
                        'recall': recall,
                        'f1_score': f1,
                        'model_type': 'classification'
                    }
                    
                    results[model_name] = {
                        'model': model,
                        'performance': self.model_performance[model_name]
                    }
                    
                    logger.info(f"{model_name} - Accuracy: {accuracy:.3f}, F1: {f1:.3f}")
                    
                except Exception as e:
                    logger.error(f"Error training {model_name}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error training classification models: {e}")
            return {}
    
    def train_regression_models(self, data_splits: Dict, models_to_train: List[str] = None) -> Dict:
        """
        Train regression models
        
        Args:
            data_splits: Prepared data splits
            models_to_train: List of model names to train
            
        Returns:
            Dictionary with trained models and performance
        """
        try:
            if models_to_train is None:
                models_to_train = list(self.regression_models.keys())
            
            logger.info(f"Training regression models: {models_to_train}")
            
            results = {}
            
            for model_name in models_to_train:
                try:
                    logger.info(f"Training {model_name}...")
                    
                    # Get model class and parameters
                    model_class = self.regression_models[model_name]
                    params = self.default_params.get(model_name, {})
                    
                    # Create and train model
                    model = model_class(**params)
                    model.fit(data_splits['X_train'], data_splits['y_train'])
                    
                    # Evaluate on validation set
                    y_pred = model.predict(data_splits['X_val'])
                    
                    # Calculate metrics
                    mse = mean_squared_error(data_splits['y_val'], y_pred)
                    mae = mean_absolute_error(data_splits['y_val'], y_pred)
                    r2 = r2_score(data_splits['y_val'], y_pred)
                    
                    # Store model and performance
                    self.models[model_name] = model
                    self.model_performance[model_name] = {
                        'mse': mse,
                        'mae': mae,
                        'r2_score': r2,
                        'model_type': 'regression'
                    }
                    
                    results[model_name] = {
                        'model': model,
                        'performance': self.model_performance[model_name]
                    }
                    
                    logger.info(f"{model_name} - R2: {r2:.3f}, MSE: {mse:.6f}")
                    
                except Exception as e:
                    logger.error(f"Error training {model_name}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error training regression models: {e}")
            return {}
    
    def optimize_hyperparameters(self, data_splits: Dict, model_name: str, 
                               model_type: str = 'classification', n_trials: int = 100) -> Dict:
        """
        Optimize hyperparameters using Optuna
        
        Args:
            data_splits: Prepared data splits
            model_name: Model name to optimize
            model_type: 'classification' or 'regression'
            n_trials: Number of optimization trials
            
        Returns:
            Best parameters and model
        """
        try:
            logger.info(f"Optimizing hyperparameters for {model_name}...")
            
            # Define objective function
            def objective(trial):
                try:
                    # Get hyperparameters
                    params = self._get_hyperparameters(trial, model_name)
                    
                    # Create model
                    if model_type == 'classification':
                        model = self.classification_models[model_name](**params)
                    else:
                        model = self.regression_models[model_name](**params)
                    
                    # Cross-validation
                    cv = TimeSeriesSplit(n_splits=3)
                    scores = []
                    
                    for train_idx, val_idx in cv.split(data_splits['X_train']):
                        X_train_cv, X_val_cv = data_splits['X_train'].iloc[train_idx], data_splits['X_train'].iloc[val_idx]
                        y_train_cv, y_val_cv = data_splits['y_train'].iloc[train_idx], data_splits['y_train'].iloc[val_idx]
                        
                        model.fit(X_train_cv, y_train_cv)
                        y_pred = model.predict(X_val_cv)
                        
                        if model_type == 'classification':
                            score = f1_score(y_val_cv, y_pred, average='weighted')
                        else:
                            score = r2_score(y_val_cv, y_pred)
                        
                        scores.append(score)
                    
                    return np.mean(scores)
                    
                except Exception as e:
                    logger.error(f"Error in trial: {e}")
                    return -1.0 if model_type == 'classification' else -np.inf
            
            # Create study
            study = optuna.create_study(direction='maximize' if model_type == 'classification' else 'minimize')
            study.optimize(objective, n_trials=n_trials)
            
            # Get best parameters
            best_params = study.best_params
            best_score = study.best_value
            
            # Train final model with best parameters
            if model_type == 'classification':
                best_model = self.classification_models[model_name](**best_params)
            else:
                best_model = self.regression_models[model_name](**best_params)
            
            best_model.fit(data_splits['X_train'], data_splits['y_train'])
            
            # Store best model
            self.best_models[model_name] = best_model
            
            logger.info(f"Best {model_name} - Score: {best_score:.3f}")
            logger.info(f"Best parameters: {best_params}")
            
            return {
                'best_model': best_model,
                'best_params': best_params,
                'best_score': best_score,
                'study': study
            }
            
        except Exception as e:
            logger.error(f"Error optimizing hyperparameters: {e}")
            return {}
    
    def _get_hyperparameters(self, trial, model_name: str) -> Dict:
        """Get hyperparameters for optimization"""
        try:
            params = {}
            
            if model_name == 'random_forest':
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 20),
                    'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                    'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                    'random_state': 42
                }
            elif model_name == 'gradient_boosting':
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 15),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                    'random_state': 42
                }
            elif model_name == 'xgboost':
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 15),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'random_state': 42
                }
            elif model_name == 'lightgbm':
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 15),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'random_state': 42,
                    'verbose': -1
                }
            elif model_name == 'logistic_regression':
                params = {
                    'C': trial.suggest_float('C', 0.01, 10.0),
                    'penalty': trial.suggest_categorical('penalty', ['l1', 'l2']),
                    'solver': 'liblinear',
                    'random_state': 42,
                    'max_iter': 1000
                }
            elif model_name == 'svm':
                params = {
                    'C': trial.suggest_float('C', 0.1, 10.0),
                    'gamma': trial.suggest_categorical('gamma', ['scale', 'auto']),
                    'kernel': trial.suggest_categorical('kernel', ['rbf', 'linear'])
                }
            elif model_name == 'ridge':
                params = {
                    'alpha': trial.suggest_float('alpha', 0.01, 10.0),
                    'random_state': 42
                }
            elif model_name == 'lasso':
                params = {
                    'alpha': trial.suggest_float('alpha', 0.01, 10.0),
                    'random_state': 42
                }
            
            return params
            
        except Exception as e:
            logger.error(f"Error getting hyperparameters: {e}")
            return {}
    
    def evaluate_models(self, data_splits: Dict) -> Dict:
        """
        Evaluate all trained models on test set
        
        Args:
            data_splits: Prepared data splits
            
        Returns:
            Evaluation results
        """
        try:
            logger.info("Evaluating models on test set...")
            
            results = {}
            
            for model_name, model in self.models.items():
                try:
                    # Predict on test set
                    y_pred = model.predict(data_splits['X_test'])
                    
                    # Calculate metrics
                    if model_name in self.model_performance and self.model_performance[model_name]['model_type'] == 'classification':
                        # Classification metrics
                        accuracy = accuracy_score(data_splits['y_test'], y_pred)
                        precision = precision_score(data_splits['y_test'], y_pred, average='weighted')
                        recall = recall_score(data_splits['y_test'], y_pred, average='weighted')
                        f1 = f1_score(data_splits['y_test'], y_pred, average='weighted')
                        
                        results[model_name] = {
                            'accuracy': accuracy,
                            'precision': precision,
                            'recall': recall,
                            'f1_score': f1,
                            'model_type': 'classification'
                        }
                        
                        logger.info(f"{model_name} Test - Accuracy: {accuracy:.3f}, F1: {f1:.3f}")
                        
                    else:
                        # Regression metrics
                        mse = mean_squared_error(data_splits['y_test'], y_pred)
                        mae = mean_absolute_error(data_splits['y_test'], y_pred)
                        r2 = r2_score(data_splits['y_test'], y_pred)
                        
                        results[model_name] = {
                            'mse': mse,
                            'mae': mae,
                            'r2_score': r2,
                            'model_type': 'regression'
                        }
                        
                        logger.info(f"{model_name} Test - R2: {r2:.3f}, MSE: {mse:.6f}")
                    
                except Exception as e:
                    logger.error(f"Error evaluating {model_name}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error evaluating models: {e}")
            return {}
    
    def get_best_model(self, metric: str = None) -> Tuple[str, Any]:
        """
        Get best performing model
        
        Args:
            metric: Metric to use for selection (None for auto)
            
        Returns:
            Tuple of (model_name, model)
        """
        try:
            if not self.models:
                logger.warning("No models trained")
                return None, None
            
            best_model_name = None
            best_score = -np.inf
            best_model_type = None
            
            for model_name, performance in self.model_performance.items():
                if metric is None:
                    # Auto-select based on model type
                    if performance['model_type'] == 'classification':
                        score = performance['f1_score']
                    else:
                        score = performance['r2_score']
                else:
                    score = performance.get(metric, 0)
                
                # Check if this is better
                if performance['model_type'] == 'classification' and score > best_score:
                    best_score = score
                    best_model_name = model_name
                    best_model_type = 'classification'
                elif performance['model_type'] == 'regression' and score > best_score:
                    best_score = score
                    best_model_name = model_name
                    best_model_type = 'regression'
            
            if best_model_name:
                logger.info(f"Best model: {best_model_name} ({best_model_type}) - {metric or 'auto'}: {best_score:.3f}")
                return best_model_name, self.models[best_model_name]
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error getting best model: {e}")
            return None, None
    
    def save_model(self, model_name: str, filepath: str):
        """Save trained model"""
        try:
            if model_name not in self.models:
                raise ValueError(f"Model {model_name} not found")
            
            model = self.models[model_name]
            joblib.dump(model, filepath)
            
            # Save feature engineering config
            config_path = filepath.replace('.pkl', '_config.json')
            self.feature_engineer.save_feature_config(config_path)
            
            logger.info(f"Model {model_name} saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self, filepath: str) -> Any:
        """Load trained model"""
        try:
            model = joblib.load(filepath)
            
            # Load feature engineering config
            config_path = filepath.replace('.pkl', '_config.json')
            self.feature_engineer.load_feature_config(config_path)
            
            logger.info(f"Model loaded from {filepath}")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
    
    def get_feature_importance(self, model_name: str) -> pd.Series:
        """Get feature importance from trained model"""
        try:
            if model_name not in self.models:
                raise ValueError(f"Model {model_name} not found")
            
            model = self.models[model_name]
            
            # Get feature importance based on model type
            if hasattr(model, 'feature_importances_'):
                importance = pd.Series(model.feature_importances_, index=self.feature_engineer.feature_columns)
            elif hasattr(model, 'coef_'):
                importance = pd.Series(np.abs(model.coef_[0]), index=self.feature_engineer.feature_columns)
            else:
                logger.warning(f"Model {model_name} does not support feature importance")
                return pd.Series()
            
            return importance.sort_values(ascending=False)
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return pd.Series()
    
    def train_ensemble_model(self, data_splits: Dict, model_names: List[str]) -> Dict:
        """
        Train ensemble model combining multiple models
        
        Args:
            data_splits: Prepared data splits
            model_names: List of model names to ensemble
            
        Returns:
            Ensemble model and performance
        """
        try:
            logger.info(f"Training ensemble model: {model_names}")
            
            # Get individual models
            individual_models = {}
            for model_name in model_names:
                if model_name in self.models:
                    individual_models[model_name] = self.models[model_name]
                else:
                    logger.warning(f"Model {model_name} not found, skipping")
            
            if len(individual_models) < 2:
                raise ValueError("Need at least 2 models for ensemble")
            
            # Create ensemble predictions
            train_predictions = {}
            val_predictions = {}
            test_predictions = {}
            
            for model_name, model in individual_models.items():
                train_predictions[model_name] = model.predict(data_splits['X_train'])
                val_predictions[model_name] = model.predict(data_splits['X_val'])
                test_predictions[model_name] = model.predict(data_splits['X_test'])
            
            # Average predictions for ensemble
            train_ensemble = np.mean(list(train_predictions.values()), axis=0)
            val_ensemble = np.mean(list(val_predictions.values()), axis=0)
            test_ensemble = np.mean(list(test_predictions.values()), axis=0)
            
            # Evaluate ensemble
            if any(self.model_performance[m]['model_type'] == 'classification' for m in individual_models):
                # Classification
                val_ensemble_class = (val_ensemble > 0.5).astype(int)
                test_ensemble_class = (test_ensemble > 0.5).astype(int)
                
                val_f1 = f1_score(data_splits['y_val'], val_ensemble_class, average='weighted')
                test_f1 = f1_score(data_splits['y_test'], test_ensemble_class, average='weighted')
                
                performance = {
                    'val_f1': val_f1,
                    'test_f1': test_f1,
                    'model_type': 'classification'
                }
                
                logger.info(f"Ensemble - Val F1: {val_f1:.3f}, Test F1: {test_f1:.3f}")
                
            else:
                # Regression
                val_r2 = r2_score(data_splits['y_val'], val_ensemble)
                test_r2 = r2_score(data_splits['y_test'], test_ensemble)
                
                performance = {
                    'val_r2': val_r2,
                    'test_r2': test_r2,
                    'model_type': 'regression'
                }
                
                logger.info(f"Ensemble - Val R2: {val_r2:.3f}, Test R2: {test_r2:.3f}")
            
            return {
                'ensemble_predictions': {
                    'train': train_ensemble,
                    'val': val_ensemble,
                    'test': test_ensemble
                },
                'individual_models': individual_models,
                'performance': performance
            }
            
        except Exception as e:
            logger.error(f"Error training ensemble model: {e}")
            return {}
