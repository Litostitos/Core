from sdk import CoreAPIClient, AuthAPI, StoreAPI

client = CoreAPIClient("http://localhost:5000")

auth = AuthAPI(client)
auth.login("bob", "writepass")

store = StoreAPI(client)

store.create_item("TiendaRenombrada", "Switch", "192.168.1.2")
print("Item created in TiendaRenombrada")
print("Current stores:", store.list_stores())