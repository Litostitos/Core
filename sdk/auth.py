class AuthAPI:
    """
    Authentication helper for the Store API.
    """
    def __init__(self, client):
        self.client = client

    def login(self, username, password):
        """
        Performs login and stores the JWT token in the client.
        Returns the full response JSON (token + user info).
        """
        data = self.client.post("/auth/login", json={
            "username": username,
            "password": password
        })

        # Save token in client for subsequent requests
        self.client.token = data["access_token"]
        return data