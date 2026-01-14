# 🤖 Binance DCA Bot for Ethereum

Automated Python bot for **Dollar Cost Averaging (DCA)** on Ethereum (ETH/USDC) via the Binance API.

## 📋 Features

- ✅ Automatic ETH purchase on specific days of month (e.g., 1st and 15th)
- ✅ **Reliable scheduling** with missed execution recovery (7-day grace period)
- ✅ Smart purchase logic based on momentum and PRUM (average purchase price)
- ✅ **Email notifications** for purchases, errors, and bot status
- ✅ Automatic USDC balance verification
- ✅ Automatic transfer from Binance Earn if needed
- ✅ Market orders for immediate execution
- ✅ Automatic retry with exponential backoff for network/API errors
- ✅ Detailed logging of each transaction (date, quantity, price, fees)
- ✅ Configuration via environment variables (secure)
- ✅ Automatic scheduler (APScheduler with CronTrigger)
- ✅ Test mode to verify configuration without buying

## 🔒 Security

- ⚠️ **NEVER** commit the `.env` file with your real API keys
- API keys are loaded from environment variables
- Required Binance API permissions: **Enable Spot & Margin Trading** + **Enable Reading**

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- Binance account with API keys configured

### Steps

1. **Clone or download the project**

```bash
cd dca_bot
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Create a `.env` file from the template:

```bash
cp .env.template .env
```

Edit the `.env` file and fill in your information:

```bash
# Binance API keys (REQUIRED)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Amount to invest per purchase (REQUIRED)
DCA_AMOUNT_USDC=50.0

# Days of month to execute
# Execute on 1st and 15th of each month
DCA_DAYS_OF_MONTH=1,15
```

4. **Create your Binance API keys**

- Go to [Binance API Management](https://www.binance.com/en/my/settings/api-management)
- Create a new API key
- Enable permissions: **Enable Spot & Margin Trading** and **Enable Reading**
- Copy the API key and secret to your `.env` file

## 🚀 Usage

### Test Mode (recommended to start)

Test the configuration without making a real purchase:

```bash
python -m dca_bot.main --test
```

This will:
- Verify connection to Binance API
- Display your balances
- Verify that the ETH/USDC symbol is valid
- Calculate the estimated amount of ETH that would be purchased

### Single manual execution

To execute a DCA purchase immediately (once):

```bash
python -m dca_bot.main --once
```

### Automatic scheduler mode

To start the bot in automatic mode (execution every 2 weeks):

```bash
python -m dca_bot.main
```

The bot will remain active and automatically execute purchases according to the configured schedule.

### Immediate execution + scheduler

To execute a purchase immediately then start the scheduler:

```bash
python -m dca_bot.main --now
```

## ⚙️ Configuration

All configurations are done in the `.env` file:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BINANCE_API_KEY` | Binance API key | - | ✅ |
| `BINANCE_API_SECRET` | Binance API secret | - | ✅ |
| `DCA_AMOUNT_USDC` | Amount in USDC per purchase | 50.0 | ✅ |
| `DCA_SYMBOL` | Trading pair | ETHUSDC | ❌ |
| `DCA_BASE_ASSET` | Asset to buy | ETH | ❌ |
| `DCA_QUOTE_ASSET` | Asset to spend | USDC | ❌ |
| `DCA_DAYS_OF_MONTH` | Days of month (e.g., "1,15") | 1,15 | ⭐ Recommended |
| `DCA_EXECUTION_HOUR` | Execution hour (0-23) | 10 | ❌ |
| `DCA_EXECUTION_MINUTE` | Execution minute (0-59) | 2 | ❌ |
| `SMTP_USER` | SMTP username | - | ❌ |
| `SMTP_PASSWORD` | SMTP password/app password | - | ❌ |

### 📧 Email Notifications

Get notified about:
- ✅ Successful purchases
- ⏭️ Skipped purchases (momentum filter)
- ❌ Errors
- 🚀 Bot startup after reboot

**Setup for Gmail:**
```env
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_TO=your_email@gmail.com
```

> **Note**: For Gmail, you need to create an [App Password](https://support.google.com/accounts/answer/185833) instead of using your regular password.

### Configuration examples

**Invest 100 USDC on 1st and 15th of each month:**
```env
DCA_AMOUNT_USDC=100.0
DCA_DAYS_OF_MONTH=1,15
```

**Invest 50 USDC on 1st of each month:**
```env
DCA_AMOUNT_USDC=50.0
DCA_DAYS_OF_MONTH=1
```

**Invest weekly on specific days:**
```env
DCA_AMOUNT_USDC=50.0
DCA_DAYS_OF_MONTH=1,8,15,22
```

**Buy Bitcoin instead of Ethereum:**
```env
DCA_SYMBOL=BTCUSDC
DCA_BASE_ASSET=BTC
DCA_QUOTE_ASSET=USDC
DCA_DAYS_OF_MONTH=1,15
```

## 📊 Logs

Logs are saved in `logs/dca_bot.log` with automatic rotation (max 10 MB per file).

Example of a successful purchase log:

```
2026-01-04 10:00:00 - dca_bot - INFO - ================================================================================
2026-01-04 10:00:00 - dca_bot - INFO - START DCA EXECUTION - 2026-01-04T10:00:00
2026-01-04 10:00:00 - dca_bot - INFO - Symbol: ETHUSDC
2026-01-04 10:00:00 - dca_bot - INFO - Amount: 50.0 USDC
2026-01-04 10:00:00 - dca_bot - INFO - ================================================================================
2026-01-04 10:00:01 - dca_bot - INFO - USDC spot balance: 100.5
2026-01-04 10:00:01 - dca_bot - INFO - Sufficient balance: 100.5 >= 50.0
2026-01-04 10:00:02 - dca_bot - INFO - Current ETHUSDC price: 3450.50
2026-01-04 10:00:03 - dca_bot - INFO - ================================================================================
2026-01-04 10:00:03 - dca_bot - INFO - ✅ DCA PURCHASE SUCCESSFUL!
2026-01-04 10:00:03 - dca_bot - INFO - Order ID: 123456789
2026-01-04 10:00:03 - dca_bot - INFO - Quantity purchased: 0.014492 ETH
2026-01-04 10:00:03 - dca_bot - INFO - Average price: 3450.50 USDC
2026-01-04 10:00:03 - dca_bot - INFO - Total cost: 50.0 USDC
2026-01-04 10:00:03 - dca_bot - INFO - Fees: 0.000014492 ETH
2026-01-04 10:00:03 - dca_bot - INFO - ================================================================================
```

## 🔄 Balance System Operation

1. **Spot balance check**: The bot first checks if you have enough USDC in your spot account.

2. **Transfer from Earn**: If the balance is insufficient, the bot checks your Binance Earn account (Simple Earn Flexible) and automatically transfers the necessary funds.

3. **Alert**: If funds are insufficient even after the transfer, the bot sends an alert in the logs and cancels the purchase.

## 🛠️ Production Deployment

### On a Linux server (recommended)

1. **Use a systemd service** to keep the bot running:

Create `/etc/systemd/system/dca-bot.service`:

```ini
[Unit]
Description=DCA Bot Binance
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/dca_bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python -m dca_bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable dca-bot
sudo systemctl start dca-bot
sudo systemctl status dca-bot
```

2. **Monitor the logs**:

```bash
sudo journalctl -u dca-bot -f
```

### With Docker (optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "dca_bot.main"]
```

Build and run:

```bash
docker build -t dca-bot .
docker run -d --name dca-bot --env-file .env dca-bot
```

## 🐛 Troubleshooting

### Error "Required environment variable missing"

Check that your `.env` file exists and contains all required variables (`BINANCE_API_KEY`, `BINANCE_API_SECRET`, `DCA_AMOUNT_USDC`).

### Binance API error "Invalid API-key"

- Verify that your API keys are correct
- Verify that permissions are enabled (Spot Trading + Reading)
- Verify that your server IP is authorized (if IP restriction enabled)

### Bot can't find funds in Earn

The bot uses the **Simple Earn Flexible** API. Make sure your funds are in flexible products and not locked.

### Error "Quantity less than minimum"

The configured amount is too low to buy the minimum quantity required by Binance. Increase `DCA_AMOUNT_USDC`.

## 📚 Code Structure

```
dca_bot/
├── __init__.py           # Package init
├── main.py               # Main entry point
├── config.py             # Configuration management
├── binance_client.py     # Binance API client
├── dca_executor.py       # Main DCA logic
├── scheduler.py          # APScheduler scheduler
├── logger.py             # Logging configuration
├── retry.py              # Retry decorators
├── .env.template          # Configuration template
├── .gitignore            # Files to ignore
├── requirements.txt      # Python dependencies
└── logs/                 # Logs folder
```

## ⚠️ Warning

**This bot performs real financial transactions.** 

- Start with small amounts
- Regularly check the logs
- The author is not responsible for financial losses

## 🔗 Resources

- [Binance API Documentation](https://binance-docs.github.io/apidocs/spot/en/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [DCA Strategy (Dollar Cost Averaging)](https://www.investopedia.com/terms/d/dollarcostaveraging.asp)
