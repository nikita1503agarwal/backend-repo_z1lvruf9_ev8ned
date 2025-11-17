import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

try:
    from bson import ObjectId
except Exception:  # safety on environments without bson, though pymongo provides it
    ObjectId = None

app = FastAPI(title="Ecommerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Models (aligned with schemas.py)
# -----------------------------
class ProductIn(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    image: Optional[str] = None
    in_stock: bool = True


class OrderItemIn(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int
    image: Optional[str] = None


class OrderIn(BaseModel):
    customer_name: str
    customer_email: str
    shipping_address: str
    items: List[OrderItemIn]


# -----------------------------
# Helpers
# -----------------------------

def serialize_id(value):
    if isinstance(value, ObjectId):
        return str(value)
    return value


def serialize_document(doc: dict) -> dict:
    if not doc:
        return doc
    doc = {**doc}
    if doc.get("_id") is not None:
        doc["id"] = serialize_id(doc.pop("_id"))
    # Convert nested ObjectIds if any
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc


# -----------------------------
# Basic routes
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Ecommerce backend is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# -----------------------------
# Schema endpoint (for viewers/tools)
# -----------------------------
@app.get("/schema")
def get_schema():
    from schemas import User, Product, Order  # type: ignore
    return {
        "user": User.model_json_schema(),
        "product": Product.model_json_schema(),
        "order": Order.model_json_schema(),
    }


# -----------------------------
# Product endpoints
# -----------------------------
@app.get("/api/products")
def list_products():
    docs = get_documents("product") if db else []
    return [serialize_document(d) for d in docs]


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        _id = ObjectId(product_id) if ObjectId else product_id
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")
    doc = db["product"].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_document(doc)


@app.post("/api/products", status_code=201)
def create_product(product: ProductIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    new_id = create_document("product", product.model_dump())
    doc = db["product"].find_one({"_id": ObjectId(new_id)}) if ObjectId else db["product"].find_one({"_id": new_id})
    return serialize_document(doc)


@app.post("/api/seed", status_code=201)
def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    sample = [
        {
            "title": "Vintage Leather Backpack",
            "description": "Handcrafted full-grain leather backpack with padded laptop sleeve.",
            "price": 129.99,
            "category": "Bags",
            "image": "https://images.unsplash.com/photo-1514477917009-389c76a86b68?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True
        },
        {
            "title": "Minimalist Watch",
            "description": "Stainless steel case, sapphire glass, Japanese movement.",
            "price": 89.0,
            "category": "Accessories",
            "image": "https://images.unsplash.com/photo-1511379938547-c1f69419868d?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True
        },
        {
            "title": "Wireless Headphones",
            "description": "Active noise cancellation with 30h battery life.",
            "price": 159.0,
            "category": "Audio",
            "image": "https://images.unsplash.com/photo-1518443254571-1f1e5b2d1a1f?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True
        },
        {
            "title": "Ceramic Mug",
            "description": "Matte glaze 12oz mug, microwave and dishwasher safe.",
            "price": 18.5,
            "category": "Home",
            "image": "https://images.unsplash.com/photo-1512100356356-de1b84283e18?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True
        }
    ]
    inserted = []
    for p in sample:
        new_id = create_document("product", p)
        inserted.append(new_id)
    # return created products
    docs = db["product"].find({"_id": {"$in": [ObjectId(i) for i in inserted]}}) if ObjectId else db["product"].find({})
    return [serialize_document(d) for d in docs]


# -----------------------------
# Order endpoints
# -----------------------------
@app.post("/api/orders", status_code=201)
def create_order(order: OrderIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    if not order.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    total = sum(i.price * max(1, i.quantity) for i in order.items)
    order_data = {
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "shipping_address": order.shipping_address,
        "items": [i.model_dump() for i in order.items],
        "total_amount": round(total, 2),
        "status": "pending",
    }
    new_id = create_document("order", order_data)
    created = db["order"].find_one({"_id": ObjectId(new_id)}) if ObjectId else db["order"].find_one({"_id": new_id})
    result = serialize_document(created)
    result["message"] = "Order placed successfully"
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
