class StoreAPI:
    """
    Store and Item operations for the Store API.
    """
    def __init__(self, client):
        self.client = client

    def list_stores(self):
        """
        GET /store/
        Returns a list of stores.
        """
        return self.client.get("/store/")

    def create_store(self, name):
        """
        POST /store/
        Creates a new store.
        """
        return self.client.post("/store/", json={"name": name})

    def create_item(self, store_name, name, ip):
        """
        POST /store/<store_name>/item
        Creates a new item inside a store.
        """
        return self.client.post(
            f"/store/{store_name}/item",
            json={"name": name, "ip": ip}
        )

    def delete_store(self, name):
        """
        DELETE /store/<name>
        Deletes a store.
        """
        return self.client.delete(f"/store/{name}")

    def rename_store(self, old_name, new_name):
        """
        PUT /store/<old_name>
        Renames a store.
        """
        return self.client.put(
            f"/store/{old_name}",
            json={"name": new_name}
        )