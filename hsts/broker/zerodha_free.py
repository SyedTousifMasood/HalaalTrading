import requests
import pyotp
import logging
from hsts.broker.base import BaseBroker

logger = logging.getLogger("hsts.broker.zerodha_free")

class ZerodhaFreeBroker(BaseBroker):
    """
    Free Zerodha Kite Broker Adapter (Uses web session enctoken & TOTP 2FA).
    No ₹2,000/month API subscription required.
    """

    def __init__(self, user_id, password, totp_secret, enctoken=None):
        self.user_id = user_id
        self.password = password
        self.totp_secret = totp_secret
        self.enctoken = enctoken
        self.session = requests.Session()
        self.base_url = "https://kite.zerodha.com"

        if enctoken:
            self.session.headers.update({
                "Authorization": f"enctoken {self.enctoken}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

    def authenticate(self):
        """
        Authenticate with Zerodha using credentials and 2FA TOTP secret to generate enctoken.
        """
        try:
            logger.info("Attempting automated Zerodha Web Login...")
            
            # Step 1: Login request
            login_url = f"{self.base_url}/api/login"
            payload = {
                "user_id": self.user_id,
                "password": self.password
            }
            res1 = self.session.post(login_url, data=payload)
            res1_json = res1.json()

            if res1_json.get("status") != "success":
                logger.error(f"Zerodha Login failed: {res1_json.get('message')}")
                return False

            request_id = res1_json["data"]["request_id"]

            # Step 2: Generate TOTP code
            totp = pyotp.TOTP(self.totp_secret)
            totp_code = totp.now()

            # Step 3: 2FA request
            twofa_url = f"{self.base_url}/api/twofa"
            twofa_payload = {
                "user_id": self.user_id,
                "request_id": request_id,
                "twofa_value": totp_code,
                "twofa_type": "totp"
            }
            res2 = self.session.post(twofa_url, data=twofa_payload)
            
            # Step 4: Extract enctoken from cookies
            if "enctoken" in res2.cookies:
                self.enctoken = res2.cookies["enctoken"]
                self.session.headers.update({
                    "Authorization": f"enctoken {self.enctoken}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                logger.info("Zerodha Free Authentication successful! enctoken extracted.")
                return True
            else:
                logger.error("Failed to extract enctoken from response cookies.")
                return False

        except Exception as e:
            logger.error(f"Exception during Zerodha Free authentication: {e}")
            return False

    def get_margins(self):
        """Fetch available margins from Zerodha OMS."""
        url = f"{self.base_url}/oms/user/margins"
        try:
            res = self.session.get(url)
            data = res.json()
            if data.get("status") == "success":
                return data.get("data", {})
            else:
                logger.error(f"Error fetching margins: {data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error fetching margins: {e}")
            return None

    def get_positions(self):
        """Fetch current open positions from Zerodha OMS."""
        url = f"{self.base_url}/oms/portfolio/positions"
        try:
            res = self.session.get(url)
            data = res.json()
            if data.get("status") == "success":
                return data.get("data", {})
            else:
                logger.error(f"Error fetching positions: {data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return None

    def place_order(self, symbol, qty, transaction_type="BUY", order_type="LIMIT", price=0.0, trigger_price=0.0):
        """
        Place an order via Zerodha OMS endpoints.
        """
        url = f"{self.base_url}/oms/orders/regular"
        payload = {
            "tradingsymbol": symbol,
            "exchange": "NSE",
            "transaction_type": transaction_type.upper(),
            "order_type": order_type.upper(),
            "quantity": qty,
            "product": "CNC",  # Delivery product for swing trading
            "validity": "DAY",
            "price": price,
            "trigger_price": trigger_price,
            "disclosed_quantity": 0
        }
        try:
            res = self.session.post(url, data=payload)
            data = res.json()
            if data.get("status") == "success":
                order_id = data["data"]["order_id"]
                logger.info(f"Order placed successfully! Order ID: {order_id}")
                return {"order_id": order_id, "status": "COMPLETE"}
            else:
                logger.error(f"Order placement failed: {data.get('message')}")
                return {"status": "FAILED", "reason": data.get("message")}
        except Exception as e:
            logger.error(f"Exception while placing order: {e}")
            return {"status": "FAILED", "reason": str(e)}

    def cancel_order(self, order_id):
        """Cancel an open order by Order ID."""
        url = f"{self.base_url}/oms/orders/regular/{order_id}"
        try:
            res = self.session.delete(url)
            data = res.json()
            if data.get("status") == "success":
                logger.info(f"Order {order_id} cancelled successfully.")
                return True
            else:
                logger.error(f"Order cancellation failed: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Exception while cancelling order: {e}")
            return False
