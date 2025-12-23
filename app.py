from flask import Flask,request, g, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from schemas import ItemSchema, StoreSchema
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

app=Flask(__name__)

db_path = os.path.join(app.instance_path, "data.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    items = db.relationship(
        "Item",
       backref="store",
       lazy=True,
      cascade="all, delete-orphan"
   )

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)

# Initialize schemas
item_schema = ItemSchema()
store_schema = StoreSchema()

# Authentication helpers (moved up so decorators like @require_role are defined before use)
#Authentication

USERS = {
    "alice": generate_password_hash("readerpass"),
    "bob": generate_password_hash("writerpass"),
    "admin": generate_password_hash("adminpass"),
}
USER_ROLES = {
    "alice": "reader",
    "bob": "writer",
    "admin": "admin",
}
ROLE_HIERARCHY = {
    "reader": 10,
    "writer": 20,
    "admin": 30,
}


def check_credentials(username, password):
    pw_hash = USERS.get(username)
    if not pw_hash:
        return False
    return check_password_hash(pw_hash, password)

def basic_auth_required(realm="Login Required"):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_credentials(auth.username, auth.password):
                # Ask client to provide credentials
                return make_response(
                    jsonify({"message": "Authentication required"}), 
                    401,
                    {"WWW-Authenticate": f'Basic realm="{realm}"'}
                )
            
            g.current_user = auth.username
            g.current_user_role = USER_ROLES.get(auth.username)
            # optionally attach user identity to request context
            return f(*args, **kwargs)
        return wrapped
    return decorator

# new: role requirement decorator (per-request auth + role check)
def require_role(min_role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_credentials(auth.username, auth.password):
                return make_response(
                    jsonify({"message": "Authentication required"}),
                    401,
                    {"WWW-Authenticate": 'Basic realm="Login Required"'}
                )
            # attach identity and role
            g.current_user = auth.username
            g.current_role = USER_ROLES.get(auth.username, "reader")
            # check hierarchy
            if ROLE_HIERARCHY.get(g.current_role, 0) < ROLE_HIERARCHY.get(min_role, 0):
                return jsonify({"message": "Forbidden: insufficient role"}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.get("/")
def welcome():
    return {"message": "Welcome!"}

@app.get("/store")
@require_role("reader")
def get_stores():
    stores = Store.query.all()
    return {"stores": [
        {"name": store.name, "items": [{"name": item.name, "ip": item.ip} for item in store.items]}
        for store in stores
    ]}



@app.post("/store")
@require_role("writer")
def crate_store():
    request_data = request.get_json()
    #vlidate incoming data
    errors = store_schema.validate(request_data)
    if errors:
        return {"message": "Validation errors", "errors": errors}, 400
    
    new_store = Store(name=request_data['name'])
    db.session.add(new_store)
    db.session.commit()

    return {"name": new_store.name, "items": []}, 201

@app.post("/store/<string:name>/item")
@require_role("writer")
def crate_item(name):
    request_data = request.get_json()
    #validate incoming data
    errors = item_schema.validate(request_data)
    if errors:
        return {"message": "Validation errors", "errors": errors}, 400
    store = Store.query.filter_by(name=name).first()
    if not store:
        return {"message": "storee not found"}, 404

    new_item = Item(name=request_data['name'], ip=request_data['ip'], store_id=store.id)
    db.session.add(new_item)
    db.session.commit()

    return {"name": new_item.name, "ip": new_item.ip}, 201

#Delete store 
@app.route("/store/<string:name>", methods=["DELETE"])
@require_role("admin")
def delete_store(name):
    store = Store.query.filter_by(name=name).first()
    if not store:
        return {"message": "Store not found"}, 404

    db.session.delete(store)
    db.session.commit()
    return {"message": "Store deleted"}, 200

with app.app_context():
    db.create_all() 

print("Resolved DB path:", os.path.join(app.instance_path, "data.db"))

@app.route("/store/<string:name>", methods=["PUT", "PATCH"])
def rename_store(name):
    import traceback
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

        # return a fresh instance (avoid detached/serialization issues)
        refreshed = Store.query.get(store.id)
        return jsonify(refreshed.to_dict()), 200

    except Exception as e:
        # log full traceback to server console / logs
        app.logger.error("Error renaming store:\n%s", traceback.format_exc())
        return jsonify({"message": "internal server error"}), 500


#Authentication

USERS = {
    "alice": generate_password_hash("readerpass"),
    "bob": generate_password_hash("writerpass"),
    "admin": generate_password_hash("adminpass"),
}
USER_ROLES = {
    "alice": "reader",
    "bob": "writer",
    "admin": "admin",
}
ROLE_HIERARCHY = {
    "reader": 10,
    "writer": 20,
    "admin": 30,
}


def check_credentials(username, password):
    pw_hash = USERS.get(username)
    if not pw_hash:
        return False
    return check_password_hash(pw_hash, password)

def basic_auth_required(realm="Login Required"):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_credentials(auth.username, auth.password):
                # Ask client to provide credentials
                return make_response(
                    jsonify({"message": "Authentication required"}), 
                    401,
                    {"WWW-Authenticate": f'Basic realm="{realm}"'}
                )
            
            g.current_user = auth.username
            g.current_user_role = USER_ROLES.get(auth.username)
            # optionally attach user identity to request context
            return f(*args, **kwargs)
        return wrapped
    return decorator

# new: role requirement decorator (per-request auth + role check)
def require_role(min_role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_credentials(auth.username, auth.password):
                return make_response(
                    jsonify({"message": "Authentication required"}),
                    401,
                    {"WWW-Authenticate": 'Basic realm="Login Required"'}
                )
            # attach identity and role
            g.current_user = auth.username
            g.current_role = USER_ROLES.get(auth.username, "reader")
            # check hierarchy
            if ROLE_HIERARCHY.get(g.current_role, 0) < ROLE_HIERARCHY.get(min_role, 0):
                return jsonify({"message": "Forbidden: insufficient role"}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/login")
@basic_auth_required()
def protected_basic():
    return jsonify({"message": "You are authenticated with Basic Auth"})



#Temporary debug
@app.route("/debug/stores")
def debug_stores():
    stores = Store.query.all()
    return {"stores": [store.name for store in stores]}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

