# Stock alerting

This project is a simple stock alerting system that sends an email when a stock price is above or below a certain threshold.

## Launch the project

Setup the environment variables by creating a `.env` file based on the `.env.example` file on the api folder.

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
