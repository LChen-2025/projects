import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

class OptionPricing:
    def __init__(self, symbol, spot_price, strike, expiry, option_type, market_price, volatility, risk_free_rate):
        self.symbol = symbol
        self.spot_price = spot_price
        self.strike = strike
        self.expiry = expiry
        self.option_type = option_type
        self.market_price = market_price
        self.volatility = volatility
        self.risk_free_rate = risk_free_rate

    
    def price(self, num_simulations=1000):
        S0 = self.spot_price
        X = self.strike
        T = self.expiry
        sigma = self.volatility
        r = self.risk_free_rate

        Z = np.random.normal(size=num_simulations)

        # simulate option paths
        ST = S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * T**0.5 * Z)

        if self.option_type == "CE": # call option
            payoff_T = np.maximum(ST - X, 0)
        elif self.option_type == "PE": # put option
            payoff_T = np.maximum(X - ST, 0)

        # Discount payoff
        payoff_0 = np.mean(payoff_T) * np.exp(-r * T)

        return payoff_0




# load data
# data source: https://www.kaggle.com/datasets/sunnysai12345/nse-future-and-options-dataset-3m/data

df_raw = pd.read_csv("data/data.csv")
df = df_raw[(df_raw["OPTION_TYP"]=="CE") | (df_raw["OPTION_TYP"]=="PE")]
# df = df[((df["SYMBOL"]=="BANKNIFTY") & (df["EXPIRY_DT"]=="03-OCT-2019") & (df["STRIKE_PR"]==29700)) | ((df["SYMBOL"]=="ACC")& (df["EXPIRY_DT"]=="31-OCT-2019") & (df["STRIKE_PR"]==1400))]
df = df[((df["SYMBOL"]=="BANKNIFTY") & (df["STRIKE_PR"]==29700)) | ((df["SYMBOL"]=="ACC")& (df["STRIKE_PR"]==1400))]
df = df.reset_index()
# df.to_csv("temp.csv", index=False)


df["EXPIRY_DT"] = pd.to_datetime(df["EXPIRY_DT"], format="%d-%b-%Y") 
df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], format="%d-%b-%Y")
df["EXPIRY_DAYS"]= (df["EXPIRY_DT"] - df["TIMESTAMP"]).dt.days



# Assumptions
rf = 0.05
volatility = 0.2


# Option chain-based approximation: spot price ~ strike price where call and put premiums are closet
df_unique = df[["SYMBOL", "STRIKE_PR", "EXPIRY_DT", "TIMESTAMP", "OPTION_TYP", "EXPIRY_DAYS"]].drop_duplicates()

spot_price_list = []
for j in range(0, len(df_unique)):
    symbol = df_unique["SYMBOL"].values[j]
    strike = df_unique["STRIKE_PR"].values[j]
    expiry = df_unique["EXPIRY_DT"].values[j]
    timestamp = df_unique["TIMESTAMP"].values[j]
    option = df_unique["OPTION_TYP"].values[j]
    expiry_days = df_unique["EXPIRY_DAYS"].values[j]

    # filter
    df_call = df[(df["SYMBOL"] == symbol) & (df["STRIKE_PR"] == strike) &
              (df["EXPIRY_DT"] == expiry) & (df["TIMESTAMP"] == timestamp) &
              (df["OPTION_TYP"] == "CE")]
    
    df_put = df[(df["SYMBOL"] == symbol) & (df["STRIKE_PR"] == strike) &
              (df["EXPIRY_DT"] == expiry) & (df["TIMESTAMP"] == timestamp) &
              (df["OPTION_TYP"] == "PE")]

    call_price = df_call.iloc[0]["CLOSE"]
    put_price = df_put.iloc[0]["CLOSE"]

    T = max(expiry_days / 365, 1 / 365)

    spot = call_price - put_price + strike * np.exp(-rf * T)

    spot_price_list.append({
        "SYMBOL": symbol,
        "STRIKE_PR": strike,
        "EXPIRY_DT": expiry,
        "TIMESTAMP": timestamp,
        "Approx_Spot_Price": spot
    }
    )
    # print(spot_price_list[j])

df_spot = pd.DataFrame(spot_price_list)
df_spot.to_csv("spot_price.csv", index=False)


# join spot price to df
df_joined = pd.merge(df, df_spot, on=["SYMBOL", "STRIKE_PR", "EXPIRY_DT", "TIMESTAMP"], how="left")


model_price_list = []; diff_list = []


for i in range(0, len(df_joined)):
    expiry_days = df_joined["EXPIRY_DAYS"].values[i]
    expiry_years = max(expiry_days / 365, 1 / 365)

    option = OptionPricing(
        symbol = df_joined["SYMBOL"].values[i],
        spot_price = df_joined["Approx_Spot_Price"].values[i],
        strike = df_joined["STRIKE_PR"].values[i],
        expiry = expiry_years,
        option_type = df_joined["OPTION_TYP"].values[i],
        market_price = df_joined["SETTLE_PR"].values[i],
        volatility = volatility,
        risk_free_rate = rf
    )

    model_price = option.price()
    price_diff = model_price - df_joined["CLOSE"].values[i]

    model_price_list.append(model_price) 
    diff_list.append(price_diff)



# export
df_result = pd.DataFrame()

df_result["Model_Price"] = model_price_list
df_result["Price_Difference"] = diff_list

df_output = pd.concat([df_joined.reset_index(drop=True), df_result.reset_index(drop=True)], axis=1)
df_output.to_csv("output.csv", index=False)




def plot_figure(symbol, expiry_date, option_type, strike_price):
    if option_type == "CE":
        option_title = "Call Option"
    elif option_type == "PE":
        option_title = "Put Option"

    # df_sub = df_output[(df_output["SYMBOL"]==symbol) & (df_output["EXPIRY_DT"]==datetime.strptime(expiry_date, "%Y-%m-%d").date()) & (df_output["OPTION_TYP"]==option_type)]
    df_sub = df_output[(df_output["SYMBOL"]==symbol) & (df_output["EXPIRY_DT"]==expiry_date) & (df_output["OPTION_TYP"]==option_type) & (df_output["STRIKE_PR"]==strike_price)]

    df_sub = df_sub.sort_values(by=["TIMESTAMP"])
    df_sub = df_sub.reset_index()

    plt.figure(figsize=(10, 6))
    plt.plot(df_sub["TIMESTAMP"], df_sub["SETTLE_PR"], label="Market Price", color="blue")
    plt.plot(df_sub["TIMESTAMP"], df_sub["Model_Price"], label="Model Price", color="red")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.title(f"{symbol} {option_title} - Expiry date: {expiry_date} & Strike price: {strike_price}")
    plt.legend()
    # plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the plot as a PNG file
    plt.savefig(f"market_vs_model_price_{symbol}_{option_title}_{expiry_date}.png")

plot_figure("BANKNIFTY", "2019-10-03", "CE", 29700)
plot_figure("BANKNIFTY", "2019-10-03", "PE", 29700)
plot_figure("ACC", "2019-10-31", "CE", 1400)
plot_figure("ACC", "2019-10-31", "PE", 1400)
