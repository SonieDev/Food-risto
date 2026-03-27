from datetime import datetime
import os

class Product:
    def __init__(self, name , price, category):
        self.name = name
        self.price = price 
        self.category = category
    
    def __str__(self):
        return f"{self.name} ({self.category}) -{self.price}€"


class OrderItem:
    def __init__(self, product, quantity):
        self.product = product
        self.quantity = quantity
    
    def subtotal(self):
        return self.product.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} = {self.subtotal()}€"


class Order:
    def __init__(self, table_number):
        self.table_number = table_number
        self.items = []
        self.created_at = datetime.now()
    
    def add_item(self, product, quantity):
        self.items.append(OrderItem(product, quantity))

    def total(self):
        return sum(item.subtotal() for item in self.items)
