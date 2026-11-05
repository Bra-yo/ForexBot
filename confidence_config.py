"""
SINGLE SOURCE OF TRUTH for the minimum trade confidence (percent, 0-100).

Every confidence gate in the bot reads this one value:
  - the candidate filter in multi_pair_live_bot_clean.py
  - EliteTradingConfig.MIN_CONFIDENCE in live_trading_executor.py
  - AdaptiveConfidenceSystem (frozen to this value, no self-adjustment)

Change it here and nowhere else.
"""

MIN_CONFIDENCE_PCT = 45.0