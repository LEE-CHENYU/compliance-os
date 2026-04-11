"""Config-backed marketplace product catalog helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from compliance_os.web.models.marketplace import ProductRow


PRODUCT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "products.yaml"


@lru_cache(maxsize=1)
def _load_product_config() -> dict[str, list[dict[str, Any]]]:
    if not PRODUCT_CONFIG_PATH.exists():
        return {"products": []}
    with PRODUCT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    products = data.get("products")
    if not isinstance(products, list):
        return {"products": []}
    return {"products": [product for product in products if isinstance(product, dict)]}


def list_product_configs(*, include_inactive: bool = False) -> list[dict[str, Any]]:
    products = [dict(product) for product in _load_product_config()["products"]]
    if include_inactive:
        return products
    return [product for product in products if bool(product.get("active", False))]


def get_product_config(sku: str, *, include_inactive: bool = False) -> dict[str, Any] | None:
    for product in list_product_configs(include_inactive=include_inactive):
        if product.get("sku") == sku:
            return product
    return None


def sync_product_catalog(db: Session) -> list[dict[str, Any]]:
    """Ensure configured products exist in the marketplace tables."""
    products = list_product_configs(include_inactive=True)
    for config in products:
        sku = str(config["sku"])
        row = db.get(ProductRow, sku)
        if row is None:
            row = ProductRow(
                sku=sku,
                name=str(config.get("name", sku)),
                description=str(config.get("description", "")),
                price_cents=int(config.get("price_cents", 0) or 0),
                tier=str(config.get("tier", "tier_0")),
                requires_attorney=bool(config.get("requires_attorney", False)),
                requires_questionnaire=bool(config.get("requires_questionnaire", False)),
                active=bool(config.get("active", False)),
            )
            db.add(row)
            continue

        row.name = str(config.get("name", row.name))
        row.description = str(config.get("description", row.description or ""))
        row.price_cents = int(config.get("price_cents", row.price_cents) or 0)
        row.tier = str(config.get("tier", row.tier))
        row.requires_attorney = bool(config.get("requires_attorney", row.requires_attorney))
        row.requires_questionnaire = bool(config.get("requires_questionnaire", row.requires_questionnaire))
        row.active = bool(config.get("active", row.active))

    db.flush()
    return products


def serialize_product(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "sku": config["sku"],
        "name": config.get("name", config["sku"]),
        "public_name": config.get("public_name"),
        "description": config.get("description", ""),
        "public_description": config.get("public_description"),
        "price_cents": int(config.get("price_cents", 0) or 0),
        "tier": config.get("tier", "tier_0"),
        "requires_attorney": bool(config.get("requires_attorney", False)),
        "requires_questionnaire": bool(config.get("requires_questionnaire", False)),
        "active": bool(config.get("active", False)),
        "category": config.get("category"),
        "filing_method": config.get("filing_method"),
        "fulfillment_mode": config.get("fulfillment_mode"),
        "headline": config.get("headline"),
        "public_headline": config.get("public_headline"),
        "highlights": list(config.get("highlights") or []),
        "public_highlights": list(config.get("public_highlights") or []),
        "cta_label": config.get("cta_label"),
        "public_cta_label": config.get("public_cta_label"),
        "path": config.get("path"),
    }
