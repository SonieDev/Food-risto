'''
from fastapi import FastAPI
from repository_pg import OrderRepository
from models import Order
from pydantic import BaseModel
from typing import List

app = FastAPI()

repo = OrderRepository()
@app.get("/")
def home():
    return {"message": "Backend Ristorante attivo"}


# 🔥 NUOVA API
@app.get("/orders")
def get_orders():
    return repo.get_all_orders()

#API Endpoint ordine dettagliato
@app.get("/orders/{order_id}")
def order_details(order_id: int):
    repo = OrderRepository()
    return repo.get_order_details(order_id)


class OrderCreate(BaseModel):
    table_number: int
    total: float

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    table_number: int
    items: List[OrderItemCreate]


@app.post("/orders")
def create_order(order: OrderCreate):
    repo = OrderRepository()

    # creare ordine base
    class SimpleOrder:
        def __init__(self, table_number):
            self.table_number = table_number
            self.items = []

        def total(self):
            return sum(item["price"] for item in self.items)

    conn = get_connection()
    cursor = conn.cursor()

    # 1️⃣ Insert order
    cursor.execute("""
        INSERT INTO orders (table_number, total, date)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        RETURNING id
    """, (order.table_number, 0))

    order_id = cursor.fetchone()[0]

    total = 0

    # 2️⃣ Insert items
    for item in order.items:

        cursor.execute("""
            SELECT price FROM products WHERE id=%s
        """, (item.product_id,))

        price = cursor.fetchone()[0]

        subtotal = price * item.quantity
        total += subtotal

        cursor.execute("""
            INSERT INTO order_items
            (order_id, product_id, quantity, price)
            VALUES (%s,%s,%s,%s)
        """, (
            order_id,
            item.product_id,
            item.quantity,
            price
        ))

    # 3️⃣ Update total order
    cursor.execute("""
        UPDATE orders SET total=%s WHERE id=%s
    """, (total, order_id))

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Order created", "order_id": order_id}
    '''


from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import psycopg2
from database_pg import get_connection
from jose import jwt
from datetime import datetime, timedelta
import os

SECRET_KEY = os.getenv("SECRET_KEY", "cambia-questa-chiave")

USERS = {
    "admin":  {"password": os.getenv("ADMIN_PASSWORD",  "admin123"),  "role": "admin"},
    "staff":  {"password": os.getenv("STAFF_PASSWORD",  "staff123"),  "role": "cucina"},
}

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(data: LoginRequest):
    user = USERS.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Credenziali errate")
    token = jwt.encode(
        {"sub": data.username, "role": user["role"], "exp": datetime.utcnow() + timedelta(hours=8)},
        SECRET_KEY, algorithm="HS256"
    )
    return {"token": token, "role": user["role"]}


app = FastAPI()

# Configurazione CORS: Fondamentale per far parlare il sito con il database
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelli per la validazione dati (Risolve l'errore 422)
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    note:       str = ""

class OrderCreate(BaseModel):
    table_number: int
    items: List[OrderItemCreate]
    note: str = ""

# 1. Endpoint per vedere i prodotti (Fa apparire il MENU sul sito)
@app.get("/products")
def get_products():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, name, price, category, available 
            FROM products
        """)
        rows = cursor.fetchall()
        return [
            {
                "id":        r[0],
                "name":      r[1],
                "price":     float(r[2]),
                "category":  r[3],
                "available": r[4] if r[4] is not None else True
            }
            for r in rows
        ]
    finally:
        cursor.close()
        conn.close()

# 2. Endpoint per salvare l'ordine (Logica Seria)
@app.post("/orders")
def create_order(order: OrderCreate):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1️⃣ Prima crea l'ordine e ottieni l'id
        cursor.execute("""
            INSERT INTO orders (table_number, total, date) 
            VALUES (%s, 0, CURRENT_TIMESTAMP) 
            RETURNING id
        """, (order.table_number,))
        order_id = cursor.fetchone()[0]

        total_order = 0

        # 2️⃣ Poi inserisci ogni prodotto
        for item in order.items:
            cursor.execute(
                "SELECT price FROM products WHERE id=%s",
                (item.product_id,)
            )
            res = cursor.fetchone()
            if not res:
                continue

            price    = float(res[0])
            subtotal = price * item.quantity
            total_order += subtotal

            cursor.execute("""
                INSERT INTO order_items 
                (order_id, product_id, quantity, price, note) 
                VALUES (%s, %s, %s, %s, %s)
            """, (order_id, item.product_id, item.quantity, price, item.note))

        # 3️⃣ Aggiorna il totale
        cursor.execute(
            "UPDATE orders SET total=%s WHERE id=%s",
            (total_order, order_id)
        )

        conn.commit()
        return {
            "status":   "success",
            "order_id": order_id,
            "total":    total_order
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/orders")
def get_orders():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT o.id, o.table_number, p.name, oi.quantity, o.date, oi.note
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            ORDER BY o.date DESC
        """)
        rows = cursor.fetchall()
        
        result = []
        for r in rows:
            result.append({
                "order_id": r[0],
                "table":    r[1],
                "product":  r[2],
                "qty":      r[3],
                "time":     str(r[4]),
                "note":     r[5] if r[5] else ""
            })
        
        return result # FastAPI capisce da solo che è un JSON
    except Exception as e:
        print(f"Errore: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

#nuovo endpoint dopo get_products
@app.patch("/products/{product_id}/available")
def toggle_product(product_id: int, available: bool):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE products SET available = %s WHERE id = %s
        """, (available, product_id))
        conn.commit()
        return {"status": "success", "product_id": product_id, "available": available}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# nuovo endpoint dopo get_orders:
@app.get("/stats/weekly")
def get_weekly_stats():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Incasso ultimi 7 giorni
        cursor.execute("""
            SELECT 
                DATE(date) as day,
                SUM(total) as revenue,
                COUNT(*) as orders
            FROM orders
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(date)
            ORDER BY day ASC
        """)
        daily = cursor.fetchall()

        # Prodotto più venduto
        cursor.execute("""
            SELECT 
                p.name,
                SUM(oi.quantity) as total_qty
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY p.name
            ORDER BY total_qty DESC
            LIMIT 5
        """)
        top_products = cursor.fetchall()

        # Ora di punta
        cursor.execute("""
            SELECT 
                EXTRACT(HOUR FROM date) as hour,
                COUNT(*) as orders
            FROM orders
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY hour
            ORDER BY orders DESC
            LIMIT 1
        """)
        peak_hour = cursor.fetchone()

        return {
            "daily":        [{"day": str(r[0]), "revenue": float(r[1]), "orders": r[2]} for r in daily],
            "top_products": [{"name": r[0], "qty": r[1]} for r in top_products],
            "peak_hour":    int(peak_hour[0]) if peak_hour else None
        }

    except Exception as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()