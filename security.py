from passlib.context import CryptContext
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 🔒 Hash password safely (handles long passwords)
def hash_password(password: str):
    # Step 1: SHA256 (removes length issue)
    sha256_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Step 2: bcrypt
    return pwd_context.hash(sha256_hash)


def verify_password(plain_password: str, hashed_password: str):
    sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(sha256_hash, hashed_password)