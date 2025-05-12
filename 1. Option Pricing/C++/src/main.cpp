#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <cmath>
#include <random>
#include <chrono>
#include <sstream>
#include <iomanip>
#include "csv.h"

struct OptionData {
    std::string symbol;
    double strike;
    std::string expiry_dt;
    std::string timestamp;
    std::string option_type;
    double close;
    double settle_pr;
    int expiry_days;
};

class OptionPricing {
public:
    OptionPricing(std::string symbol, double spot_price, double strike, double expiry,
                  std::string option_type, double market_price,
                  double volatility, double risk_free_rate)
        : symbol(symbol), spot_price(spot_price), strike(strike), expiry(expiry),
          option_type(option_type), market_price(market_price),
          volatility(volatility), risk_free_rate(risk_free_rate) {}

    double price(int num_simulations = 1000) {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::normal_distribution<> dist(0.0, 1.0);
        double sum_payoff = 0.0;

        for (int i = 0; i < num_simulations; ++i) {
            double Z = dist(gen);
            double ST = spot_price * std::exp((risk_free_rate - 0.5 * volatility * volatility) * expiry
                                              + volatility * std::sqrt(expiry) * Z);
            double payoff = 0.0;
            if (option_type == "CE")
                payoff = std::max(ST - strike, 0.0);
            else if (option_type == "PE")
                payoff = std::max(strike - ST, 0.0);
            sum_payoff += payoff;
        }
        return (sum_payoff / num_simulations) * std::exp(-risk_free_rate * expiry);
    }

private:
std::string symbol;
double spot_price;
double strike;
double expiry;
std::string option_type;
double market_price;
double volatility;
double risk_free_rate;
};

int main() {
    std::vector<OptionData> options;

    // Load CSV
    io::CSVReader<7> in("data/data.csv");
    in.read_header(io::ignore_extra_column, "SYMBOL", "STRIKE_PR", "EXPIRY_DT", "TIMESTAMP",
                   "OPTION_TYP", "CLOSE", "SETTLE_PR");

    OptionData row;
    std::string expiry_str, timestamp_str;
    while (in.read_row(row.symbol, row.strike, expiry_str, timestamp_str,
                       row.option_type, row.close, row.settle_pr)) {

        // Parse date strings
        std::tm expiry_tm = {}, timestamp_tm = {};
        std::istringstream(expiry_str) >> std::get_time(&expiry_tm, "%Y-%m-%d");
        std::istringstream(timestamp_str) >> std::get_time(&timestamp_tm, "%Y-%m-%d");

        std::time_t expiry_time = std::mktime(&expiry_tm);
        std::time_t timestamp_time = std::mktime(&timestamp_tm);

        int days = std::difftime(expiry_time, timestamp_time) / (60 * 60 * 24);


        row.expiry_dt = expiry_str;
        row.timestamp = timestamp_str;

        options.push_back(row);
    }

    std::map<std::string, double> spot_prices;
    double rf = 0.05;
    double volatility = 0.2;

    // Calculate spot prices
    for (size_t i = 0; i < options.size(); i += 2) {
        auto call = options[i];
        auto put = options[i + 1];
        double T = std::max(call.expiry_days / 365.0, 1.0 / 365);
        double spot = call.close - put.close + call.strike * std::exp(-rf * T);

        std::string key = call.symbol + "|" + call.expiry_dt + "|" + call.timestamp + "|" + std::to_string((int)call.strike);
        spot_prices[key] = spot;
    }

    // Price model and write output
    std::ofstream out("output.csv");
    out << "SYMBOL,STRIKE_PR,EXPIRY_DT,TIMESTAMP,OPTION_TYP,CLOSE,SETTLE_PR,EXPIRY_DAYS,Model_Price,Price_Difference\n";

    for (auto &opt : options) {
        double expiry_years = std::max(opt.expiry_days / 365.0, 1.0 / 365.0);
        std::string key = opt.symbol + "|" + opt.expiry_dt + "|" + opt.timestamp + "|" + std::to_string((int)opt.strike);
        double approx_spot = spot_prices[key];

        OptionPricing pricer(opt.symbol, approx_spot, opt.strike, expiry_years, opt.option_type,
                             opt.settle_pr, volatility, rf);
        double model_price = pricer.price();
        double diff = model_price - opt.close;

        out << opt.symbol << "," << opt.strike << "," << opt.expiry_dt << "," << opt.timestamp << ","
            << opt.option_type << "," << opt.close << "," << opt.settle_pr << "," << opt.expiry_days
            << "," << model_price << "," << diff << "\n";
    }

    std::cout << "Pricing complete. Output saved to output.csv\n";
    return 0;
}
