# -*- coding: utf-8 -*-
import logging
from dateutil.parser import isoparse
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TelemetryAPIController(http.Controller):

    def _validate_api_key(self, api_key):
        system_key = request.env["ir.config_parameter"].sudo().get_param(
            "coldchain.api_key", default="sec_live_default_secret_key"
        )
        return api_key == system_key

    @http.route(
        "/api/v1/telemetry/ingest",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False
    )
    def ingest_telemetry(self, **kwargs):
        """
        Ingest bulk sensor records via JSON-RPC / REST JSON.
        In modern Odoo type="json", the payload is pre-parsed in request.dispatcher.jsonrequest.
        """
        payload = request.dispatcher.jsonrequest or kwargs

        api_key = payload.get("api_key")
        if not self._validate_api_key(api_key):
            return {"status": "unauthorized", "message": "Invalid or missing API key"}

        readings = payload.get("readings", [])
        if not isinstance(readings, list) or not readings:
            return {"status": "error", "message": "Field 'readings' must be a non-empty list"}

        # Bulk resolve lot names to lot records
        lot_names = list({r.get("lot_name") for r in readings if r.get("lot_name")})
        lots = request.env["stock.lot"].sudo().search([("name", "in", lot_names)])
        lot_map = {lot.name: lot.id for lot in lots}

        vals_list = []
        rejected = []

        for idx, reading in enumerate(readings):
            lot_name = reading.get("lot_name")
            lot_id = lot_map.get(lot_name)

            if not lot_id:
                rejected.append({"index": idx, "reason": f"Lot '{lot_name}' not found"})
                continue

            raw_timestamp = reading.get("timestamp")
            try:
                parsed_time = isoparse(raw_timestamp).astimezone().replace(tzinfo=None) if raw_timestamp else False
            except Exception:
                rejected.append({"index": idx, "reason": f"Malformed ISO-8601 timestamp: '{raw_timestamp}'"})
                continue

            vals_list.append({
                "device_id": reading.get("device_id"),
                "lot_id": lot_id,
                "timestamp": parsed_time,
                "temperature": reading.get("temperature"),
                "humidity": reading.get("humidity"),
                "battery_level": reading.get("battery_level"),
                "latitude": reading.get("latitude"),
                "longitude": reading.get("longitude"),
                "is_processed": False,
            })

        inserted_count = 0
        if vals_list:
            created_records = request.env["telemetry.log"].sudo().create(vals_list)
            inserted_count = len(created_records)

        return {
            "status": "success",
            "inserted_count": inserted_count,
            "rejected_count": len(rejected),
            "rejections": rejected,
        }