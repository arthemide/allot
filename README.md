# Stock alerting

This project is a simple stock alerting system that sends an email when a stock price is above or below a certain threshold.

## Project Structure

- **api/** - FastAPI backend for stock alerting
- **front/** - Svelte frontend
- **bot/dca/** - Binance DCA (Dollar Cost Averaging) bot for automated crypto purchases

## Launch the stock alerting system

Setup the environment variables by creating a `.env` file based on the `.env.template` file on the api folder.

Then you can launch the project with the following command:
```bash
make up-debug
```

If you do not need to make the db migration, you can launch the project with:
```bash
make up-debug-no-mig
```

## Run the tests

```bash
cd api
make tests
```

## 🤖 DCA Bot - Automated Binance Trading

The DCA (Dollar Cost Averaging) bot automates cryptocurrency purchases on Binance.

### Quick Start

1. **Install dependencies:**
```bash
make dca-install
```

2. **Configure the bot:**
```bash
cd bot/dca
cp .env.template .env
# Edit .env with your Binance API keys and preferences
```

3. **Test configuration (recommended):**
```bash
make dca-test
```

4. **Run once manually:**
```bash
make dca-once
```

5. **Start the scheduler:**
```bash
make dca-start
```

### Available Commands

- `make dca-install` - Install bot dependencies
- `make dca-test` - Test configuration without real purchases
- `make dca-once` - Execute one DCA purchase
- `make dca-now` - Execute immediately then start scheduler
- `make dca-start` - Start scheduler (runs every 2 weeks)
- `make dca-logs` - View bot logs
- `make dca-install-service` - **macOS: Install as background service (recommended)**
- `make dca-uninstall-service` - macOS: Remove background service
- `make dca-status` - macOS: Check service status

### Deployment Options

**Recommandé pour macOS : Service automatique**
```bash
make dca-install-service
```
Le bot démarre automatiquement à chaque ouverture de session et se relance en cas de crash.

**Alternative : Lancement manuel**
```bash
make dca-start
```
Nécessite de garder le terminal ouvert.

### Configuration

All configuration is done via environment variables in `bot/dca/.env`:

- `BINANCE_API_KEY` - Your Binance API key
- `BINANCE_API_SECRET` - Your Binance API secret
- `DCA_AMOUNT_USDC` - Amount in USDC per purchase (e.g., 50.0)
- `DCA_DAYS_OF_MONTH` - Days of month to execute (e.g., 1,15)
- `DCA_SYMBOL` - Trading pair (default: ETHUSDC)

See `bot/dca/.env.template` for all available options.

### Page Bot (`/bot`)

The `/bot` page provides a visual interface for DCA bot transactions recorded in the database:

- **Fund selector** — filter transactions by fund
- **Cumulative investment chart** — line chart showing cumulative investment per asset over time (Chart.js)
- **Transaction timeline** — bar chart of transaction amounts, color-coded by type (buy/sell)
- **Transactions table** — detailed list with date, asset, type badge, quantity, price, and total

### Features

✅ Automatic balance checking (spot + earn)  
✅ Automatic transfer from Binance Earn if needed  
✅ Market orders for immediate execution  
✅ Retry with exponential backoff  
✅ Detailed logging with rotation  
✅ Configurable scheduling  

For detailed documentation, see `bot/dca/README.md`.
