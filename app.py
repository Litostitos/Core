# ...existing code...
from flask import Flask, request, g, jsonify
from flask_sqlalchemy import SQLAlchemy
from schemas import ItemSchema, StoreSchema
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import datetime

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    verify_jwt_in_request,
    get_jwt_identity,
)

app = Flask(__name__)

# JWT config - set a strong secret in env in production
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "change-me-in-prod")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(
    seconds=int(os.environ.get("JWT_ACCESS_EXPIRES_SECONDS", 60 * 60 * 8))
)

jwt = JWTManager(app)

# ensure instance folder exists for sqlite file
os.makedirs(app.instance_path, exist_ok=True)
db_path = os.path.join(app.instance_path, "data.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    items = db.relationship(
        "Item", backref="store", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {"name": self.name, "items": [i.to_dict() for i in self.items]}


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False)

    def to_dict(self):
        return {"name": self.name, "ip": self.ip}


# Initialize schemas
item_schema = ItemSchema()
store_schema = StoreSchema()

# --- Authentication / Authorization (JWT) ---
USERS = {
    "alice": generate_password_hash("readerpass"),
    "bob": generate_password_hash("writerpass"),
    "admin": generate_password_hash("adminpass"),
}
USER_ROLES = {"alice": "reader", "bob": "writer", "admin": "admin"}
ROLE_HIERARCHY = {"reader": 10, "writer": 20, "admin": 30}


def check_credentials(username, password):
    pw_hash = USERS.get(username)
    if not pw_hash:
        return False
    return check_password_hash(pw_hash, password)


def require_role(min_role):
    """
    Decorator: require a valid JWT and that the identity's role >= min_role.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception as e:
                return jsonify({"message": "Missing or invalid token", "error": str(e)}), 401

            identity = get_jwt_identity()
            if not identity:
                return jsonify({"message": "Invalid token (no identity)"}), 401

            g.current_user = identity
            g.current_role = USER_ROLES.get(identity, "reader")

            if ROLE_HIERARCHY.get(g.current_role, 0) < ROLE_HIERARCHY.get(min_role, 0):
                return jsonify({"message": "Forbidden: insufficient role"}), 403

            return f(*args, **kwargs)
        return wrapped
    return decorator


# --- Routes ---
@app.post("/auth/login")
def auth_login():
    """
    POST /auth/login
    JSON: { "username": "...", "password": "..." }
    Returns access_token if credentials valid.
    """
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"message": "username and password required"}), 400
    if not check_credentials(username, password):
        return jsonify({"message": "invalid credentials"}), 401

    access_token = create_access_token(identity=username)
    return (
        jsonify({"access_token": access_token, "user": {"username": username, "role": USER_ROLES.get(username)}}),
        200,
    )


@app.get("/")
def welcome():
    return {"message": "Welcome!"}


@app.get("/store")
@require_role("reader")
def get_stores():
    stores = Store.query.all()
    return {"stores": [s.to_dict() for s in stores]}


@app.post("/store")
@require_role("writer")
def crate_store():
    request_data = request.get_json() or {}
    errors = store_schema.validate(request_data)
    if errors:
        return {"message": "Validation errors", "errors": errors}, 400

    name = request_data.get("name")
    if not name:
        return {"message": "name required"}, 400
    if Store.query.filter_by(name=name).first():
        return {"message": "store exists"}, 400

    new_store = Store(name=name)
    db.session.add(new_store)
    db.session.commit()
    return {"name": new_store.name, "items": []}, 201


@app.post("/store/<string:name>/item")
@require_role("writer")
def crate_item(name):
    request_data = request.get_json() or {}
    errors = item_schema.validate(request_data)
    if errors:
        return {"message": "Validation errors", "errors": errors}, 400

    store = Store.query.filter_by(name=name).first()
    if not store:
        return {"message": "store not found"}, 404

    item_name = request_data.get("name")
    ip = request_data.get("ip")
    if not item_name or not ip:
        return {"message": "name and ip required"}, 400

    new_item = Item(name=item_name, ip=ip, store=store)
    db.session.add(new_item)
    db.session.commit()
    return {"name": new_item.name, "ip": new_item.ip}, 201


@app.route("/store/<string:name>", methods=["DELETE"])
@require_role("admin")
def delete_store(name):
    store = Store.query.filter_by(name=name).first()
    if not store:
        return {"message": "Store not found"}, 404

    db.session.delete(store)
    db.session.commit()
    return {"message": "Store deleted"}, 200


@app.route("/store/<string:name>", methods=["PUT", "PATCH"])
@require_role("writer")
def rename_store(name):
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        new_name = data.get("name")
        if not new_name:
            return jsonify({"message": "new name required"}), 400

        store = Store.query.filter_by(name=name).first()
        if not store:
            return jsonify({"message": "store not found"}), 404

        if Store.query.filter_by(name=new_name).first():
            return jsonify({"message": "a store with the new name already exists"}), 400

        store.name = new_name
        db.session.commit()

        refreshed = Store.query.get(store.id)
        return jsonify(refreshed.to_dict()), 200

    except Exception as e:
        app.logger.error("Error renaming store: %s", str(e))
        return jsonify({"message": "internal server error"}), 500


# Temporary debug
@app.route("/debug/stores")
def debug_stores():
    stores = Store.query.all()
    return {"stores": [store.name for store in stores]}


# Initialize DB and run
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    print("Resolved DB path:", db_path)
    app.run(host="0.0.0.0", port=5000, debug=True)
# ...existing code...