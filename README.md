# Stock alerting

This project is a simple stock alerting system that sends an email when a stock price is above or below a certain threshold.

## Launch the project

To launch the project you have to setup a configuration file `config.json` in the root directory of the project. The configuration file should have the following structure:

```json
{
    "fund_name": "Fund name",
    "stocks": [
        {
            "symbol": "symbol_name",
            "parts_number": 1,
            "prum": 2,
            "current_repartition": 70,
            "target_repartition": 80,
            "arbitration_threshold": 5,
            "threshold_to_alert": 10
        },
    ],
    "FUND_UPDATE_INTERVAL": 60,
}
```

Then you can launch the project with the following command:
```bash
make run
```

## Run the tests

```bash
make tests
```

