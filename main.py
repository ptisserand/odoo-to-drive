#!/usr/bin/env python
import time
import json
import requests
import os
import logging

from dotenv import load_dotenv

logger = logging.getLogger("vrac_sync")

load_dotenv()

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_LOGIN = os.getenv("ODOO_LOGIN")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

SYNCER_URL = os.getenv("SYNCER_URL")
SYNCER_LOGIN = os.getenv("SYNCER_LOGIN")
SYNCER_PASSWORD = os.getenv("SYNCER_PASSWORD")

ODOO_EXPORT_DATA = {
    "model": "product.template",
    "fields": [
        {"name": "id", "label": "External ID"},
        {"name": "name", "label": "Nom"},
        {"name": "qty_available", "label": "Quantité en stock"},
        {"name": "pos_categ_id/name", "label": "Catégorie du point de vente/Nom"},
        {"name": "seller_ids/name/name", "label": "Fournisseur/Fournisseur/Nom"},
        {"name": "list_price", "label": "Prix de vente"},
        {"name": "to_weight", "label": "A peser"},
    ],
    "ids": False,
    "domain": [["purchase_ok", "=", 1]],
    "context": {
        "lang": "fr_FR",
        "tz": "Europe/Paris",
        "uid": 14,
        "search_default_filter_to_purchase": 1,
        "active_model": "product.template",
    },
    "import_compat": True,
}


def odoo_export() -> bytes:
    s = requests.Session()
    payload = {"db": ODOO_DB, "login": ODOO_LOGIN, "password": ODOO_PASSWORD}
    url = f"{ODOO_URL}/login"
    resp = s.post(url, payload)
    if not resp.ok:
        msg = f"Login failed: {resp.reason}"
        logger.error(msg)
        raise Exception(msg)
    logger.debug("Waiting for ODOO login")
    time.sleep(3)
    # Hack ?
    resp = s.post(url, payload)
    resp = s.get(f"{ODOO_URL}")
    logger.debug(f"ODOO login return code: {resp.status_code}")

    token = int(time.time())
    payload = {"data": json.dumps(ODOO_EXPORT_DATA), "token": token}
    url = f"{ODOO_URL}/export/xls"
    resp = s.post(url, payload)
    if not resp.ok:
        msg = f"Export XLS failed : {resp.reason}"
        logger.error(msg)
        raise Exception(msg)
    return resp.content


def syncer_import(data: bytes):
    s = requests.Session()
    payload = {"email": SYNCER_LOGIN, "password": SYNCER_PASSWORD}
    resp = s.post(f"{SYNCER_URL}/api/login", json=payload)
    if not resp.ok:
        msg = f"Login failed: {resp.reason}"
        logger.error(msg)
        raise Exception(msg)
    resp = s.post(f"{SYNCER_URL}/upload", files={"xls": data})
    if not resp.ok:
        msg = f"Upload failed: {resp.reason}"
        logger.error(msg)
        raise Exception(msg)
    logger.info(f"Upload OK")
    result = resp.json()
    logger.info(f"Number of missing IDs {len(result['missing_ids'])}")


if __name__ == "__main__":
    log_level = logging.DEBUG
    logger.setLevel(log_level)
    ch = logging.StreamHandler()
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    data = odoo_export()
    logger.debug(f"XLS length: {len(data)}")
    syncer_import(data)
    logger.info("DONE")
