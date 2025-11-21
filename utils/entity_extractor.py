import re
import json
from typing import Dict, List, Optional

class TeslaEntityExtractor:
    
    def __init__(self):
        # Vehicle models
        self.vehicles = {
            'model_3': [r'model\s*3', r'\bm3\b', r'model3'],
            'model_s': [r'model\s*s\b', r'models(?!\w)'],
            'model_x': [r'model\s*x', r'modelx\b', r'\bmx\b'],
            'model_y': [r'model\s*y', r'modely\b', r'\bmy\b'],
            'cybertruck': [r'cybertruck', r'cyber\s*truck'],
            'roadster': [r'roadster'],
            'semi': [r'semi(?:\s+truck)?']
        }
        
        # Energy products
        self.energy_products = {
            'powerwall': [r'powerwall', r'\bpw2\b', r'\bpw3\b'],
            'powerwall_2': [r'powerwall\s*2', r'\bpw2\b'],
            'powerwall_3': [r'powerwall\s*3', r'\bpw3\b'],
            'solar_panels': [r'solar\s+panel', r'solar\s+array', r'\bpv\s+panel'],
            'solar_roof': [r'solar\s+roof', r'solar\s+tiles?'],
            'megapack': [r'megapack'],
            'megawatt': [r'megawatt'],
            'supercharger': [r'supercharger', r'\bsc\s+v[234]', r'super\s+charger']
        }
        
        # Issues/topics (critical for anomaly detection)
        self.issues = {
            'recall': [r'\brecall', r'\btsb\b', r'service\s+bulletin'],
            'fire': [r'\bfire', r'\bburn(?:ing)?', r'flame', r'combustion', r'ignit'],
            'accident': [r'accident', r'crash', r'collision', r'wreck'],
            'safety': [r'safety\s+(?:issue|concern|hazard)', r'dangerous', r'hazard'],
            'service': [r'service\s+center', r'mobile\s+service', r'repair\s+(?:shop|center)'],
            'warranty': [r'warranty', r'out\s+of\s+warranty', r'extended\s+warranty'],
            'battery_issue': [r'battery\s+(?:degradation|issue|problem|fail)', r'range\s+loss'],
            'autopilot': [r'autopilot', r'\bfsd\b', r'full\s+self[\s-]driving'],
            'charging_issue': [r'charging\s+(?:issue|problem|error)', r'won\'?t\s+charge', r'charging\s+fail'],
            'inspection_failure': [r'inspection\s+fail', r'failed\s+inspection', r'nyserda']
        }
    
    def extract_entities(self, text: str) -> Dict:
        """Extract all entities from text
        
        Args:
            text: Combined title + selftext
            
        Returns:
            Dict with vehicles, energy_products, and issues lists
        """
        if not text:
            return {'vehicles': [], 'energy_products': [], 'issues': []}
            
        text_lower = text.lower()
        
        entities = {
            'vehicles': [],
            'energy_products': [],
            'issues': []
        }
        
        # Extract vehicles
        for vehicle, patterns in self.vehicles.items():
            if any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in patterns):
                if vehicle not in entities['vehicles']:
                    entities['vehicles'].append(vehicle)
        
        # Extract energy products
        for product, patterns in self.energy_products.items():
            if any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in patterns):
                if product not in entities['energy_products']:
                    entities['energy_products'].append(product)
        
        # Extract issues
        for issue, patterns in self.issues.items():
            if any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in patterns):
                if issue not in entities['issues']:
                    entities['issues'].append(issue)
        
        return entities
    
    def get_primary_product(self, entities: Dict) -> Optional[str]:
        """Determine primary product mentioned
        
        Priority: energy products > vehicles > None
        
        Args:
            entities: Dict from extract_entities()
            
        Returns:
            Primary product name or None
        """
        # Priority: energy > vehicles
        if entities['energy_products']:
            return entities['energy_products'][0]
        elif entities['vehicles']:
            return entities['vehicles'][0]
        else:
            return None
    
    def analyze_text(self, text: str) -> Dict:
        """Convenience method to extract entities and primary product
        
        Args:
            text: Combined title + selftext
            
        Returns:
            Dict with entities and primary_product
        """
        entities = self.extract_entities(text)
        primary_product = self.get_primary_product(entities)
        
        return {
            'entities': entities,
            'primary_product': primary_product
        }


# Test function
if __name__ == "__main__":
    extractor = TeslaEntityExtractor()
    
    test_cases = [
        "My Model 3 Powerwall isn't charging after recall",
        "Tesla Recalls Powerwall 2 AC Battery Systems Due to Fire and Burn Hazards",
        "solar panel failed NYSERDA inspection - anyone else?",
        "FSD almost caused an accident with my Model Y",
        "Supercharger V3 charging issues at Downtown location"
    ]
    
    for text in test_cases:
        result = extractor.analyze_text(text)
        print(f"\nText: {text}")
        print(f"Entities: {result['entities']}")
        print(f"Primary: {result['primary_product']}")