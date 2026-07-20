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

    def initialize_journal(self):
        """
        Creates and formats the Excel Workbook if it does not exist.
        """
        if os.path.exists(self.file_path):
            logger.info("Trading Journal already exists. Initialized successfully.")
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

        # 3. Setup Logs Sheet
        ws_logs = wb.create_sheet(title="Logs")
        self._setup_logs(ws_logs)

        wb.save(self.file_path)
        logger.info("Workbook created and formatted successfully.")

    def _setup_dashboard(self, ws):
        # Disable Gridlines setting
        ws.views.sheetView[0].showGridLines = True

        # Styles
        font_title = Font(name="Segoe UI", size=16, bold=True, color="1B365D")
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        font_bold = Font(name="Segoe UI", size=11, bold=True)
        font_regular = Font(name="Segoe UI", size=11)
        fill_header = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
        fill_metric = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")

        # Title block
        ws["A1"] = "HSTS v1.0 Trading Dashboard"
        ws["A1"].font = font_title
        ws.row_dimensions[1].height = 30

        # Stats Table Headers
        headers = ["Metric", "Value"]
        for col_idx, text in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[3].height = 24

        # Metrics rows
        metrics = [
            ("Lifetime PnL", "=SUM(Ledger!L:L)"),
            ("Win Rate", '=IF((COUNTIF(Ledger!K:K, "WIN")+COUNTIF(Ledger!K:K, "LOSS"))>0, COUNTIF(Ledger!K:K, "WIN")/(COUNTIF(Ledger!K:K, "WIN")+COUNTIF(Ledger!K:K, "LOSS")), 0)'),
            ("Total Completed Trades", '=COUNTIF(Ledger!K:K, "WIN") + COUNTIF(Ledger!K:K, "LOSS")'),
            ("Active Open Positions", '=COUNTIF(Ledger!K:K, "OPEN")'),
            ("Win Trades", '=COUNTIF(Ledger!K:K, "WIN")'),
            ("Loss Trades", '=COUNTIF(Ledger!K:K, "LOSS")'),
        ]

        for i, (metric_name, formula) in enumerate(metrics, 4):
            cell_name = ws.cell(row=i, column=1, value=metric_name)
            cell_name.font = font_bold
            cell_name.fill = fill_metric
            
            cell_val = ws.cell(row=i, column=2, value=formula)
            cell_val.font = font_regular
            if metric_name == "Win Rate":
                cell_val.number_format = "0.0%"
            elif metric_name == "Lifetime PnL":
                cell_val.number_format = "INR #,##0.00"

        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 20

    def _setup_ledger(self, ws):
        ws.views.sheetView[0].showGridLines = True
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")

        headers = [
            "Symbol", "Name", "Entry Date", "Qty", "Buy Price", 
            "Suggested Entry", "Slippage/Deviation", "Target Price", 
            "Stop Loss", "Exit Date", "Exit Price", "Realized PnL", 
            "Status", "Notes"
        ]

        for col_idx, text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        ws.row_dimensions[1].height = 28

        # Set default widths
        for col_idx in range(1, len(headers) + 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = 16
        ws.column_dimensions["B"].width = 25  # Name column
        ws.column_dimensions["N"].width = 30  # Notes column

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

    def add_trade(self, symbol, name, entry_date, qty, buy_price, suggested_entry, target, stop_loss, notes=""):
        """
        Record a new open trade to the ledger.
        """
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb["Ledger"]
        
        row_idx = ws.max_row + 1
        
        # Calculate initial slippage/deviation
        slippage = buy_price - suggested_entry

        ws.cell(row=row_idx, column=1, value=symbol)
        ws.cell(row=row_idx, column=2, value=name)
        ws.cell(row=row_idx, column=3, value=entry_date)
        ws.cell(row=row_idx, column=4, value=qty)
        ws.cell(row=row_idx, column=5, value=buy_price)
        ws.cell(row=row_idx, column=6, value=suggested_entry)
        ws.cell(row=row_idx, column=7, value=slippage)
        ws.cell(row=row_idx, column=8, value=target)
        ws.cell(row=row_idx, column=9, value=stop_loss)
        
        # Exit fields (Blank initially)
        ws.cell(row=row_idx, column=10, value="")
        ws.cell(row=row_idx, column=11, value="")
        
        # PnL Formula: =IF(K{row_idx}="WIN", (K{row_idx}-E{row_idx})*D{row_idx}, IF(K{row_idx}="LOSS", (K{row_idx}-E{row_idx})*D{row_idx}, 0))
        # Better: =IF(K{row_idx}="OPEN", 0, (K{row_idx}-E{row_idx})*D{row_idx})
        # Exit price is Col K (11), Buy Price is Col E (5), Qty is Col D (4)
        pnl_formula = f'=IF(M{row_idx}="OPEN", 0, (K{row_idx}-E{row_idx})*D{row_idx})'
        ws.cell(row=row_idx, column=12, value=pnl_formula)
        
        # Status (Col M)
        ws.cell(row=row_idx, column=13, value="OPEN")
        ws.cell(row=row_idx, column=14, value=notes)

        # Formats
        ws.cell(row=row_idx, column=5).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=6).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=7).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=8).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=9).number_format = "INR #,##0.00"
        ws.cell(row=row_idx, column=12).number_format = "INR #,##0.00"

        wb.save(self.file_path)
        logger.info(f"Recorded open trade for {symbol} to Ledger (Row {row_idx})")
        self.log_event(f"Recorded buy order: {qty} shares of {symbol} at {buy_price}")

    def close_trade(self, symbol, exit_date, exit_price, status, notes=""):
        """
        Close an existing open trade for a symbol in the Ledger.
        """
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb["Ledger"]
        
        # Find open trade
        found = False
        for r in range(2, ws.max_row + 1):
            if ws.cell(row=r, column=1).value == symbol and ws.cell(row=r, column=13).value == "OPEN":
                ws.cell(row=r, column=10, value=exit_date)
                ws.cell(row=r, column=11, value=exit_price)
                ws.cell(row=r, column=13, value=status.upper())  # WIN or LOSS
                if notes:
                    ws.cell(row=r, column=14, value=f"{ws.cell(row=r, column=14).value} | {notes}".strip(" |"))
                
                # Format exit price
                ws.cell(row=r, column=11).number_format = "INR #,##0.00"
                found = True
                logger.info(f"Closed trade for {symbol} at Row {r} with status {status}")
                break

        if not found:
            logger.error(f"No active open trade found for symbol {symbol}")
            wb.close()
            return False

        wb.save(self.file_path)
        self.log_event(f"Closed trade: {symbol} exited at {exit_price} ({status})")
        return True

    def log_event(self, message, level="INFO"):
        """
        Append system events to the Logs sheet.
        """
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb["Logs"]
        row_idx = ws.max_row + 1
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.cell(row=row_idx, column=1, value=timestamp)
        ws.cell(row=row_idx, column=2, value=level.upper())
        ws.cell(row=row_idx, column=3, value=message)
        
        wb.save(self.file_path)
