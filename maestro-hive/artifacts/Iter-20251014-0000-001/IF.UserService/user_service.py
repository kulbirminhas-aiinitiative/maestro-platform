
class UserService:
    def create_user(self, username: str) -> dict:
        return {"username": username, "id": 1}

    def get_user(self, user_id: int) -> dict:
        return {"username": "test", "id": user_id}
