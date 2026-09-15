# AI-Based Indian Options Trading System

Experimental quantitative trading platform for NIFTY 50 options using Angel One SmartAPI.

## Disclaimer

- This is experimental trading software.
- Backtested performance does not guarantee future results.
- Paper-trading results do not guarantee live performance.
- Options trading involves substantial risk.
- AI predictions are probabilistic.
- Transaction costs and slippage can materially reduce returns.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your Angel One API credentials:
   ```bash
   cp .env.example .env
   ```

3. Run the milestone 1 script (retrieves and prints the NIFTY option chain):
   ```bash
   python app/main.py
   ```

## Development Phases

This project is being built in phases. Currently at Phase 1 & 2.

To run the backend:

bash
./scripts/start_api.sh

To run the frontend:

bash
cd frontend && npm run dev
