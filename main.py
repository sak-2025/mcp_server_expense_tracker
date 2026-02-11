from fastmcp import FastMCP
import os 
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- Configuration & Logging ---
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "expenses.db"))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ExpenseTracker")

mcp = FastMCP("ExpenseTracker")


# --- Data Models  -data Validation  ---
class ExpenseEntry(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO format YYYY-MM-DD")
    amount: float = Field(..., gt=0, description="Transaction amount ")
    category: str = Field(..., min_length=4)
    subcategory: Optional[str] = ""
    remark: Optional[str] = ""


# --- Database Orchestration ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn


def init_db():
    """Create expenses table and  performance indexing."""
    with get_db_connection() as conn:
     conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                remark TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    # Index for analytical query performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON expenses(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON expenses(date)")
    logger.info("Database initialized with performance indices.")

init_db()


@mcp.tool()
def add_expense(data: ExpenseEntry) -> Dict[str, Any]:
    """
    Add a new expense entry. 
    Date should be in YYYY-MM-DD format.
    """
    try:
        with get_db_connection() as c:
         cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, remark) VALUES (?,?,?,?,?)",
            (data.date, data.amount, data.category, data.subcategory, data.remark)
        )
        return {"status": "success", "id": cur.lastrowid , "message": "Transaction committed."}
    except sqlite3.Error as e:
       logger.error(f"Database integrity error: {e}")
       return {"status": "error", "message": str(e)}


@mcp.tool()
def list_expenses_by_range(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Retrieves expenses between two dates (inclusive).
    Dates must be in YYYY-MM-DD format.
    """
    try:
        with get_db_connection() as c:
            c.row_factory = sqlite3.Row
            # We use a multi-line string (triple quotes) for SQL readability
            query = """
                SELECT id, date, amount, category, subcategory, remark 
                FROM expenses 
                WHERE date BETWEEN ? AND ? 
                ORDER BY date DESC
            """
            cur = c.execute(query, (start_date, end_date))
            rows = cur.fetchall()
            
            # Returns an empty list if no results, or the list of dicts
            return [dict(row) for row in rows]
            
    except sqlite3.Error as e:
        logger.error(f"Data retrieval error: {e}")
        return {"status": "error", "message": "Failed to retrieve records from database."}
    



@mcp.tool()
def get_expenses_by_category(category: str):
    """Filter expenses by a specific category."""
    try:
        with get_db_connection() as c:
            cur = c.execute("SELECT * FROM expenses WHERE category = ? ", (category,))
            return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Data retrieval error: {e}")
        return {"status": "error", "message": "Failed to retrieve records from database."}

   


@mcp.tool()
def get_total_spending():
    """Calculate the total spending across all categories."""
    try:
        with get_db_connection() as c:
         c.row_factory = sqlite3.Row
         cur = c.execute("SELECT SUM(amount) as total FROM expenses")
         result = cur.fetchone()
         return {"total_spending": result[0] if result[0] else 0}
    except sqlite3.Error as e:
        logger.error(f"Data retrieval error: {e}")
        return {"status": "error", "message": "Failed to retrieve total spending from database."}




@mcp.tool()
def summarize(startdate ,enddate ,category=None):
    ''' Summarize all spendng with or without category '''
    try:
      with get_db_connection() as c:
            query = """
                SELECT id, date, amount, category, subcategory, remark 
                FROM expenses 
                WHERE date BETWEEN ? AND ?  
                """ 
            params = [startdate,enddate]
            
            if category:
                query += "category = ? "
                params = params.append(category)

            query += "group by category order by category asc "

            cur =c.execute(query,params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols,r)) for r in cur.fetchall()]
    except sqlite3.Error as e:
       logger.error(f"Data retrieval error: {e}")
       return {"status": "error", "message": "Failed to retrieve summarized data from database."}



if __name__ == "__main__":
    mcp.run()

