from sdk import CoreAPIClient, AuthAPI, StoreAPI

client = CoreAPIClient("http://localhost:5000")
auth = AuthAPI(client)
store = StoreAPI(client)

# Login as writer
login_data = auth.login("bob", "writerpass")
print("Logged in as:", login_data["user"])

# List stores (should be empty initially)
print("Stores:", store.list_stores())

# Create a store
store.create_store("TiendaNueva")

# Create an item in that store
store.create_item("TiendaNueva", "Router", "192.168.1.1")

# List again
print("Stores after creation:", store.list_stores())

# Rename store
store.rename_store("TiendaNueva", "TiendaRenombrada")

print("Stores after rename:", store.list_stores())