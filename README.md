# Coinbase Rebalance Agent

An always-on Python 3.12.4 rebalancing agent that automatically maintains target portfolio weights using Coinbase Advanced Trade REST v3 API.

## Purpose

This agent continuously monitors your crypto portfolio and executes trades to keep asset allocations within defined target weights and tolerance levels. It's designed to run 24/7 in the background, making small adjustments as market conditions change.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Coinbase Rebalance Agent                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    │
│  │   Config    │    │   Utils     │    │    Runner       │    │
│  │             │    │             │    │                 │    │
│  │ • Targets   │    │ • API Client│    │ • Rebalance     │    │
│  │ • Tolerance │    │ • Rounding  │    │ • Scheduler     │    │
│  │ • Limits    │    │ • NAV Calc  │    │ • Logging       │    │
│  └─────────────┘    └─────────────┘    └─────────────────┘    │
│         │                   │                   │              │
│         └───────────────────┼───────────────────┘              │
│                             │                                  │
│                             ▼                                  │
│                    ┌─────────────────┐                        │
│                    │ Coinbase API    │                        │
│                    │ Advanced Trade  │                        │
│                    │ REST v3         │                        │
│                    └─────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Automated Rebalancing**: Continuously monitors portfolio and executes trades
- **Dynamic Asset Selection**: Automatically selects top-performing USD-quoted assets
- **Configurable Targets**: Set custom target weights for each asset
- **Tolerance Levels**: Avoid excessive trading with configurable deviation thresholds
- **Minimum Notional**: Prevents tiny trades that incur high fees
- **Rich Logging**: Comprehensive logging with colored output
- **Sandbox Support**: Test with sandbox environment before going live
- **Jupyter Integration**: Analyze performance and test strategies

## Dynamic Selector

The agent now uses a dynamic selector that automatically chooses the best-performing USD-quoted cryptocurrency pairs from Coinbase Advanced Trade. This replaces the previous static asset list approach.

### How It Works

The scoring algorithm combines volume and momentum:
- **Score = 24h USD Volume × 3-day Price Momentum**
- **Volume**: Higher volume indicates better liquidity and market interest
- **Momentum**: 3-day price change percentage captures recent performance trends

### Configuration

Tune the selector behavior in `config.yml`:

```yaml
top_n: 25                      # Number of top assets to include
cash_buffer: 0.05              # Keep 5% in cash
tolerance: 0.007               # 0.7% rebalance threshold
liquidity_floor: 20000         # Minimum USD volume filter
rebalance_interval_minutes: 60 # Rebalance frequency
```

### Key Parameters

- **`top_n`**: Number of highest-scored assets to include in portfolio (default: 25)
- **`cash_buffer`**: Percentage to keep as cash buffer (default: 0.05 = 5%)
- **`tolerance`**: Rebalance threshold as fraction of NAV (default: 0.007 = 0.7%)
- **`liquidity_floor`**: Minimum 24h USD volume to consider (future use)

### Benefits

- **Adaptive**: Automatically adjusts to market conditions
- **Momentum-based**: Captures trending assets while maintaining diversification
- **Liquidity-aware**: Prioritizes tradeable assets with sufficient volume
- **Configurable**: Easy to tune parameters without code changes

## Quick Start

### Setup Environment

```bash
# Create and activate virtual environment
make venv

# Configure your API keys
cp .env.example .env
# Edit .env with your Coinbase API credentials
```

### Run the Agent

```bash
# Start the rebalancing agent (sandbox mode)
make run

# Launch Jupyter Lab for analysis
make notebook

# Deploy to production
make deploy
```

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Format code
black agent/ tests/
isort agent/ tests/

# Type checking
mypy agent/
```

## Configuration

The agent uses dynamic asset selection configured via `config.yml`:

```yaml
top_n: 25                      # Number of top assets to include
cash_buffer: 0.05              # Keep 5% in cash
tolerance: 0.007               # 0.7% rebalance threshold
liquidity_floor: 20000         # Minimum USD volume filter
rebalance_interval_minutes: 60 # Rebalance frequency
```

Additional settings in `agent/config.py`:

```python
TOLERANCE = Decimal("0.007")  # 0.7% tolerance
MIN_NOTIONAL = Decimal("10")  # Minimum $10 trades
MAX_SLIPPAGE = Decimal("0.005")  # Maximum allowed slippage
```

## Environment Variables

Create a `.env` file based on `.env.example`:

```
CB_API_KEY=your_api_key_here
CB_API_SECRET=your_api_secret_here
CB_API_PASSPHRASE=your_passphrase_here
CB_PORTFOLIO_ID=your_portfolio_id_here
CB_API_URL=https://api.coinbase.com
```

## Project Structure

```
coinbase_rebalance_agent/
├── agent/
│   ├── __init__.py
│   ├── config.py        # API settings and validation
│   ├── selector.py      # Dynamic asset selection logic
│   ├── utils.py         # Helper functions
│   └── runner.py        # Main rebalancing logic
├── notebooks/
│   └── 00_api_sanity.ipynb  # API testing and visualization
├── tests/
│   ├── test_utils.py    # Unit tests
│   └── test_selector.py # Selector unit tests
├── docs/
├── config.yml           # Dynamic selector configuration
├── requirements.txt
├── Makefile
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and formatting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Disclaimer

This software is for educational and research purposes. Use at your own risk. Cryptocurrency trading involves substantial risk of loss. 