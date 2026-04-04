import json
import os
import secrets
import string
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class PasswordManager:
    def __init__(self, file_path="passwords.json", fernet: Fernet | None = None):
        self.file_path = file_path
        self.fernet = fernet

        # Stelle sicher, dass die Datei existiert
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump({}, f)

    # ------------------- encryption -------------------
    def set_fernet(self, fernet: Fernet):
        self.fernet = fernet

    def encrypt_password(self, password: str) -> str:
        if not self.fernet:
            raise ValueError("Fernet key is not set.")
        return self.fernet.encrypt(password.encode()).decode()

    def decrypt_password(self, password: str) -> str:
        if not self.fernet:
            raise ValueError("Fernet key is not set.")
        try:
            return self.fernet.decrypt(password.encode()).decode()
        except Exception:
            # Falls Passwort nicht verschlüsselt ist
            return password

    # ------------------- load/save data -------------------
    def load_data_raw(self) -> dict:
        if not os.path.exists(self.file_path):
            return {}
        with open(self.file_path, "r") as f:
            return json.load(f)

    def load_data(self) -> dict:
        data = self.load_data_raw()
        for service, accounts in data.items():
            for acc in accounts:
                acc["password"] = self.decrypt_password(acc["password"])
        return data

    def save_data(self, service: str, username: str, password: str):
        data = self.load_data_raw()
        encrypted_password = self.encrypt_password(password)

        if service not in data:
            data[service] = []

        # allow multiple accounts per service
        data[service].append({
            "username": username,
            "password": encrypted_password
        })

        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)

    # ------------------- delete/update -------------------
    def delete_entry(self, service: str, username: str, password: str):
        data = self.load_data_raw()

        if service in data:
            data[service] = [
                acc for acc in data[service]
                if not (acc["username"] == username and self.decrypt_password(acc["password"]) == password)
            ]
            if not data[service]:
                del data[service]

        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)

    def update_entry(
        self,
        service: str,
        old_username: str,
        old_password: str,
        new_username: str,
        new_password: str
    ):
        data = self.load_data_raw()
        if service in data:
            for acc in data[service]:
                if acc["username"] == old_username and self.decrypt_password(acc["password"]) == old_password:
                    acc["username"] = new_username
                    acc["password"] = self.encrypt_password(new_password)
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)

    # ------------------- password generator -------------------
    @staticmethod
    def generate_password(length=16) -> str:
        letters = string.ascii_letters
        numbers = string.digits
        special = string.punctuation
        all_chars = letters + numbers + special
        return "".join(secrets.choice(all_chars) for _ in range(length))

    # ------------------- check empty file -------------------
    def is_empty(self) -> bool:
        if not os.path.exists(self.file_path):
            return True
        with open(self.file_path, "r") as f:
            try:
                data = json.load(f)
                return not bool(data)
            except json.JSONDecodeError:
                return True
            
def generate_key(master_password: str, salt: bytes) -> bytes:
    """
    Generates a Fernet key from a master password and salt.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))