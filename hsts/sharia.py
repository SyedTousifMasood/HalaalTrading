import pandas as pd
import yfinance as yf
import logging

logger = logging.getLogger("hsts.sharia")

# Non-permissible industries/sectors
NON_PERMISSIBLE_SECTORS = ["Financial Services"]
NON_PERMISSIBLE_INDUSTRIES = [
    "Banks—Regional", "Banks—Diversified", "Insurance—Life", 
    "Insurance—Property & Casualty", "Insurance Brokers", 
    "Credit Services", "Asset Management", "Tobacco", 
    "Brewers", "Beverages—Wineries & Distilleries", "Gambling"
]

class ShariaScreeningEngine:
    def __init__(self, universe_csv_path="data/universe.csv", cache_path="data/sharia_cache.json"):
        self.universe_csv_path = universe_csv_path
        self.universe = pd.read_csv(universe_csv_path)
        self.cache_path = cache_path
        self.cache = self._load_cache()

    def is_business_compliant(self, info):
        """
        Screen stock based on core business activities.
        """
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        business_summary = info.get("longBusinessSummary", "").lower()

        # Check sector & industry exclusions
        if sector in NON_PERMISSIBLE_SECTORS:
            # Most Indian financial services are conventional/interest-based.
            logger.info(f"Rejected: Non-permissible sector '{sector}'")
            return False

        if industry in NON_PERMISSIBLE_INDUSTRIES:
            logger.info(f"Rejected: Non-permissible industry '{industry}'")
            return False

        # Keywords check in business summary
        haram_keywords = ["tobacco", "alcohol", "liquor", "casino", "gambling", "pork", "interest-based"]
        for kw in haram_keywords:
            if kw in business_summary:
                logger.info(f"Rejected: Haram keyword '{kw}' found in business summary")
                return False

        return True

    def get_financial_ratios(self, ticker):
        """
        Fetch balance sheet and calculate financial ratios.
        Ratios are calculated using quarterly reports.
        """
        try:
            balance_sheet = ticker.quarterly_balance_sheet
            financials = ticker.quarterly_financials

            if balance_sheet.empty or financials.empty:
                # Fallback to annual if quarterly is empty
                balance_sheet = ticker.balance_sheet
                financials = ticker.financials

            if balance_sheet.empty:
                return None

            # Get latest period columns
            latest_bs = balance_sheet.iloc[:, 0]
            latest_fin = financials.iloc[:, 0] if not financials.empty else None

            # Total Assets
            total_assets = latest_bs.get("Total Assets", 0)
            if total_assets == 0:
                return None

            # Debt (Long Term Debt + Short Term Debt)
            long_term_debt = latest_bs.get("Long Term Debt", 0)
            short_term_debt = latest_bs.get("Short Term Debt / Current Portion of Long Term Debt", 0)
            if short_term_debt == 0:
                short_term_debt = latest_bs.get("Current Debt", 0)
            total_debt = long_term_debt + short_term_debt

            # Cash and Equivalents
            cash_equivalents = latest_bs.get("Cash And Cash Equivalents", 0)
            cash_short_term_investments = latest_bs.get("Cash Cash Equivalents And Short Term Investments", 0)
            cash_pool = max(cash_equivalents, cash_short_term_investments)

            # Receivables
            receivables = latest_bs.get("Net Receivables", 0)

            # Interest/Non-permissible Income
            interest_income = 0
            if latest_fin is not None:
                interest_income = latest_fin.get("Interest Income", 0)
                if interest_income == 0:
                    interest_income = latest_fin.get("Non Operating Interest Income", 0)
            total_revenue = latest_fin.get("Total Revenue", 1) if latest_fin is not None else 1

            ratios = {
                "debt_to_assets": total_debt / total_assets,
                "cash_to_assets": cash_pool / total_assets,
                "receivables_to_assets": receivables / total_assets,
                "interest_to_revenue": interest_income / total_revenue
            }
            return ratios
        except Exception as e:
            logger.error(f"Error fetching financial data for {ticker.ticker}: {e}")
            return None

    def _load_cache(self):
        import os
        import json
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading Sharia cache: {e}")
        return {}

    def _save_cache(self):
        import os
        import json
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        try:
            with open(self.cache_path, "w") as f:
                json.dump(self.cache, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving Sharia cache: {e}")

    def screen_stock(self, symbol):
        """
        Full screening logic combining business activity and financial ratios.
        """
        import time

        # 1. Check source from universe first
        matched = self.universe[self.universe["symbol"] == symbol]
        if not matched.empty:
            source = matched.iloc[0]["source"]
            if source == "nifty_shariah":
                # Option 1: Pre-screened by NSE Indices
                logger.debug(f"{symbol} is pre-screened (Nifty Shariah). Automatically compliant.")
                return True, {"source": "Nifty Shariah", "status": "Compliant"}

        # 2. Check local cache
        now = time.time()
        thirty_days = 30 * 24 * 60 * 60
        if symbol in self.cache:
            entry = self.cache[symbol]
            cached_time = entry.get("timestamp", 0)
            if (now - cached_time) < thirty_days:
                logger.debug(f"Using cached Sharia status for {symbol} (Screened {(now - cached_time)/86400:.1f} days ago)")
                return entry["is_compliant"], entry["details"]

        # Option 3: Programmatic screening
        logger.info(f"Running programmatic screen for {symbol}...")
        ticker_symbol = f"{symbol}.NS"
        ticker = yf.Ticker(ticker_symbol)

        try:
            info = ticker.info
            if not info or "sector" not in info:
                logger.warning(f"Could not retrieve info for {symbol}. Stock skipped.")
                res = (False, {"status": "Data Fetch Failed", "reason": "No info or sector found"})
                self.cache[symbol] = {
                    "is_compliant": res[0],
                    "details": res[1],
                    "timestamp": now
                }
                self._save_cache()
                return res
        except Exception as e:
            logger.error(f"Error fetching ticker info for {symbol}: {e}")
            res = (False, {"status": "Data Fetch Failed", "reason": str(e)})
            self.cache[symbol] = {
                "is_compliant": res[0],
                "details": res[1],
                "timestamp": now
            }
            self._save_cache()
            return res

        # 1. Business Screen
        if not self.is_business_compliant(info):
            res = (False, {"reason": f"Non-permissible activities ({info.get('industry', 'unknown')})", "status": "Non-Compliant"})
            self.cache[symbol] = {
                "is_compliant": res[0],
                "details": res[1],
                "timestamp": now
            }
            self._save_cache()
            return res

        # 2. Financial Screen
        ratios = self.get_financial_ratios(ticker)
        if not ratios:
            res = (False, {"reason": "Financial ratios could not be calculated (missing data)", "status": "Non-Compliant"})
            self.cache[symbol] = {
                "is_compliant": res[0],
                "details": res[1],
                "timestamp": now
            }
            self._save_cache()
            return res

        # AAOIFI Compliance Limits
        violations = []
        if ratios["debt_to_assets"] >= 0.33:
            violations.append(f"Debt/Assets ratio ({ratios['debt_to_assets']:.2%}) >= 33%")
        if ratios["cash_to_assets"] >= 0.33:
            violations.append(f"Cash/Assets ratio ({ratios['cash_to_assets']:.2%}) >= 33%")
        if ratios["receivables_to_assets"] >= 0.49:
            violations.append(f"Receivables/Assets ratio ({ratios['receivables_to_assets']:.2%}) >= 49%")
        if ratios["interest_to_revenue"] >= 0.05:
            violations.append(f"Interest/Revenue ratio ({ratios['interest_to_revenue']:.2%}) >= 5%")

        if violations:
            logger.info(f"Rejected {symbol}: Financial ratio violations: {', '.join(violations)}")
            res = (False, {
                "reason": "Financial ratio violations", 
                "violations": violations, 
                "ratios": ratios,
                "status": "Non-Compliant"
            })
        else:
            res = (True, {
                "source": "Programmatic Screen", 
                "ratios": ratios,
                "status": "Compliant"
            })

        # Save to cache
        self.cache[symbol] = {
            "is_compliant": res[0],
            "details": res[1],
            "timestamp": now
        }
        self._save_cache()
        return res
