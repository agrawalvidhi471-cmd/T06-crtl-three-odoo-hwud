import os
import json
import logging

_logger = logging.getLogger(__name__)

class AIRemediationAdvisor:
    """
    Generates dynamic commercial & logistical remediation advice 
    for spoiled/degraded cold-chain lots using LLM reasoning.
    """

    SYSTEM_PROMPT = """
You are an expert Cold-Chain Logistics & Quality Assurance Advisor.
Analyze the provided batch excursion details and generate a concise, actionable 3-step decision plan for the operations team.

Your output should directly cover:
1. Risk Assessment: Immediate impact on safety and quality.
2. Recommended Action: Reroute to nearer hub, apply discount markdown, or scrap.
3. Logistics Command: Exact operational instructions for warehouse/driver.

Keep your response professional, bulleted, and concise (under 120 words).
"""

    @classmethod
    def generate_recommendation(cls, product_name: str, peak_temp: float, max_allowed_temp: float, 
                                duration_hours: float, remaining_quality_pct: float, 
                                current_location: str = "In Transit") -> str:
        """
        Calls LLM service to generate advice. Falls back to a deterministic 
        rules engine if API keys/network connections are unavailable during hackathon demo.
        """
        prompt_payload = f"""
- Product: {product_name}
- Peak Excursion Temp: {peak_temp}°C (Max Allowed: {max_allowed_temp}°C)
- Duration Outside Limits: {duration_hours} hours
- Post-Breach Quality Retention: {remaining_quality_pct}%
- Current Location: {current_location}
"""

        # Try API Call (e.g. OpenAI / Groq)
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": cls.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt_payload}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                _logger.warning(f"LLM API Call failed ({e}), falling back to Heuristic Engine.")

        # Fallback Heuristic Engine (Ensures 100% reliable demo without internet/API keys)
        return cls._fallback_heuristic_recommendation(
            product_name, peak_temp, max_allowed_temp, duration_hours, remaining_quality_pct
        )

    @staticmethod
    def _fallback_heuristic_recommendation(product_name: str, peak_temp: float, max_temp: float, 
                                             duration: float, quality_pct: float) -> str:
        """Rule-based backup output if offline."""
        if quality_pct <= 30.0 or (peak_temp - max_temp) > 12.0:
            return (
                f"🚨 **CRITICAL RISK DETECTED ({quality_pct}% Quality Remaining)**\n"
                f"• **Action Required:** SCRAP BATCH IMMEDIATELY.\n"
                f"• **Reason:** Thermal exposure ({peak_temp}°C for {duration}h) exceeded safety margins for {product_name}.\n"
                f"• **Logistics Order:** Quarantine batch upon arrival at next checkpoint. Do not release for consumer delivery."
            )
        elif quality_pct <= 70.0:
            return (
                f"⚠️ **MODERATE DEGRADATION ({quality_pct}% Quality Remaining)**\n"
                f"• **Action Required:** APPLY 35% MARKDOWN & REROUTE.\n"
                f"• **Reason:** Reduced shelf-life prevents long-distance transit.\n"
                f"• **Logistics Order:** Divert shipment to nearest fulfillment hub for immediate liquidation/flash sale."
            )
        else:
            return (
                f"✅ **MINOR EXCURSION ({quality_pct}% Quality Remaining)**\n"
                f"• **Action Required:** CONTINUE TRANSIT WITH QA FLAG.\n"
                f"• **Reason:** Quality remains above 70% threshold.\n"
                f"• **Logistics Order:** Proceed to target destination but prioritize first-out dispatching (FEFO)."
            )