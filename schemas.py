"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- Order -> "order" collection
"""

from typing import List, Optional
from pydantic import BaseModel, Field

# -----------------------------
# USERS
# -----------------------------
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    is_active: bool = Field(True, description="Whether user is active")

# -----------------------------
# PRODUCTS
# -----------------------------
class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    image: Optional[str] = Field(None, description="Primary image URL")
    in_stock: bool = Field(True, description="Whether product is in stock")

# -----------------------------
# ORDERS
# -----------------------------
class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int = Field(ge=1)
    image: Optional[str] = None

class Order(BaseModel):
    customer_name: str
    customer_email: str
    shipping_address: str
    items: List[OrderItem]
    total_amount: float = Field(ge=0)
    status: str = Field("pending", description="Order status")
