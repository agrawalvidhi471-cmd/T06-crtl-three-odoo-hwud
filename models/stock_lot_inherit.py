from odoo import models, fields


class StockLot(models.Model):
    _inherit = 'stock.lot'

    # Cold-chain temperature limits
    temp_min_c = fields.Float(
        string='Minimum Temperature (°C)',
        help='Minimum allowed storage temperature for this batch.'
    )

    temp_max_c = fields.Float(
        string='Maximum Temperature (°C)',
        help='Maximum allowed storage temperature for this batch.'
    )

    max_allowed_humidity = fields.Float(
        string='Maximum Humidity (%)',
        help='Maximum allowed humidity for this batch.'
    )

    # Sensor information
    sensor_device_id = fields.Char(
        string='Sensor Device ID',
        help='ID of the IoT sensor monitoring this batch.'
    )

    # Cold-chain health
    batch_health = fields.Selection(
        [
            ('optimal', 'Optimal'),
            ('warning', 'Warning'),
            ('critical', 'Critical'),
            ('compromised', 'Compromised'),
        ],
        string='Cold-Chain Health',
        default='optimal',
        tracking=True,
        help='Current cold-chain condition of this batch.'
    )

    # Excursion tracking
    cumulative_excursion_minutes = fields.Integer(
        string='Cumulative Excursion (Minutes)',
        default=0,
        help='Total time this batch has spent outside its allowed temperature range.'
    )

    # Shelf-life information
    original_expiration_date = fields.Datetime(
        string='Original Expiration Date',
        help='Original expiration date before cold-chain degradation.'
    )

    dynamic_expiration_date = fields.Datetime(
        string='Dynamic Expiration Date',
        help='Updated expiration date calculated from cold-chain exposure.'
    )

    quality_retention_pct = fields.Float(
        string='Quality Retention (%)',
        default=100.0,
        help='Estimated percentage of product quality remaining.'
    )

    # Relationships with other parts of the system
    telemetry_log_ids = fields.One2many(
        'telemetry.log',
        'lot_id',
        string='Telemetry Logs'
    )

    spoilage_incident_ids = fields.One2many(
        'spoilage.incident',
        'lot_id',
        string='Spoilage Incidents'
    )