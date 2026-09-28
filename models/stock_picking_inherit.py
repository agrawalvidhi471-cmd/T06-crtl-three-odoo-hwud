from odoo import models, fields
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Cold-chain transit information
    transit_monitoring_state = fields.Selection(
        [
            ('normal', 'Normal Transit'),
            ('excursion', 'Excursion Detected'),
            ('reroute', 'Reroute In Progress'),
            ('quarantine', 'Quarantine'),
        ],
        string='Cold-Chain Transit Status',
        default='normal',
        tracking=True,
    )

    vehicle_container_id = fields.Char(
        string='Vehicle / Container ID',
        help='Identifier of the refrigerated vehicle or container.'
    )

    source_warehouse = fields.Char(
        string='Source Warehouse',
        help='Warehouse from which this shipment originated.'
    )

    destination_hub = fields.Char(
        string='Destination Hub',
        help='Destination hub for this shipment.'
    )

    live_gps_coordinates = fields.Char(
        string='Live GPS Coordinates',
        help='Latest GPS coordinates reported by the transport sensor.'
    )

    # Telemetry readings associated with this shipment
    telemetry_log_ids = fields.One2many(
        'telemetry.log',
        'picking_id',
        string='Telemetry Logs'
    )

    def button_validate(self):
        """
        Prevent a transfer from being validated if any lot
        in the transfer has been marked as compromised.
        """

        for picking in self:
            compromised_lots = picking.move_line_ids.mapped(
                'lot_id'
            ).filtered(
                lambda lot: lot.batch_health == 'compromised'
            )

            if compromised_lots:
                lot_names = ', '.join(
                    compromised_lots.mapped('name')
                )

                raise UserError(
                    'Transfer blocked!\n\n'
                    'The following lot(s) are marked as COMPROMISED:\n'
                    '%s\n\n'
                    'The transfer cannot be validated until the '
                    'cold-chain issue has been resolved.'
                    % lot_names
                )

        return super().button_validate()