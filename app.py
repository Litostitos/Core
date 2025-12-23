from flask import Flask, request, g
from flask_sqlalchemy import SQLAlchemy
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

from flask_restx import Api, Resource, fields, Namespace

# -----------------------------------------------------------------------------
# Flask + RESTX initialization
# -----------------------------------------------------------------------------
app = Flask(__name__)

# Swagger JWT Authorization
authorizations = {
    "BearerAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer {token}'"
    }
}

api = Api(
    app,
    version="1.0",
    title="Core API",
    description="API documentation (OpenAPI/Swagger) estilo DEVCOR",
    doc="/swagger",
    authorizations=authorizations,
    security="BearerAuth"
)

# Namespaces
auth_ns = Namespace("auth", description="Authentication operations")
store_ns = Namespace("store", description="Store and item operations")

api.add_namespace(auth_ns)
api.add_namespace(store_ns)

# -----------------------------------------------------------------------------
# JWT configuration
# -----------------------------------------------------------------------------
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "change-me-in-prod")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(
    seconds=int(os.environ.get("JWT_ACCESS_EXPIRES_SECONDS", 60 * 60 * 8))
)

jwt = JWTManager(app)

# -----------------------------------------------------------------------------
# Database configuration
# -----------------------------------------------------------------------------
os.makedirs(app.instance_path, exist_ok=True)
db_path = os.path.join(app.instance_path, "data.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------------------------------------------------------
# Models (SQLAlchemy)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# RESTX Models (OpenAPI)
# -----------------------------------------------------------------------------
login_model = auth_ns.model("Login", {
    "username": fields.String(required=True),
    "password": fields.String(required=True)
})

store_create_model = store_ns.model("StoreCreate", {
    "name": fields.String(required=True)
})

item_create_model = store_ns.model("ItemCreate", {
    "name": fields.String(required=True),
    "ip": fields.String(required=True)
})

store_model = store_ns.model("Store", {
    "name": fields.String,
    "items": fields.List(fields.Raw)
})

item_model = store_ns.model("Item", {
    "name": fields.String,
    "ip": fields.String
})

# -----------------------------------------------------------------------------
# Authentication / Authorization
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# FIX: Decorator without jsonify() (prevents Swagger 500 errors)
# -----------------------------------------------------------------------------
def require_role(min_role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception as e:
                return {"message": "Missing or invalid token", "error": str(e)}, 401

            identity = get_jwt_identity()
            if not identity:
                return {"message": "Invalid token (no identity)"}, 401

            g.current_user = identity
            g.current_role = USER_ROLES.get(identity, "reader")

            if ROLE_HIERARCHY.get(g.current_role, 0) < ROLE_HIERARCHY.get(min_role, 0):
                return {"message": "Forbidden: insufficient role"}, 403

            return f(*args, **kwargs)
        return wrapped
    return decorator

# -----------------------------------------------------------------------------
# AUTH ENDPOINTS
# -----------------------------------------------------------------------------
@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.doc(description="Authenticate user and return JWT access token")
    def post(self):
        data = request.get_json() or {}
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return {"message": "username and password required"}, 400
        if not check_credentials(username, password):
            return {"message": "invalid credentials"}, 401

        access_token = create_access_token(identity=username)
        return {
            "access_token": access_token,
            "user": {"username": username, "role": USER_ROLES.get(username)}
        }, 200

# -----------------------------------------------------------------------------
# STORE ENDPOINTS
# -----------------------------------------------------------------------------
@store_ns.route("/")
class StoreList(Resource):
    @require_role("reader")
    @store_ns.marshal_list_with(store_model)
    @store_ns.doc(description="Get all stores (reader or higher)")
    def get(self):
        stores = Store.query.all()
        return [s.to_dict() for s in stores]

    @require_role("writer")
    @store_ns.expect(store_create_model)
    @store_ns.marshal_with(store_model, code=201)
    @store_ns.doc(description="Create a new store (writer or higher)")
    def post(self):
        data = request.get_json() or {}
        name = data.get("name")

        if not name:
            return {"message": "name required"}, 400
        if Store.query.filter_by(name=name).first():
            return {"message": "store exists"}, 400

        new_store = Store(name=name)
        db.session.add(new_store)
        db.session.commit()
        return new_store.to_dict(), 201


@store_ns.route("/<string:name>/item")
class ItemCreate(Resource):
    @require_role("writer")
    @store_ns.expect(item_create_model)
    @store_ns.marshal_with(item_model, code=201)
    @store_ns.doc(description="Create an item inside a store (writer or higher)")
    def post(self, name):
        data = request.get_json() or {}

        store = Store.query.filter_by(name=name).first()
        if not store:
            return {"message": "store not found"}, 404

        item_name = data.get("name")
        ip = data.get("ip")

        if not item_name or not ip:
            return {"message": "name and ip required"}, 400

        new_item = Item(name=item_name, ip=ip, store=store)
        db.session.add(new_item)
        db.session.commit()
        return new_item.to_dict(), 201


@store_ns.route("/<string:name>")
class StoreOperations(Resource):
    @require_role("admin")
    @store_ns.doc(description="Delete a store (admin only)")
    def delete(self, name):
        store = Store.query.filter_by(name=name).first()
        if not store:
            return {"message": "Store not found"}, 404

        db.session.delete(store)
        db.session.commit()
        return {"message": "Store deleted"}, 200

    @require_role("writer")
    @store_ns.doc(description="Rename a store (writer or higher)")
    def put(self, name):
        data = request.get_json() or {}
        new_name = data.get("name")

        if not new_name:
            return {"message": "new name required"}, 400

        store = Store.query.filter_by(name=name).first()
        if not store:
            return {"message": "store not found"}, 404

        if Store.query.filter_by(name=new_name).first():
            return {"message": "a store with the new name already exists"}, 400

        store.name = new_name
        db.session.commit()

        refreshed = Store.query.get(store.id)
        return refreshed.to_dict(), 200

# -----------------------------------------------------------------------------
# DEBUG ENDPOINT
# -----------------------------------------------------------------------------
@store_ns.route("/debug/list")
class DebugStores(Resource):
    def get(self):
        stores = Store.query.all()
        return {"stores": [s.name for s in stores]}

# -----------------------------------------------------------------------------
# Initialize DB
# -----------------------------------------------------------------------------
with app.app_context():
    db.create_all()

# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("Resolved DB path:", db_path)
    app.run(host="0.0.0.0", port=5000, debug=True)