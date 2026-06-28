import json
from typing import Dict, Optional
from pydantic import BaseModel, Field
import google.generativeai as genai

from src import config

class VisaRule(BaseModel):
    passport_nationality: str = Field(description="The passport nationality, e.g., US")
    region_or_country: str = Field(description="The destination country or region (e.g., Schengen, United Kingdom)")
    max_days: int = Field(description="Maximum allowable days of stay")
    rolling_window_days: Optional[int] = Field(None, description="The rolling window size in days (e.g., 180 for Schengen), or null if per-entry")
    description: str = Field(description="Brief explanation of the stay limit")

class VisaRulesExtractor:
    def __init__(self):
        self.cache_file = config.VISA_RULES_FILE
        if not config.is_gemini_mocked():
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    def _load_cached_rules(self) -> list:
        if not self.cache_file.exists():
            return []
        try:
            with open(self.cache_file, "r") as f:
                data = json.load(f)
                return data.get("rules", [])
        except Exception:
            return []

    def _save_rule_to_cache(self, rule: VisaRule):
        rules = self._load_cached_rules()
        # Remove existing rule if it matches nationality and region to avoid duplicates
        rules = [
            r for r in rules
            if not (r["passport_nationality"].upper() == rule.passport_nationality.upper()
                    and r["region_or_country"].lower() == rule.region_or_country.lower())
        ]
        rules.append(rule.model_dump())
        
        try:
            with open(self.cache_file, "w") as f:
                json.dump({"rules": rules}, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to cache rule: {e}")

    def get_visa_rule(self, passport_nationality: str, region_or_country: str) -> VisaRule:
        """
        Get the visa rule for a specific passport nationality and region/country.
        Checks local cache first. If not found, calls Gemini (unless mocked) and caches it.
        """
        passport_upper = passport_nationality.upper()
        region_lower = region_or_country.lower()

        # 1. Check Cache
        cached_rules = self._load_cached_rules()
        for rule_data in cached_rules:
            if (rule_data.get("passport_nationality", "").upper() == passport_upper
                    and rule_data.get("region_or_country", "").lower() == region_lower):
                return VisaRule(**rule_data)

        # 2. Handle Mock Mode or Key Absence
        if config.is_gemini_mocked() or not self.model:
            print(f"Gemini API key not configured or placeholder detected. Generating mock rules for {passport_nationality} to {region_or_country}...")
            # Generate a default mock rule based on common visa rules
            mock_max_days = 90
            mock_window = None
            if "schengen" in region_lower:
                mock_max_days = 90
                mock_window = 180
            elif "united kingdom" in region_lower or "uk" in region_lower:
                mock_max_days = 180
                mock_window = 365
            elif "albania" in region_lower:
                mock_max_days = 365
                mock_window = 365

            rule = VisaRule(
                passport_nationality=passport_upper,
                region_or_country=region_or_country,
                max_days=mock_max_days,
                rolling_window_days=mock_window,
                description=f"Mock Visa Rule: {passport_upper} citizens can stay in {region_or_country} for up to {mock_max_days} days."
            )
            self._save_rule_to_cache(rule)
            return rule

        # 3. Call Gemini API
        prompt = f"""
        You are an international immigration law consultant.
        Determine the maximum stay duration and rolling window restrictions (if any) for a traveler with a passport from '{passport_upper}' visiting '{region_or_country}'.
        
        Provide the answer in raw JSON format with the following keys:
        - "passport_nationality": "{passport_upper}"
        - "region_or_country": "{region_or_country}"
        - "max_days": integer (e.g. 90, 180, 365)
        - "rolling_window_days": integer (e.g. 180 if a rolling limit like Schengen applies, or null if it resets per entry)
        - "description": "A brief explanation of the visa-free or tourist visa limits for this route."

        Return ONLY raw JSON, with no markdown code blocks, backticks, or other wrappers.
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            cleaned_text = response.text.strip()
            # In case the model wraps the output in code blocks despite instructions
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text.split("json")[-1].split("```")[0].strip()
            
            rule_data = json.loads(cleaned_text)
            rule = VisaRule(**rule_data)
            self._save_rule_to_cache(rule)
            return rule
        except Exception as e:
            print(f"Error querying Gemini: {e}. Falling back to default mock rule.")
            # Safety Fallback
            fallback_rule = VisaRule(
                passport_nationality=passport_upper,
                region_or_country=region_or_country,
                max_days=90,
                rolling_window_days=180 if "schengen" in region_lower else None,
                description=f"Fallback rule: Standard tourist allowance of 90 days."
            )
            return fallback_rule
