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


from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List
import psycopg2
from database_pg import get_connection
from jose import jwt
from datetime import datetime, timedelta
from collections import defaultdict
import anthropic
import time
import os

app = FastAPI()

# ══════════════════════════════════════════
# CORS
# ══════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # puoi mettere il tuo dominio Netlify qui
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════
# MODELLI ORDINE
# ══════════════════════════════════════════
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    note: str = ""

class OrderCreate(BaseModel):
    table_number: int
    items: List[OrderItemCreate]
    note: str = ""

# ══════════════════════════════════════════
# CONFIG JWT + UTENTI
# ══════════════════════════════════════════
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-questa-chiave")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
STAFF_PASSWORD = os.getenv("STAFF_PASSWORD")

if not ADMIN_PASSWORD or not STAFF_PASSWORD:
    raise RuntimeError("❌ ADMIN_PASSWORD e STAFF_PASSWORD devono essere impostate su Railway!")

USERS = {
    "admin": {"password": ADMIN_PASSWORD, "role": "admin"},
    "staff": {"password": STAFF_PASSWORD, "role": "cucina"},
}

# ══════════════════════════════════════════
# ANTI BRUTE FORCE
# ══════════════════════════════════════════
login_attempts = defaultdict(list)

def is_blocked(ip: str) -> bool:
    now = time.time()
    # Mantieni solo tentativi degli ultimi 5 minuti
    login_attempts[ip] = [t for t in login_attempts[ip] if now - t < 300]
    # Blocca dopo 5 tentativi falliti
    return len(login_attempts[ip]) >= 5

# ══════════════════════════════════════════
# VERIFICA TOKEN
# ══════════════════════════════════════════
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")

# ══════════════════════════════════════════
# MODELLO LOGIN
# ══════════════════════════════════════════
class LoginRequest(BaseModel):
    username: str
    password: str

# ══════════════════════════════════════════
# ENDPOINT LOGIN
# ══════════════════════════════════════════
@app.post("/login")
def login(data: LoginRequest, request: Request):
    ip = request.client.host

    # Controlla se IP è bloccato
    if is_blocked(ip):
        raise HTTPException(status_code=429, detail="Troppi tentativi. Aspetta 5 minuti.")

    user = USERS.get(data.username)
    if not user or user["password"] != data.password:
        # Registra tentativo fallito
        login_attempts[ip].append(time.time())
        raise HTTPException(status_code=401, detail="Credenziali errate")

    # Login ok → resetta tentativi
    login_attempts[ip] = []

    token = jwt.encode(
        {
            "sub": data.username,
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(hours=2)
        },
        SECRET_KEY,
        algorithm="HS256"
    )
    return {"token": token, "role": user["role"]}

# ══════════════════════════════════════════
# GET PRODOTTI — pubblico (serve al menu clienti)
# ══════════════════════════════════════════
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

# ══════════════════════════════════════════
# POST ORDINE — pubblico (clienti ordinano)
# ══════════════════════════════════════════
@app.post("/orders")
def create_order(order: OrderCreate):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO orders (table_number, total, date) 
            VALUES (%s, 0, CURRENT_TIMESTAMP) 
            RETURNING id
        """, (order.table_number,))
        order_id = cursor.fetchone()[0]

        total_order = 0

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

# ══════════════════════════════════════════
# GET ORDINI — protetto (solo staff e admin)
# ══════════════════════════════════════════
@app.get("/orders")
def get_orders(token = Depends(verify_token)):
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

        return result
    except Exception as e:
        print(f"Errore: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# ══════════════════════════════════════════
# TOGGLE PRODOTTO — protetto (solo admin)
# ══════════════════════════════════════════
@app.patch("/products/{product_id}/available")
def toggle_product(product_id: int, available: bool, token = Depends(verify_token)):
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

# ══════════════════════════════════════════
# STATS SETTIMANALI — protetto (solo admin)
# ══════════════════════════════════════════
@app.get("/stats/weekly")
def get_weekly_stats(token = Depends(verify_token)):
    conn = get_connection()
    cursor = conn.cursor()
    try:
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

# ══════════════════════════════════════════
# CHAT IA — Config
# ══════════════════════════════════════════
ai_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Controllo chiave
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_KEY:
    raise RuntimeError("❌ ANTHROPIC_API_KEY non trovata!")

SYSTEM_PROMPT = """Sei l'assistente virtuale del ristorante STEVIA, un ristorante premium specializzato in hamburger gourmet e grigliate.

INFORMAZIONI:
- Orari: Lunedì-Domenica 12:00-15:00 e 19:00-23:30
- Prenotazioni: +39 02 1234567

MENU:
🍔 HAMBURGER: Smach 12€, Dakota 9€, American 10€, Louisiana 11€, BBQ 12€
🔥 GRIGLIATE: Pollo 12€, Gallo 14€, Chicken Creek 15€, Buffalo 16€, Ribs 18€, Barbecue mix 20€
🍟 SFIZIOSITÀ: Nuggets 6€, Wings 12€, French fries 4€
🥤 BEVANDE: Caffè/Tè/Coca/Sprite 2.50€, Succo 3€, Liquori 5€

Rispondi sempre in italiano, sii amichevole e consiglia i piatti con entusiasmo."""

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

# ══════════════════════════════════════════
# ENDPOINT CHAT IA — pubblico (clienti)
# ══════════════════════════════════════════
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        response = ai_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": m.role, "content": m.content} for m in req.messages]
        )
        return {"reply": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def home():
    return {"message": "Backend Ristorante attivo"}