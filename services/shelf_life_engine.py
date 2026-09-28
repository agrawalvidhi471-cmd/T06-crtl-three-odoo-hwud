import math
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ShelfLifeEngine:
    """
    Calculates dynamic quality loss and dynamic expiration dates 
    based on kinetic thermal degradation principles (Q10 rule).
    """

    @staticmethod
    def calculate_degradation(temp_c: float, target_max_temp: float, duration_hours: float, base_q10: float = 2.0) -> float:
        """
        Calculates quality loss percentage for a given temperature excursion.
        
        :param temp_c: Actual recorded temperature during breach (°C)
        :param target_max_temp: Maximum allowed safe temperature (°C)
        :param duration_hours: Duration of excursion in hours
        :param base_q10: Temperature coefficient factor (default 2.0)
        :return: Quality loss percentage (0.0 to 100.0)
        """
        if temp_c <= target_max_temp or duration_hours <= 0:
            return 0.0

        # Delta T above maximum threshold
        delta_t = temp_c - target_max_temp
        
        # Acceleration factor: Rate of spoilage doubles every 10°C elevation (Q10 rule)
        acceleration_factor = math.pow(base_q10, delta_t / 10.0)
        
        # Base decay rate per hour outside safe limits (1.5% loss per hour baseline * acceleration)
        base_decay_rate_per_hour = 1.5
        quality_loss_pct = duration_hours * base_decay_rate_per_hour * acceleration_factor
        
        return min(round(quality_loss_pct, 2), 100.0)

    @classmethod
    def recalculate_lot_shelf_life(cls, lot_record, peak_temp: float, excursion_hours: float):
        """
        Recalculates quality retention %, cumulative excursion mins, 
        and updates the dynamic expiration date on an Odoo stock.lot record.
        """
        if not lot_record:
            return

        # 1. Calculate quality loss
        quality_loss = cls.calculate_degradation(
            temp_c=peak_temp,
            target_max_temp=lot_record.temp_max_c,
            duration_hours=excursion_hours
        )

        # 2. Update remaining quality retention
        new_quality_pct = max(0.0, lot_record.quality_retention_pct - quality_loss)
        
        # 3. Calculate new dynamic expiration date based on quality retention ratio
        current_expiry = lot_record.dynamic_expiration_date or lot_record.original_expiration_date or datetime.now()
        
        if new_quality_pct <= 0:
            new_dynamic_expiry = datetime.now()
            new_health = 'compromised'
        else:
            # Shift expiration closer proportional to quality drop
            days_remaining = (current_expiry - datetime.now()).total_seconds() / 86400.0
            adjusted_days_remaining = days_remaining * (new_quality_pct / 100.0)
            new_dynamic_expiry = datetime.now() + timedelta(days=max(0, adjusted_days_remaining))
            
            # Health state mapping
            if new_quality_pct > 80:
                new_health = 'optimal'
            elif new_quality_pct > 50:
                new_health = 'warning'
            else:
                new_health = 'critical'

        # 4. Write back to Odoo lot
        excursion_mins_added = int(excursion_hours * 60)
        lot_record.write({
            'quality_retention_pct': new_quality_pct,
            'cumulative_excursion_minutes': lot_record.cumulative_excursion_minutes + excursion_mins_added,
            'dynamic_expiration_date': new_dynamic_expiry,
            'batch_health': new_health
        })

        _logger.info(
            f"[ShelfLifeEngine] Updated Lot {lot_record.name}: "
            f"Quality={new_quality_pct}%, Health={new_health}, Expiry={new_dynamic_expiry}"
        )