import hashlib
def hasher(uep):
    salt = "5gz"
    db_password = uep + salt
    h = hashlib.md5(db_password.encode())
    return h.hexdigest()