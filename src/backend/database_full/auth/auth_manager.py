"""Авторизация - только вход/регистрация/сессии"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ..repository.user_repository import UserRepository


class AuthManager:
    def __init__(self):
        self.user_repo = UserRepository()

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str) -> Dict[str, Any]:
        if self.user_repo.user_exists(username):
            return {"success": False, "error": "Пользователь уже существует"}

        if len(username) < 3:
            return {"success": False, "error": "Имя не менее 3 символов"}
        if len(password) < 4:
            return {"success": False, "error": "Пароль не менее 4 символов"}

        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)

        success = self.user_repo.create_user(user_id, username, password_hash)
        if not success:
            return {"success": False, "error": "Ошибка создания"}

        self.user_repo.create_profile(user_id, username)

        return {"success": True, "user_id": user_id, "username": username}

    def login(self, username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        user = self.user_repo.get_user_by_username(username)
        if not user or user['password_hash'] != self._hash_password(password):
            return {"success": False, "error": "Неверный логин или пароль"}

        self.user_repo.update_last_login(user['id'])

        session_token = secrets.token_urlsafe(32)
        expires_in_days = 30 if remember_me else 1
        expires_at = datetime.now() + timedelta(days=expires_in_days)

        self.user_repo.create_session(user['id'], session_token, expires_at.isoformat())

        return {
            "success": True,
            "user_id": user['id'],
            "username": user['username'],
            "session_token": session_token,
            "expires_at": expires_at.isoformat()
        }

    def logout(self, session_token: str) -> bool:
        return self.user_repo.revoke_session(session_token)

    def get_user_id_by_token(self, session_token: str) -> Optional[str]:
        session = self.user_repo.get_session_by_token(session_token)
        if not session:
            return None

        expires_at = datetime.fromisoformat(session['expires_at'])
        if expires_at < datetime.now():
            return None

        return session['user_id']

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.user_repo.get_user_by_id(user_id)


auth_manager = AuthManager()