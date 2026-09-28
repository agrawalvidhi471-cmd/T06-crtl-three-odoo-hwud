# -*- coding: utf-8 -*-
{
    'name': 'Smart Cold-Chain Guardian',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Monitor cold-chain conditions, track telemetry, and prevent unsafe stock transfers',
    'description': """
        Smart Cold-Chain & Food Spoilage Guardian
        ========================================
        * Monitors temperature-sensitive inventory batches with live IoT telemetry feeds.
        * Tracks cold-chain health and logs thermal excursions in real-time.
        * Evaluates kinetic degradation and predicts dynamic shelf-life loss.
        * Watchdog cron jobs detect offline/unresponsive sensor loggers.
        * Prevents compromised lots from being validated or transferred.
    """,
    'author': 'Hackathon Team',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'stock',
        'mail',
        'web',
    ],
    'data': [
        # Security definitions & Access Rights
        'security/security_groups.xml',
        'security/ir.model.access.csv',

        # Configuration, Precision & Sequences
        'data/decimal_precision_data.xml',
        'data/sequence.xml',
        'data/cron_jobs.xml',

        # UI Views
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/spoilage_incident_views.xml',
        'views/telemetry_log_views.xml',
        'views/dashboard_views.xml',

        # Menus & Navigation (Loaded last so actions are already resolved)
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
