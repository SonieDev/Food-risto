from models import Product
from system import CashRegister, RestaurantSystem

# Casse
caisseA = CashRegister(name="Boissons", categories=["boissons"])
caisseB = CashRegister(name="Grillade", categories=["grillade"])
caisseC = CashRegister(name="Hamburger&&Friture", categories=["hamburger"])

# Prodotti
caffe = Product("caffe", 2.50, "boissons")
tea = Product("tea", 2.5, "boissons")
liqueur = Product("liqueur", 5.0, "boissons")
juice = Product("juice", 3.0, "boissons")
coca = Product("coca", 2.5, "boissons")
sprite = Product("sprite", 2.5, "boissons")

pollo = Product("pollo", 12.0, "grillade")
gallo = Product("gallo", 14.0, "grillade")
chicken_creek = Product("chicken creek", 15.0, "grillade")
buffalo = Product("buffalo", 16.0, "grillade")
ribs = Product("ribs", 18.0, "grillade")
barbecue = Product("barbecue", 20.0, "grillade")

smach = Product("smach", 12.0, "hamburger")
dakota = Product("dakota", 9.0, "hamburger")
american_burger = Product("american burger", 10.0, "hamburger")
nugget = Product("nugget", 6.0, "hamburger")
wings = Product("wings", 12.0, "hamburger")
french = Product("french", 4.0, "hamburger")
louisiana = Product("louisiana", 11.0, "hamburger")
bbq_burger = Product("bbq burger", 12.0, "hamburger")

# Sistema
system = RestaurantSystem(total_tables=10)
system.add_cash_register(caisseA)
system.add_cash_register(caisseB)
system.add_cash_register(caisseC)

# Menu
menu = {
    "caffe": caffe,
    "tea": tea,
    "liqueur": liqueur,
    "juice": juice,
    "coca": coca,
    "sprite": sprite,
    "pollo": pollo,
    "gallo": gallo,
    "chicken": chicken_creek,
    "buffalo": buffalo,
    "ribs": ribs,
    "barbecue": barbecue,
    "smach": smach,
    "dakota": dakota,
    "american": american_burger,
    "nugget": nugget,
    "wings": wings,
    "french": french,
    "louisiana": louisiana,
    "bbq": bbq_burger
}
