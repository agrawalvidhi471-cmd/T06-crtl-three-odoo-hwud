from datetime import timedelta

from odoo import models, fields, api


class TelemetryLog(models.Model):
    _name = "telemetry.log"
    _description = "Cold Chain IoT Telemetry Reading"
    _order = "timestamp desc, id desc"

    device_id = fields.Char(
        string="Device Identifier",
        required=True,
        index=True,
        help="Hardware MAC address or serial number of the logger."
    )

    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Associated Batch / Lot",
        required=True,
        index=True,
        ondelete="cascade"
    )

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Associated Shipment / Transfer",
        index=True,
        ondelete="set null"
    )

    timestamp = fields.Datetime(
        string="Sensor Timestamp",
        required=True,
        index=True,
        default=fields.Datetime.now,
        help="UTC timestamp recorded by the physical logger."
    )

    recorded_temp = fields.Float(
        string="Recorded Temperature (°C)",
        digits="ColdChain Metric",
        required=True
    )

    temperature = fields.Float(
        string="Temperature (°C)",
        digits="ColdChain Metric",
        compute="_compute_temperature_alias",
        inverse="_inverse_temperature_alias",
        store=True,
        help="Alias for recorded_temp."
    )

    recorded_humidity = fields.Float(
        string="Relative Humidity (%)",
        digits="ColdChain Metric"
    )

    humidity = fields.Float(
        string="Humidity (%)",
        digits="ColdChain Metric",
        compute="_compute_humidity_alias",
        inverse="_inverse_humidity_alias",
        store=True,
        help="Alias for recorded_humidity."
    )

    battery_level = fields.Float(
        string="Battery Level (%)",
        digits="ColdChain Metric"
    )

    latitude = fields.Float(
        string="Latitude",
        digits=(10, 6)
    )

    longitude = fields.Float(
        string="Longitude",
        digits=(10, 6)
    )

    gps_checkpoint = fields.Char(
        string="GPS Checkpoint",
        compute="_compute_gps_checkpoint",
        inverse="_inverse_gps_checkpoint",
        store=True
    )

    is_processed = fields.Boolean(
        string="Processed by Engine",
        default=False,
        index=True
    )

    is_breach = fields.Boolean(
        string="Threshold Breached?",
        compute="_compute_is_breach",
        store=True,
        help="True when temperature is outside the allowed batch range."
    )

    _sql_constraints = [
        (
            "unique_device_timestamp",
            "unique(device_id, timestamp)",
            "A telemetry log for this device and timestamp already exists."
        )
    ]

    # ---------------------------------------------------------
    # FIELD ALIASES
    # ---------------------------------------------------------

    @api.depends("recorded_temp")
    def _compute_temperature_alias(self):
        for record in self:
            record.temperature = record.recorded_temp

    def _inverse_temperature_alias(self):
        for record in self:
            record.recorded_temp = record.temperature

    @api.depends("recorded_humidity")
    def _compute_humidity_alias(self):
        for record in self:
            record.humidity = record.recorded_humidity

    def _inverse_humidity_alias(self):
        for record in self:
            record.recorded_humidity = record.humidity

    # ---------------------------------------------------------
    # GPS
    # ---------------------------------------------------------

    @api.depends("latitude", "longitude")
    def _compute_gps_checkpoint(self):
        for record in self:
            if record.latitude or record.longitude:
                record.gps_checkpoint = (
                    f"{record.latitude:.5f}, {record.longitude:.5f}"
                )
            elif not record.gps_checkpoint:
                record.gps_checkpoint = False

    def _inverse_gps_checkpoint(self):
        for record in self:
            if record.gps_checkpoint and "," in record.gps_checkpoint:
                try:
                    lat_str, lon_str = record.gps_checkpoint.split(",")
                    record.latitude = float(lat_str.strip())
                    record.longitude = float(lon_str.strip())
                except ValueError:
                    pass

    # ---------------------------------------------------------
    # BREACH DETECTION
    # ---------------------------------------------------------

    @api.depends(
        "recorded_temp",
        "lot_id.temp_min_c",
        "lot_id.temp_max_c"
    )
    def _compute_is_breach(self):
        for record in self:
            if record.lot_id:
                temp = record.recorded_temp
                min_t = record.lot_id.temp_min_c
                max_t = record.lot_id.temp_max_c

                record.is_breach = (
                    (min_t is not False and temp < min_t)
                    or
                    (max_t is not False and temp > max_t)
                )
            else:
                record.is_breach = (
                    record.recorded_temp < 2.0
                    or record.recorded_temp > 8.0
                )

    # ---------------------------------------------------------
    # AUTOMATIC COLD-CHAIN RESPONSE
    # ---------------------------------------------------------

    @api.model
    def create(self, vals):
        record = super().create(vals)

        if record.is_breach and record.lot_id:
            lot = record.lot_id

            # Move batch into critical monitoring status
            lot.write({
                "batch_health": "critical"
            })

            # Check if an active incident already exists
            existing_incident = self.env["spoilage.incident"].search([
                ("lot_id", "=", lot.id),
                (
                    "investigation_state",
                    "in",
                    ["logged", "qa_review"]
                )
            ], limit=1)

            if not existing_incident:

                # -------------------------------------------------
                # SEVERITY LOGIC
                #
                # 1°C or less above maximum = MODERATE
                # More than 1°C above maximum = CRITICAL
                #
                # Example for a 2–8°C product:
                # 8°C or below = no breach
                # 9°C = moderate
                # 10°C+ = critical
                # -------------------------------------------------

                temp_difference = (
                    record.recorded_temp - lot.temp_max_c
                )

                if temp_difference <= 1:
                    severity = "moderate"
                else:
                    severity = "critical"

                self.env["spoilage.incident"].create({
                    "lot_id": lot.id,

                    "picking_id": (
                        record.picking_id.id
                        if record.picking_id
                        else False
                    ),

                    "peak_breached_temp": record.recorded_temp,

                    "excursion_duration_hours": 0.0,

                    "severity_level": severity,

                    "ai_action_recommendation": (
                        "COLD-CHAIN BREACH DETECTED\n\n"
                        f"Sensor {record.device_id} reported "
                        f"{record.recorded_temp}°C.\n"
                        f"Allowed range: {lot.temp_min_c}°C - "
                        f"{lot.temp_max_c}°C.\n\n"
                        f"Severity classification: "
                        f"{severity.upper()}\n\n"
                        "Recommended action: quarantine the affected "
                        "batch and investigate the cold-chain excursion "
                        "before allowing further distribution."
                    ),
                })

            # -------------------------------------------------
            # CHATTER ALERT
            # -------------------------------------------------

            lot.message_post(
                body=(
                    "<b>🚨 Cold-Chain Breach Detected</b><br/>"
                    f"Sensor: {record.device_id}<br/>"
                    f"Temperature: {record.recorded_temp}°C<br/>"
                    f"Allowed range: {lot.temp_min_c}°C - "
                    f"{lot.temp_max_c}°C<br/>"
                    "<b>Batch moved to Critical status.</b>"
                ),
                subject="Cold-Chain Temperature Breach",
                message_type="notification"
            )

        return record

    # ---------------------------------------------------------
    # SENSOR HEARTBEAT CHECK
    # ---------------------------------------------------------

    @api.model
    def cron_check_sensor_heartbeats(self):

        timeout_threshold = (
            fields.Datetime.now()
            - timedelta(minutes=60)
        )

        tracked_lots = (
            self.env["stock.lot"].search([
                ("sensor_device_id", "!=", False)
            ])
            if hasattr(
                self.env["stock.lot"],
                "sensor_device_id"
            )
            else self.env["stock.lot"].browse()
        )

        for lot in tracked_lots:

            latest_log = self.search(
                [("lot_id", "=", lot.id)],
                limit=1,
                order="timestamp desc"
            )

            if (
                not latest_log
                or latest_log.timestamp < timeout_threshold
            ):
                lot.message_post(
                    body=(
                        f"Cold Chain Alert: Sensor "
                        f"{lot.sensor_device_id} has not reported since "
                        f"{latest_log.timestamp if latest_log else 'never'}. "
                        "Check device connectivity."
                    ),
                    subject="Telemetry Heartbeat Lost",
                    message_type="notification"
                )