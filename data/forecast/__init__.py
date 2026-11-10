"""Price-prediction forecasting package (docs/price-prediction-plan.md).

Stufe 1: baselines + rolling-origin evaluation harness, built on top of
Stufe 0's ``forecast_input`` view. Reads the master DB read-only (G6);
writes only to ``price_forecasts`` (Stufe 5), never back into ``lots``.
"""
