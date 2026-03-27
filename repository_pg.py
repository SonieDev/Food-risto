from database_pg import get_connection


class OrderRepository:

    def save_order(self, order):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO orders (table_number, total, date)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        RETURNING id;
        """, (
            order.table_number,
            order.total()
        ))

        order_id = cursor.fetchone()[0]

        for item in order.items:
            cursor.execute("""
            INSERT INTO order_items
            (order_id, product_name, quantity, price)
            VALUES (%s, %s, %s, %s)
            """, (
                order_id,
                item.product.name,
                item.quantity,
                item.product.price
            ))

        conn.commit()
        cursor.close()
        conn.close()

# endpoind per vedere gli ordini
    def get_all_orders(self):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, table_number, total, date FROM orders;")
        rows = cursor.fetchall()

        orders = []
        for row in rows:
            orders.append({
                "id": row[0],
                "table_number": row[1],
                "total": row[2],
                "date": str(row[3])
            })

        cursor.close()
        conn.close()

        return orders
    
    #Get Order Details Completo
    def get_order_details(self, order_id):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                p.name,
                oi.quantity,
                oi.price
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order_id,))

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return rows
        

'''
    def get_all_orders(self):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM orders;")
        orders = cursor.fetchall()

        cursor.close()
        conn.close()

       return orders
''' 

    

    