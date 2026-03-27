from models import Order
from menu import system
# from database.repository import OrderRepository
from repository_pg import OrderRepository
from reports import *

class BackendService:

    def __init__(self):
        self.repo = OrderRepository()

    def assign_table(self):
        return system.assign_table()

    def create_order(self, table_number):
        return Order(table_number)

    def process_order(self, order):
        system.dispatch_order(order)
        system.show_registerS(order)
        save_receipt_file(order)
        update_daily_report(order)
        save_to_history(order)
        self.repo.save_order(order)

    def free_table(self, table_number):
        system.free_table(table_number)

    def clear_registers(self):
        system.clear_registers()