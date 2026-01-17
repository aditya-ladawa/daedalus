# Incremental RAGAS Evaluation Guide

## Overview

The RAGAS evaluation script now supports **incremental evaluation**, allowing you to run modes separately and merge results later. This is useful for long evaluations that might fail partway through.

## Workflow

### 1. Run Individual Modes

Run each mode separately. Results are automatically saved to mode-specific JSON files:

```bash
# Run naive mode (saves naive_results.json)
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes naive

# Run local mode (saves local_results.json)
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes local

# Run global mode (saves global_results.json)
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes global

# Run hybrid mode (saves hybrid_results.json)
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes hybrid
```

### 2. Merge Results

After running all modes, combine them into a unified report:

```bash
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --merge
```

This will:

- Find all `*_results.json` files in the results directory
- Generate a unified markdown report (`unified_report_TIMESTAMP.md`)
- Create a unified JSON file (`unified_evaluation_TIMESTAMP.json`)
- Display a comparison summary

## Output Files

### Individual Mode Runs

- `naive_results.json` - Naive mode results
- `local_results.json` - Local mode results
- `global_results.json` - Global mode results
- `hybrid_results.json` - Hybrid mode results
- `evaluation_TIMESTAMP.json` - Timestamped unified results (if running multiple modes at once)
- `report_TIMESTAMP.md` - Timestamped report

### Merge Operation

- `unified_report_TIMESTAMP.md` - Combined markdown report
- `unified_evaluation_TIMESTAMP.json` - Combined JSON results

## Advanced Options

### Custom Output Directory

```bash
# Save results to a custom directory
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes naive --output-dir my_results/

# Merge from custom directory
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --merge --output-dir my_results/
```

### Quick Testing

```bash
# Test with 2 questions
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes naive --quick
```

### Limited Questions

```bash
# Test with first 20 questions
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes naive --limit 20
```

## Example: Incremental Evaluation Workflow

```bash
# Day 1: Run naive and local (faster modes)
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes naive
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes local

# Day 2: Run global and hybrid (slower modes)
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes global
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes hybrid

# Day 3: Merge all results
python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --merge
```

## Benefits

1. **Resilience**: If one mode fails, you don't lose results from other modes
2. **Flexibility**: Run modes at different times or on different machines
3. **Debugging**: Easier to identify which mode is causing issues
4. **Time Management**: Spread long evaluations across multiple sessions
5. **Resource Management**: Run heavy modes when system resources are available

## Notes

- Each mode run overwrites its corresponding `*_results.json` file
- The merge operation creates new timestamped files without deleting individual mode files
- You can re-run the merge operation multiple times to generate new reports
- Individual mode files contain full per-question scores and metrics
