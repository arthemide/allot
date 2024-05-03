import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yfinance as yf


# Function to fetch stock data
def get_stock_price(symbol):
    stock_data = yf.Ticker(symbol)
    return stock_data.history(period="1d")["Close"][0]


# Function to send email alerts
def send_email(subject, body):
    sender_email = "your_email@gmail.com"
    receiver_email = "recipient_email@gmail.com"
    password = "your_password"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())


# Main function
def main():
    stock_symbol = "AAPL"
    target_price = 150.0

    while True:
        current_price = get_stock_price(stock_symbol)

        if current_price < target_price:
            subject = f"{stock_symbol} Alert!"
            body = f"{stock_symbol} price is below {target_price}. Current price: {current_price}"
            send_email(subject, body)
            print("Alert sent!")

        # Sleep for some time before checking again
        # Adjust this value based on how frequently you want to check
        time.sleep(300)  # Check every 5 minutes


if __name__ == "__main__":
    main()
