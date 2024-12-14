from fastapi import FastAPI, HTTPException

from database import SessionLocal, init_db
from models import Product


router = FastAPI()


def to_string(product: Product) -> dict:
    return {'id': product.id, 'name': product.name, 'quantity': product.quantity, 'price': product.price}


@router.on_event("startup")
def startup_event():
    init_db()


@router.post("/product/add")
def create_product(name: str, quantity: int, price: int):
    with SessionLocal() as db:
        existing_product = db.query(Product).filter(Product.name == name).first()

        if existing_product:
            raise HTTPException(status_code=400, detail="Product already exists!")

        new_product = Product(name=name, quantity=quantity, price=price)
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

    return {"message": f"Product added -> {to_string(new_product)}"}


@router.get("/products/")
def list_products():
    with SessionLocal() as db:
        products = db.query(Product).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "quantity": p.quantity,
                "price": p.price
            } for p in products
        ]


# New route: Get product by ID
@router.get("/products/{product_id}")
def get_product_by_id(product_id: int):
    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found!")
        
        return to_string(product)