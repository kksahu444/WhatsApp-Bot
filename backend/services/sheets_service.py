"""
Google Sheets Service for Order Logging.

Logs orders to a shared Google Sheet for business tracking.
Uses service account authentication via JSON file.
"""

import os
from datetime import datetime
from typing import Dict, Optional
from loguru import logger

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.warning("⚠️ gspread not installed, Google Sheets logging disabled")


class GoogleSheetsService:
    """
    Google Sheets integration for order logging.
    
    Uses service account authentication.
    Credentials file: /app/service_account.json (Docker) or ./service_account.json (local)
    """
    
    # Google Sheets API scopes
    SCOPES = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Default sheet configuration
    SPREADSHEET_NAME = "SmartShop_Data"
    WORKSHEET_NAME = "Orders"
    
    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.spreadsheet = None
        self.worksheet = None
        self._initialized = False
        
        # Credential file paths (try Docker path first, then local)
        self.credential_paths = [
            "/app/service_account.json",      # Docker container path
            "./service_account.json",          # Local development
            os.path.expanduser("~/service_account.json"),  # Home directory
        ]
    
    def _get_credentials_path(self) -> Optional[str]:
        """Find the service account JSON file."""
        for path in self.credential_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _initialize(self) -> bool:
        """
        Initialize Google Sheets client.
        
        Returns:
            bool: True if initialization successful
        """
        if self._initialized and self.client:
            return True
        
        if not GSPREAD_AVAILABLE:
            logger.warning("⚠️ gspread library not available")
            return False
        
        try:
            # Find credentials file
            creds_path = self._get_credentials_path()
            if not creds_path:
                logger.warning("⚠️ service_account.json not found, Sheets logging disabled")
                return False
            
            logger.info(f"📊 Loading Google credentials from: {creds_path}")
            
            # Authenticate
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                creds_path, 
                self.SCOPES
            )
            self.client = gspread.authorize(credentials)
            
            # Open spreadsheet and worksheet
            self.spreadsheet = self.client.open(self.SPREADSHEET_NAME)
            self.worksheet = self.spreadsheet.worksheet(self.WORKSHEET_NAME)
            
            self._initialized = True
            logger.info(f"✅ Google Sheets connected: {self.SPREADSHEET_NAME}/{self.WORKSHEET_NAME}")
            return True
            
        except gspread.SpreadsheetNotFound:
            logger.error(f"❌ Spreadsheet '{self.SPREADSHEET_NAME}' not found. "
                        f"Create it and share with service account email.")
            return False
        except gspread.WorksheetNotFound:
            logger.error(f"❌ Worksheet '{self.WORKSHEET_NAME}' not found. "
                        f"Create a sheet named '{self.WORKSHEET_NAME}'.")
            return False
        except Exception as e:
            logger.error(f"❌ Google Sheets initialization failed: {e}")
            return False
    
    def log_order(self, order_data: Dict) -> bool:
        """
        Log an order to Google Sheets.
        
        CRITICAL: This method swallows all exceptions to prevent
        crashing the main application. Errors are logged only.
        
        Args:
            order_data: Dict with order details
                - order_id: str
                - user_phone: str
                - user_name: str (optional)
                - items: list or str
                - total_amount: float
                - status: str
                - created_at: str (optional)
        
        Returns:
            bool: True if logged successfully
        """
        try:
            # Initialize if needed
            if not self._initialize():
                logger.warning("⚠️ Sheets not initialized, skipping order log")
                return False
            
            # Extract order data
            order_id = order_data.get('order_id', 'N/A')
            user_phone = order_data.get('user_phone', 'N/A')
            user_name = order_data.get('user_name', 'N/A')
            
            # Format items
            items = order_data.get('items', [])
            if isinstance(items, list):
                items_str = ', '.join([
                    f"{item.get('product_name', 'Unknown')} x{item.get('quantity', 1)}"
                    for item in items
                ])
            else:
                items_str = str(items)
            
            total_amount = order_data.get('total_amount', 0)
            status = order_data.get('status', 'PENDING')
            
            # Timestamps
            created_at = order_data.get('created_at', '')
            if created_at:
                # Parse if it's a datetime string
                try:
                    if isinstance(created_at, str):
                        order_date = created_at[:10]  # YYYY-MM-DD
                    else:
                        order_date = created_at.strftime('%Y-%m-%d')
                except:
                    order_date = datetime.now().strftime('%Y-%m-%d')
            else:
                order_date = datetime.now().strftime('%Y-%m-%d')
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Row to append
            row = [
                order_id,
                order_date,
                user_phone,
                user_name,
                items_str,
                f"₹{total_amount:,.2f}",
                status,
                timestamp
            ]
            
            # Append to sheet
            self.worksheet.append_row(row, value_input_option='USER_ENTERED')
            
            logger.info(f"📊 Order logged to Sheets: {order_id}")
            return True
            
        except gspread.exceptions.APIError as e:
            logger.error(f"❌ Google Sheets API error: {e}")
            return False
        except Exception as e:
            # CRITICAL: Swallow all exceptions - don't crash main app
            logger.error(f"❌ Failed to log order to Sheets: {e}")
            return False
    
    def update_order_status(self, order_id: str, new_status: str) -> bool:
        """
        Update order status in Google Sheets.
        
        Args:
            order_id: Order ID to update
            new_status: New status value
            
        Returns:
            bool: True if updated successfully
        """
        try:
            if not self._initialize():
                return False
            
            # Find the row with this order ID
            cell = self.worksheet.find(order_id)
            if cell:
                # Status is in column 7 (G)
                self.worksheet.update_cell(cell.row, 7, new_status)
                # Update timestamp in column 8 (H)
                self.worksheet.update_cell(
                    cell.row, 8, 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                logger.info(f"📊 Order status updated in Sheets: {order_id} -> {new_status}")
                return True
            else:
                logger.warning(f"⚠️ Order {order_id} not found in Sheets")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update order in Sheets: {e}")
            return False
    
    def ensure_headers(self) -> bool:
        """
        Ensure the worksheet has proper headers.
        Call this once during setup.
        """
        try:
            if not self._initialize():
                return False
            
            headers = [
                'Order ID',
                'Date',
                'Phone',
                'Customer Name',
                'Items',
                'Amount',
                'Status',
                'Last Updated'
            ]
            
            # Check if first row is empty or doesn't have headers
            first_row = self.worksheet.row_values(1)
            if not first_row or first_row[0] != 'Order ID':
                self.worksheet.insert_row(headers, 1)
                logger.info("📊 Headers added to Google Sheet")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add headers: {e}")
            return False


# Singleton instance
_sheets_service: Optional[GoogleSheetsService] = None


def get_sheets_service() -> GoogleSheetsService:
    """Get or create Google Sheets service singleton."""
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = GoogleSheetsService()
    return _sheets_service
