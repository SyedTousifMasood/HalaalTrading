import os
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import datetime
import logging

logger = logging.getLogger("hsts.journal")

class TradingJournal:
    def __init__(self, file_path="G:/My Drive/HalaalTrading/Trading_Journal.xlsx"):
        self.file_path = file_path
        self.initialize_journal()

    def _get_true_max_row(self, ws):
        """Find the actual last populated row in Column A to prevent writing 1000 rows down."""
        for r in range(ws.max_row, 0, -1):
            val = ws.cell(row=r, column=1).value
            if val is not None and str(val).strip() != "":
                return r
        return 1

    def initialize_journal(self):
        """
        Creates, formats, or updates the Excel Workbook.
        """
        if os.path.exists(self.file_path):
            logger.info("Trading Journal already exists. Checking for updates/missing sheets...")
            wb = openpyxl.load_workbook(self.file_path)
            
            # Upgrade check: Add Capital sheet if missing
            if "Capital" not in wb.sheetnames:
                logger.info("Upgrading Trading Journal: Adding Capital sheet...")
                ws_cap = wb.create_sheet(title="Capital")
                self._setup_capital(ws_cap)

            # Upgrade check: Add Recommendations sheet if missing
            if "Recommendations" not in wb.sheetnames:
                logger.info("Upgrading Trading Journal: Adding Recommendations sheet...")
                ws_recs = wb.create_sheet(title="Recommendations")
                self._setup_recommendations(ws_recs)

            ws_dash = wb["Dashboard"]
            self._setup_dashboard(ws_dash)

            wb.save(self.file_path)
            wb.close()
            self._upgrade_rr_ratio_columns()
            return

        logger.info(f"Creating a new Trading Journal at {self.file_path}...")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        wb = openpyxl.Workbook()
        
        # 1. Setup Dashboard Sheet
        ws_dash = wb.active
        ws_dash.title = "Dashboard"
        self._setup_dashboard(ws_dash)

        # 2. Setup Ledger Sheet
        ws_ledg = wb.create_sheet(title="Ledger")
        self._setup_ledger(ws_ledg)

        # 3. Setup Recommendations Sheet
        ws_recs = wb.create_sheet(title="Recommendations")
        self._setup_recommendations(ws_recs)

        # 4. Setup Capital Sheet
        ws_cap = wb.create_sheet(title="Capital")
        self._setup_capital(ws_cap)

        # 5. Setup Logs Sheet
        ws_logs = wb.create_sheet(title="Logs")
        self._setup_logs(ws_logs)

        wb.save(self.file_path)
        logger.info("Workbook created and formatted successfully.")

    def _upgrade_rr_ratio_columns(self):
        wb = openpyxl.load_workbook(self.file_path)
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        fill_header_recs = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
        fill_header_ledg = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")

        # 1. Recommendations Sheet Upgrade
        if "Recommendations" in wb.sheetnames:
            ws = wb["Recommendations"]
            if ws.cell(row=1, column=8).value != "Risk-to-Reward Ratio":
                logger.info("Upgrading Recommendations sheet: Adding Risk-to-Reward Ratio column...")
                ws.insert_cols(8)
                cell = ws.cell(row=1, column=8, value="Risk-to-Reward Ratio")
                cell.font = font_header
                cell.fill = fill_header_recs
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.column_dimensions["H"].width = 22

                true_max = self._get_true_max_row(ws)
                for r in range(2, true_max + 1):
                    entry = ws.cell(row=r, column=5).value
                    sl = ws.cell(row=r, column=6).value
                    target = ws.cell(row=r, column=7).value
                    
                    if isinstance(entry, (int, float)) and isinstance(sl, (int, float)) and isinstance(target, (int, float)):
                        risk = entry - sl
                        reward = target - entry
                        rr_val = (reward / risk) if risk > 0 else 2.0
                        ws.cell(row=r, column=8, value=f"1:{rr_val:.1f}")
                    else:
                        ws.cell(row=r, column=8, value="1:2.0")

        # 2. Ledger Sheet Upgrade
        if "Ledger" in wb.sheetnames:
            ws = wb["Ledger"]
            if ws.cell(row=1, column=10).value != "Risk-to-Reward Ratio":
                logger.info("Upgrading Ledger sheet: Adding Risk-to-Reward Ratio column...")
                ws.insert_cols(10)
                cell = ws.cell(row=1, column=10, value="Risk-to-Reward Ratio")
                cell.font = font_header
                cell.fill = fill_header_ledg
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.column_dimensions["J"].width = 22

                true_max = self._get_true_max_row(ws)
                for r in range(2, true_max + 1):
                    buy_price = ws.cell(row=r, column=5).value
                    target = ws.cell(row=r, column=8).value
                    sl = ws.cell(row=r, column=9).value
                    
                    if isinstance(buy_price, (int, float)) and isinstance(sl, (int, float)) and isinstance(target, (int, float)):
                        risk = buy_price - sl
                        reward = target - buy_price
                        rr_val = (reward / risk) if risk > 0 else 2.0
                        ws.cell(row=r, column=10, value=f"1:{rr_val:.1f}")
                    else:
                        ws.cell(row=r, column=10, value="1:2.0")
                    
                    pnl_formula = f'=IF(N{r}="OPEN", 0, (L{r}-E{r})*D{r})'
                    ws.cell(row=r, column=13, value=pnl_formula)

        ws_dash = wb["Dashboard"]
        self._setup_dashboard(ws_dash)

        wb.save(self.file_path)

    def _setup_dashboard(self, ws):
        ws.views.sheetView[0].showGridLines = True
        font_title = Font(name="Segoe UI", size=16, bold=True, color="1B365D")
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        font_bold = Font(name="Segoe UI", size=11, bold=True)
        font_regular = Font(name="Segoe UI", size=11)
        fill_header = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
        fill_metric = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")

        ws["A1"] = "HSTS v1.0 Trading Dashboard"
        ws["A1"].font = font_title
        ws.row_dimensions[1].height = 30

        headers = ["Metric", "Value"]
        for col_idx, text in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[3].height = 24

        metrics = [
            ("Total Net Capital Deposited", '=SUMIF(Capital!B:B, "DEPOSIT", Capital!C:C) - SUMIF(Capital!B:B, "WITHDRAWAL", Capital!C:C)'),
            ("Lifetime Realized PnL", "=SUM(Ledger!M:M)"),
            ("Current Total Portfolio Value", "=B4 + B5"),
            ("Capital Deployed in Open Trades", '=SUMPRODUCT((Ledger!N2:N500="OPEN")*(Ledger!E2:E500)*(Ledger!D2:D500))'),
            ("Capital Available for Trading", "=B6 - B7"),
            ("Win Rate", '=IF((COUNTIF(Ledger!N:N, "WIN")+COUNTIF(Ledger!N:N, "LOSS"))>0, COUNTIF(Ledger!N:N, "WIN")/(COUNTIF(Ledger!N:N, "WIN")+COUNTIF(Ledger!N:N, "LOSS")), 0)'),
            ("Total Completed Trades", '=COUNTIF(Ledger!N:N, "WIN") + COUNTIF(Ledger!N:N, "LOSS")'),
            ("Active Open Positions", '=COUNTIF(Ledger!N:N, "OPEN")'),
            ("Win Trades", '=COUNTIF(Ledger!N:N, "WIN")'),
            ("Loss Trades", '=COUNTIF(Ledger!N:N, "LOSS")'),
        ]

        for i, (metric_name, formula) in enumerate(metrics, 4):
            cell_name = ws.cell(row=i, column=1, value=metric_name)
            cell_name.font = font_bold
            cell_name.fill = fill_metric
            
            cell_val = ws.cell(row=i, column=2, value=formula)
            cell_val.font = font_regular
            if metric_name == "Win Rate":
                cell_val.number_format = "0.0%"
            elif metric_name in ["Total Net Capital Deposited", "Lifetime Realized PnL", "Current Total Portfolio Value", "Capital Deployed in Open Trades", "Capital Available for Trading"]:
                cell_val.number_format = "INR #,##0.00"

        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 22

    def _setup_ledger(self, ws):
        ws.views.sheetView[0].showGridLines = True
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")

        headers = [
            "Symbol", "Name", "Entry Date", "Qty", "Buy Price", 
            "Suggested Entry", "Slippage/Deviation", "Target Price", 
            "Stop Loss", "Risk-to-Reward Ratio", "Exit Date", "Exit Price", 
            "Realized PnL", "Status", "Notes"
        ]

        for col_idx, text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        ws.row_dimensions[1].height = 28

        for col_idx in range(1, len(headers) + 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = 16
        ws.column_dimensions["B"].width = 25
        ws.column_dimensions["J"].width = 22
        ws.column_dimensions["O"].width = 30

    def _setup_recommendations(self, ws):
        ws.views.sheetView[0].showGridLines = True
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")

        headers = [
            "Date", "Symbol", "Name", "Composite Score", 
            "Target Entry Price", "Initial Stop-Loss", "Profit Target", 
            "Risk-to-Reward Ratio", "Recommended Qty", "Recommended Allocation", 
            "Execution Status", "Notes"
        ]

        for col_idx, text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.row_dimensions[1].height = 28

        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 14
        ws.column_dimensions["C"].width = 25
        ws.column_dimensions["D"].width = 18
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 18
        ws.column_dimensions["G"].width = 18
        ws.column_dimensions["H"].width = 22
        ws.column_dimensions["I"].width = 18
        ws.column_dimensions["J"].width = 22
        ws.column_dimensions["K"].width = 24
        ws.column_dimensions["L"].width = 30

    def get_available_capital(self, default_capital=100000.0):
        """Calculates Capital Available for Trading dynamically from the Journal."""
        if not os.path.exists(self.file_path):
            return default_capital
        try:
            wb = openpyxl.load_workbook(self.file_path, data_only=True)
            ws_cap = wb["Capital"]
            deposits = 0.0
            for r in range(2, self._get_true_max_row(ws_cap) + 1):
                t_type = str(ws_cap.cell(row=r, column=2).value or "").strip().upper()
                amt = float(ws_cap.cell(row=r, column=3).value or 0.0)
                if t_type == "DEPOSIT":
                    deposits += amt
                elif t_type == "WITHDRAWAL":
                    deposits -= amt
            if deposits <= 0.0:
                deposits = default_capital

            ws_ledg = wb["Ledger"]
            deployed = 0.0
            realized_pnl = 0.0
            for r in range(2, self._get_true_max_row(ws_ledg) + 1):
                status = str(ws_ledg.cell(row=r, column=14).value or "").strip().upper()
                qty = float(ws_ledg.cell(row=r, column=4).value or 0.0)
                price = float(ws_ledg.cell(row=r, column=5).value or 0.0)
                
                # Column 13 is Realized PnL (Formula or float)
                pnl_val = ws_ledg.cell(row=r, column=13).value
                if isinstance(pnl_val, (int, float)):
                    pnl = float(pnl_val)
                else:
                    # Calculate manually if formula string
                    exit_p = float(ws_ledg.cell(row=r, column=12).value or price)
                    pnl = (exit_p - price) * qty

                if status == "OPEN":
                    deployed += (qty * price)
                elif status in ["CLOSED", "WIN", "LOSS"]:
                    realized_pnl += pnl

            wb.close()
            avail = deposits + realized_pnl - deployed
            return avail if avail > 0 else default_capital
        except Exception as e:
            logger.error(f"Error reading available capital from journal: {e}")
            return default_capital

    def _setup_capital(self, ws):
        ws.views.sheetView[0].showGridLines = True
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")

        headers = ["Date", "Type", "Amount", "Notes"]
        for col_idx, text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 18
        ws.column_dimensions["D"].width = 40

    def _setup_logs(self, ws):
        ws.views.sheetView[0].showGridLines = True
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="4A5568", end_color="4A5568", fill_type="solid")

        headers = ["Timestamp", "Level", "Message"]
        for col_idx, text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 12
        ws.column_dimensions["C"].width = 80

    def add_recommendation(self, symbol, name, score, target_entry, stop_loss, profit_target, qty, allocation, status="PENDING", notes=""):
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb["Recommendations"]
        row_idx = self._get_true_max_row(ws) + 1
        
        date_str = datetime.date.today().strftime("%Y-%m-%d")

        risk = target_entry - stop_loss
        reward = profit_target - target_entry
        rr_val = (reward / risk) if risk > 0 else 2.0
        rr_ratio_str = f"1:{rr_val:.1f}"

        ws.cell(row=row_idx, column=1, value=date_str)
        ws.cell(row=row_idx, column=2, value=symbol)
        ws.cell(row=row_idx, column=3, value=name)
        ws.cell(row=row_idx, column=4, value=f"{score:.0f}/100")
        ws.cell(row=row_idx, column=5, value=target_entry)
        ws.cell(row=row_idx, column=6, value=stop_loss)
        ws.cell(row=row_idx, column=7, value=profit_target)
        ws.cell(row=row_idx, column=8, value=rr_ratio_str)
        ws.cell(row=row_idx, column=9, value=qty)
        ws.cell(row=row_idx, column=10, value=allocation)
        ws.cell(row=row_idx, column=11, value=status)
        ws.cell(row=row_idx, column=12, value=notes)

        ws.cell(row=row_idx, column=5).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=6).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=7).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=10).number_format = "INR #,##0.00"

        wb.save(self.file_path)
        logger.info(f"Logged recommendation for {symbol} to Recommendations sheet (Row {row_idx})")

    def capital_transaction_exists(self, notes):
        """Checks if a capital transaction with the exact notes already exists to prevent duplicate charges."""
        if not os.path.exists(self.file_path):
            return False
        try:
            wb = openpyxl.load_workbook(self.file_path, data_only=True)
            ws = wb["Capital"]
            for r in range(2, self._get_true_max_row(ws) + 1):
                val = ws.cell(row=r, column=4).value
                if val == notes:
                    wb.close()
                    return True
            wb.close()
            return False
        except Exception as e:
            logger.error(f"Error checking capital transaction existence: {e}")
            return False

    def add_capital_transaction(self, transaction_type, amount, notes=""):
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb["Capital"]
        row_idx = self._get_true_max_row(ws) + 1
        
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        ws.cell(row=row_idx, column=1, value=date_str)
        ws.cell(row=row_idx, column=2, value=transaction_type.upper())
        ws.cell(row=row_idx, column=3, value=amount)
        ws.cell(row=row_idx, column=4, value=notes)

        ws.cell(row=row_idx, column=3).number_format = "INR #,##0.00"
        
        wb.save(self.file_path)
        logger.info(f"Capital Transaction: {transaction_type.upper()} of INR {amount:.2f} logged.")
        self.log_event(f"Capital Transaction: {transaction_type.upper()} of INR {amount:.2f} logged.")

    def add_trade(self, symbol, name, entry_date, qty, buy_price, suggested_entry, target, stop_loss, notes=""):
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb["Ledger"]
        row_idx = self._get_true_max_row(ws) + 1
        
        # Prevent duplicate entries for same symbol/date
        for r in range(2, row_idx):
            if ws.cell(row=r, column=1).value == symbol and ws.cell(row=r, column=3).value == entry_date and ws.cell(row=r, column=14).value == "OPEN":
                logger.info(f"Trade for {symbol} on {entry_date} already exists at Row {r}. Skipping duplicate.")
                wb.close()
                return

        slippage = buy_price - suggested_entry
        risk = buy_price - stop_loss
        reward = target - buy_price
        rr_val = (reward / risk) if risk > 0 else 2.0
        rr_ratio_str = f"1:{rr_val:.1f}"

        ws.cell(row=row_idx, column=1, value=symbol)
        ws.cell(row=row_idx, column=2, value=name)
        ws.cell(row=row_idx, column=3, value=entry_date)
        ws.cell(row=row_idx, column=4, value=qty)
        ws.cell(row=row_idx, column=5, value=buy_price)
        ws.cell(row=row_idx, column=6, value=suggested_entry)
        ws.cell(row=row_idx, column=7, value=slippage)
        ws.cell(row=row_idx, column=8, value=target)
        ws.cell(row=row_idx, column=9, value=stop_loss)
        ws.cell(row=row_idx, column=10, value=rr_ratio_str)
        
        ws.cell(row=row_idx, column=11, value="")
        ws.cell(row=row_idx, column=12, value="")
        pnl_formula = f'=IF(N{row_idx}="OPEN", 0, (L{row_idx}-E{row_idx})*D{row_idx})'
        ws.cell(row=row_idx, column=13, value=pnl_formula)
        ws.cell(row=row_idx, column=14, value="OPEN")
        ws.cell(row=row_idx, column=15, value=notes)

        ws.cell(row=row_idx, column=5).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=6).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=7).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=8).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=9).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=13).number_format = "INR #,##0.00"

        wb.save(self.file_path)
        logger.info(f"Recorded open trade for {symbol} to Ledger (Row {row_idx})")
        self.log_event(f"Recorded buy order: {qty} shares of {symbol} at {buy_price}")

    def close_trade(self, symbol, exit_date, exit_price, status, notes=""):
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb["Ledger"]
        found = False
        true_max = self._get_true_max_row(ws)
        for r in range(2, true_max + 1):
            if ws.cell(row=r, column=1).value == symbol and ws.cell(row=r, column=14).value == "OPEN":
                ws.cell(row=r, column=11, value=exit_date)
                ws.cell(row=r, column=12, value=exit_price)
                ws.cell(row=r, column=14, value=status.upper())
                if notes:
                    ws.cell(row=r, column=15, value=f"{ws.cell(row=r, column=15).value} | {notes}".strip(" |"))
                ws.cell(row=r, column=12).number_format = "INR #,##0.00"
                found = True
                break

        if not found:
            logger.error(f"No active open trade found for symbol {symbol}")
            wb.close()
            return False

        wb.save(self.file_path)
        self.log_event(f"Closed trade: {symbol} exited at {exit_price} ({status})")
        return True

    def log_event(self, message, level="INFO"):
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb["Logs"]
        row_idx = self._get_true_max_row(ws) + 1
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.cell(row=row_idx, column=1, value=timestamp)
        ws.cell(row=row_idx, column=2, value=level.upper())
        ws.cell(row=row_idx, column=3, value=message)
        wb.save(self.file_path)
