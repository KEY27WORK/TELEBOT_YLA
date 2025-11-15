from decimal import Decimal

from app.domain.availability.status import AvailabilityStatus
from app.domain.products.entities import ProductInfo


def make_product(stock_data):
    return ProductInfo(
        title="Test product",
        price=Decimal("10.00"),
        stock_data=stock_data,
    )


def test_product_info_converts_bool_stock_entries():
    info = make_product({"Black": {"M": True, "L": False}})

    assert info.stock_data["Black"]["M"] is AvailabilityStatus.YES
    assert info.stock_data["Black"]["L"] is AvailabilityStatus.NO


def test_product_info_keeps_existing_status_instances():
    stock = {
        "Red": {
            "S": AvailabilityStatus.YES,
            "M": AvailabilityStatus.NO,
        }
    }
    info = make_product(stock)

    assert info.stock_data == stock
