"""
Strategy Optimization Framework for BrayoForexBot
Finds optimal parameters through systematic testing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Callable, Any
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from datetime import datetime
import logging
from backtest import BacktestEngine

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    """
    Advanced Strategy Optimizer
    Uses grid search and genetic algorithms to find optimal parameters
    """
    
    def __init__(self, data: pd.DataFrame, initial_balance: float = 10000):
        self.data = data
        self.initial_balance = initial_balance
        self.optimization_results = []
        self.best_parameters = {}
        
    def grid_search(self, 
                   strategy_func: Callable,
                   parameter_grid: Dict[str, List],
                   metric: str = 'total_return_pct',
                   maximize: bool = True,
                   parallel: bool = True) -> Dict:
        """
        Perform grid search optimization
        
        Args:
            strategy_func: Strategy function to optimize
            parameter_grid: Dictionary of parameters to test
            metric: Metric to optimize
            maximize: Whether to maximize or minimize the metric
            parallel: Use parallel processing
            
        Returns:
            Best parameters and results
        """
        logger.info(f"🔥 Starting grid search with {len(parameter_grid)} parameters")
        
        # Generate all parameter combinations
        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())
        combinations = list(itertools.product(*param_values))
        
        logger.info(f"Testing {len(combinations)} parameter combinations...")
        
        # Test each combination
        results = []
        
        if parallel and len(combinations) > 10:
            results = self._parallel_grid_search(strategy_func, param_names, combinations, metric)
        else:
            results = self._sequential_grid_search(strategy_func, param_names, combinations, metric)
        
        # Find best parameters
        if maximize:
            best_result = max(results, key=lambda x: x['metrics'].get(metric, 0))
        else:
            best_result = min(results, key=lambda x: x['metrics'].get(metric, float('inf')))
        
        self.optimization_results = results
        self.best_parameters = best_result['parameters']
        
        logger.info(f"✅ Grid search completed. Best {metric}: {best_result['metrics'].get(metric, 0):.2f}")
        
        return {
            'best_parameters': best_result['parameters'],
            'best_metrics': best_result['metrics'],
            'all_results': results,
            'total_combinations': len(combinations)
        }
    
    def _parallel_grid_search(self, strategy_func: Callable, param_names: List[str], 
                            combinations: List[Tuple], metric: str) -> List[Dict]:
        """Run grid search in parallel"""
        results = []
        
        with ProcessPoolExecutor(max_workers=4) as executor:
            # Submit all tasks
            future_to_params = {}
            for i, combination in enumerate(combinations):
                params = dict(zip(param_names, combination))
                future = executor.submit(self._test_parameters, strategy_func, params)
                future_to_params[future] = params
            
            # Collect results
            for future in as_completed(future_to_params):
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Progress update
                    if len(results) % 10 == 0:
                        logger.info(f"Tested {len(results)}/{len(combinations)} combinations")
                        
                except Exception as e:
                    logger.error(f"Error in parallel optimization: {e}")
        
        return results
    
    def _sequential_grid_search(self, strategy_func: Callable, param_names: List[str], 
                              combinations: List[Tuple], metric: str) -> List[Dict]:
        """Run grid search sequentially"""
        results = []
        
        for i, combination in enumerate(combinations):
            params = dict(zip(param_names, combination))
            result = self._test_parameters(strategy_func, params)
            results.append(result)
            
            # Progress update
            if (i + 1) % 10 == 0:
                logger.info(f"Tested {i + 1}/{len(combinations)} combinations")
        
        return results
    
    def _test_parameters(self, strategy_func: Callable, parameters: Dict) -> Dict:
        """Test a single parameter set"""
        try:
            # Create strategy function with parameters
            def parameterized_strategy(data):
                return strategy_func(data, **parameters)
            
            # Run backtest
            backtest = BacktestEngine(self.initial_balance)
            results = backtest.run_backtest(self.data, parameterized_strategy)
            
            return {
                'parameters': parameters,
                'metrics': results['metrics'],
                'trades': len(results['trades']),
                'final_balance': results['final_balance']
            }
            
        except Exception as e:
            logger.error(f"Error testing parameters {parameters}: {e}")
            return {
                'parameters': parameters,
                'metrics': {'error': str(e)},
                'trades': 0,
                'final_balance': self.initial_balance
            }
    
    def genetic_algorithm(self, 
                        strategy_func: Callable,
                        param_ranges: Dict[str, Tuple[float, float]],
                        population_size: int = 50,
                        generations: int = 100,
                        mutation_rate: float = 0.1,
                        metric: str = 'total_return_pct',
                        maximize: bool = True) -> Dict:
        """
        Genetic algorithm optimization
        
        Args:
            strategy_func: Strategy function to optimize
            param_ranges: Parameter ranges (min, max)
            population_size: Size of population
            generations: Number of generations
            mutation_rate: Mutation probability
            metric: Fitness metric
            maximize: Whether to maximize fitness
            
        Returns:
            Best parameters and evolution history
        """
        logger.info(f"🧬 Starting genetic algorithm optimization...")
        
        # Initialize population
        population = self._initialize_population(param_ranges, population_size)
        evolution_history = []
        
        for generation in range(generations):
            # Evaluate fitness
            fitness_scores = []
            for individual in population:
                params = self._individual_to_params(individual, param_ranges)
                result = self._test_parameters(strategy_func, params)
                fitness = result['metrics'].get(metric, 0)
                fitness_scores.append(fitness)
            
            # Record best individual
            if maximize:
                best_idx = np.argmax(fitness_scores)
            else:
                best_idx = np.argmin(fitness_scores)
            
            best_params = self._individual_to_params(population[best_idx], param_ranges)
            best_result = self._test_parameters(strategy_func, best_params)
            
            evolution_history.append({
                'generation': generation,
                'best_fitness': fitness_scores[best_idx],
                'avg_fitness': np.mean(fitness_scores),
                'best_parameters': best_params,
                'best_metrics': best_result['metrics']
            })
            
            # Progress update
            if (generation + 1) % 10 == 0:
                logger.info(f"Generation {generation + 1}: Best {metric} = {fitness_scores[best_idx]:.2f}")
            
            # Selection and reproduction
            population = self._evolve_population(population, fitness_scores, param_ranges, 
                                              mutation_rate, maximize)
        
        # Get final best parameters
        final_best = evolution_history[-1]
        
        logger.info(f"✅ Genetic algorithm completed. Best {metric}: {final_best['best_fitness']:.2f}")
        
        return {
            'best_parameters': final_best['best_parameters'],
            'best_metrics': final_best['best_metrics'],
            'evolution_history': evolution_history,
            'generations': generations
        }
    
    def _initialize_population(self, param_ranges: Dict[str, Tuple[float, float]], 
                             size: int) -> List[List[float]]:
        """Initialize random population"""
        population = []
        param_names = list(param_ranges.keys())
        
        for _ in range(size):
            individual = []
            for param_name in param_names:
                min_val, max_val = param_ranges[param_name]
                individual.append(np.random.uniform(min_val, max_val))
            population.append(individual)
        
        return population
    
    def _individual_to_params(self, individual: List[float], param_ranges: Dict[str, Tuple[float, float]]) -> Dict:
        """Convert individual to parameters dictionary"""
        param_names = list(param_ranges.keys())
        return dict(zip(param_names, individual))
    
    def _evolve_population(self, population: List[List[float]], fitness_scores: List[float],
                          param_ranges: Dict[str, Tuple[float, float]], mutation_rate: float,
                          maximize: bool) -> List[List[float]]:
        """Evolve population through selection, crossover, and mutation"""
        # Selection (tournament selection)
        selected = self._tournament_selection(population, fitness_scores, maximize)
        
        # Crossover
        offspring = self._crossover(selected)
        
        # Mutation
        mutated = self._mutate(offspring, param_ranges, mutation_rate)
        
        return mutated
    
    def _tournament_selection(self, population: List[List[float]], fitness_scores: List[float],
                              maximize: bool, tournament_size: int = 3) -> List[List[float]]:
        """Tournament selection"""
        selected = []
        population_size = len(population)
        
        for _ in range(population_size):
            # Random tournament
            tournament_indices = np.random.choice(population_size, tournament_size, replace=False)
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            
            if maximize:
                winner_idx = tournament_indices[np.argmax(tournament_fitness)]
            else:
                winner_idx = tournament_indices[np.argmin(tournament_fitness)]
            
            selected.append(population[winner_idx].copy())
        
        return selected
    
    def _crossover(self, selected: List[List[float]]) -> List[List[float]]:
        """Single-point crossover"""
        offspring = []
        
        for i in range(0, len(selected), 2):
            if i + 1 < len(selected):
                parent1 = selected[i]
                parent2 = selected[i + 1]
                
                # Single-point crossover
                crossover_point = np.random.randint(1, len(parent1))
                
                child1 = parent1[:crossover_point] + parent2[crossover_point:]
                child2 = parent2[:crossover_point] + parent1[crossover_point:]
                
                offspring.extend([child1, child2])
            else:
                offspring.append(selected[i])
        
        return offspring
    
    def _mutate(self, offspring: List[List[float]], param_ranges: Dict[str, Tuple[float, float]],
                mutation_rate: float) -> List[List[float]]:
        """Gaussian mutation"""
        mutated = []
        
        for individual in offspring:
            mutated_individual = individual.copy()
            
            for i in range(len(mutated_individual)):
                if np.random.random() < mutation_rate:
                    # Gaussian mutation
                    param_name = list(param_ranges.keys())[i]
                    min_val, max_val = param_ranges[param_name]
                    
                    # Add small random noise
                    noise = np.random.normal(0, (max_val - min_val) * 0.1)
                    mutated_value = mutated_individual[i] + noise
                    
                    # Clamp to valid range
                    mutated_individual[i] = np.clip(mutated_value, min_val, max_val)
            
            mutated.append(mutated_individual)
        
        return mutated
    
    def walk_forward_optimization(self, 
                                 strategy_func: Callable,
                                 parameter_grid: Dict[str, List],
                                 train_periods: int = 12,
                                 test_periods: int = 3,
                                 metric: str = 'total_return_pct') -> Dict:
        """
        Walk-forward optimization
        
        Args:
            strategy_func: Strategy function to optimize
            parameter_grid: Parameter grid for optimization
            train_periods: Number of periods for training
            test_periods: Number of periods for testing
            metric: Metric to optimize
            
        Returns:
            Walk-forward results
        """
        logger.info("🚶 Starting walk-forward optimization...")
        
        # Split data into periods
        total_periods = len(self.data) // (train_periods + test_periods)
        walk_results = []
        
        for period in range(total_periods):
            # Define train and test ranges
            train_start = period * (train_periods + test_periods)
            train_end = train_start + train_periods
            test_start = train_end
            test_end = test_start + test_periods
            
            if test_end >= len(self.data):
                break
            
            train_data = self.data.iloc[train_start:train_end]
            test_data = self.data.iloc[test_start:test_end]
            
            logger.info(f"Period {period + 1}: Training {len(train_data)} bars, Testing {len(test_data)} bars")
            
            # Optimize on training data
            optimizer = StrategyOptimizer(train_data, self.initial_balance)
            train_results = optimizer.grid_search(strategy_func, parameter_grid, metric)
            
            # Test on out-of-sample data
            best_params = train_results['best_parameters']
            
            def optimized_strategy(data):
                return strategy_func(data, **best_params)
            
            backtest = BacktestEngine(self.initial_balance)
            test_results = backtest.run_backtest(test_data, optimized_strategy)
            
            walk_results.append({
                'period': period + 1,
                'train_start': train_start,
                'train_end': train_end,
                'test_start': test_start,
                'test_end': test_end,
                'best_parameters': best_params,
                'train_metrics': train_results['best_metrics'],
                'test_metrics': test_results['metrics'],
                'train_return': train_results['best_metrics'].get(metric, 0),
                'test_return': test_results['metrics'].get(metric, 0)
            })
        
        # Calculate overall performance
        total_train_return = sum(r['train_return'] for r in walk_results)
        total_test_return = sum(r['test_return'] for r in walk_results)
        
        logger.info(f"✅ Walk-forward completed. Train: {total_train_return:.2f}, Test: {total_test_return:.2f}")
        
        return {
            'period_results': walk_results,
            'total_train_return': total_train_return,
            'total_test_return': total_test_return,
            'overfitting_ratio': total_test_return / total_train_return if total_train_return != 0 else 0
        }
    
    def save_optimization_results(self, results: Dict, filepath: str):
        """Save optimization results to file"""
        try:
            # Convert numpy types to JSON serializable
            serializable_results = self._make_json_serializable(results)
            
            with open(filepath, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            logger.info(f"Optimization results saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def _make_json_serializable(self, obj):
        """Convert numpy types to JSON serializable"""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        else:
            return obj
    
    def plot_optimization_results(self, results: Dict, save_path: str = None):
        """Plot optimization results"""
        import matplotlib.pyplot as plt
        
        if 'all_results' in results:  # Grid search results
            self._plot_grid_search_results(results, save_path)
        elif 'evolution_history' in results:  # Genetic algorithm results
            self._plot_genetic_algorithm_results(results, save_path)
        elif 'period_results' in results:  # Walk-forward results
            self._plot_walk_forward_results(results, save_path)
    
    def _plot_grid_search_results(self, results: Dict, save_path: str = None):
        """Plot grid search results"""
        all_results = results['all_results']
        
        # Extract metrics
        returns = [r['metrics'].get('total_return_pct', 0) for r in all_results]
        win_rates = [r['metrics'].get('win_rate', 0) for r in all_results]
        sharpe_ratios = [r['metrics'].get('sharpe_ratio', 0) for r in all_results]
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Grid Search Optimization Results', fontsize=16)
        
        # Return distribution
        axes[0, 0].hist(returns, bins=30, alpha=0.7, color='green')
        axes[0, 0].set_title('Return Distribution')
        axes[0, 0].set_xlabel('Return (%)')
        axes[0, 0].set_ylabel('Frequency')
        
        # Win Rate vs Return
        axes[0, 1].scatter(win_rates, returns, alpha=0.6)
        axes[0, 1].set_title('Win Rate vs Return')
        axes[0, 1].set_xlabel('Win Rate (%)')
        axes[0, 1].set_ylabel('Return (%)')
        
        # Sharpe Ratio vs Return
        axes[1, 0].scatter(sharpe_ratios, returns, alpha=0.6, color='orange')
        axes[1, 0].set_title('Sharpe Ratio vs Return')
        axes[1, 0].set_xlabel('Sharpe Ratio')
        axes[1, 0].set_ylabel('Return (%)')
        
        # Best parameters
        best_params = results['best_parameters']
        param_text = '\n'.join([f"{k}: {v}" for k, v in best_params.items()])
        axes[1, 1].text(0.1, 0.5, f"Best Parameters:\n\n{param_text}", 
                        fontsize=10, verticalalignment='center')
        axes[1, 1].set_title('Best Parameters')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def _plot_genetic_algorithm_results(self, results: Dict, save_path: str = None):
        """Plot genetic algorithm evolution"""
        history = results['evolution_history']
        
        generations = [h['generation'] for h in history]
        best_fitness = [h['best_fitness'] for h in history]
        avg_fitness = [h['avg_fitness'] for h in history]
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Genetic Algorithm Evolution', fontsize=16)
        
        # Fitness evolution
        axes[0].plot(generations, best_fitness, label='Best Fitness', linewidth=2)
        axes[0].plot(generations, avg_fitness, label='Average Fitness', linewidth=2)
        axes[0].set_title('Fitness Evolution')
        axes[0].set_xlabel('Generation')
        axes[0].set_ylabel('Fitness')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Best parameters
        best_params = results['best_parameters']
        param_text = '\n'.join([f"{k}: {v:.3f}" for k, v in best_params.items()])
        axes[1].text(0.1, 0.5, f"Best Parameters:\n\n{param_text}", 
                    fontsize=10, vertical_alignment='center')
        axes[1].set_title('Final Best Parameters')
        axes[1].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def _plot_walk_forward_results(self, results: Dict, save_path: str = None):
        """Plot walk-forward results"""
        periods = results['period_results']
        
        period_numbers = [p['period'] for p in periods]
        train_returns = [p['train_return'] for p in periods]
        test_returns = [p['test_return'] for p in periods]
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
        fig.suptitle('Walk-Forward Optimization Results', fontsize=16)
        
        # Returns comparison
        x = np.arange(len(period_numbers))
        width = 0.35
        
        axes[0].bar(x - width/2, train_returns, width, label='Train Return', alpha=0.7)
        axes[0].bar(x + width/2, test_returns, width, label='Test Return', alpha=0.7)
        axes[0].set_title('Train vs Test Returns')
        axes[0].set_xlabel('Period')
        axes[0].set_ylabel('Return (%)')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(period_numbers)
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Cumulative returns
        cumulative_train = np.cumsum(train_returns)
        cumulative_test = np.cumsum(test_returns)
        
        axes[1].plot(period_numbers, cumulative_train, 'o-', label='Cumulative Train', linewidth=2)
        axes[1].plot(period_numbers, cumulative_test, 'o-', label='Cumulative Test', linewidth=2)
        axes[1].set_title('Cumulative Returns')
        axes[1].set_xlabel('Period')
        axes[1].set_ylabel('Cumulative Return (%)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
