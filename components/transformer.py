#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TRANSFORMER MANAGER - Heurístico com Pesos
==========================================
Gerencia transformer heurístico com pesos e atenção.

Author: Agent Smith Team
Version: 3.0.0
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from utils.helpers import load_json


class TransformerManager:
    """Gerenciador do transformer heurístico"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        
        # Carrega padrões com pesos
        self.patterns = load_json("data/patterns.json")
        self.history = []
        self.learned = []
        
        self.total_attempts = 0
        self.total_success = 0
    
    def correct(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Corrige usando transformer heurístico"""
        self.total_attempts += 1
        
        # Ordena por peso (maior primeiro = atenção)
        sorted_patterns = sorted(self.patterns, key=lambda x: x.get("weight", 0), reverse=True)
        
        for pattern_data in sorted_patterns:
            pattern = pattern_data.get("pattern", "")
            correction = pattern_data.get("correction", "")
            weight = pattern_data.get("weight", 0.5)
            
            if re.search(pattern, text, re.IGNORECASE):
                corrected = re.sub(pattern, correction, text, flags=re.IGNORECASE)
                self.total_success += 1
                self.history.append({
                    "original": text,
                    "corrected": corrected,
                    "weight": weight
                })
                return corrected, {
                    "corrected": True,
                    "weight": weight,
                    "attention": "high" if weight > 0.85 else "medium" if weight > 0.70 else "low"
                }
        
        return text, {"corrected": False}
    
    def learn(self, original: str, corrected: str, weight: float = 0.5) -> bool:
        """Aprende novo padrão"""
        pattern = re.escape(original[:20]) if len(original) > 20 else re.escape(original)
        
        for p in self.patterns:
            if p.get("pattern") == pattern:
                return False
        
        self.patterns.append({"pattern": pattern, "correction": corrected, "weight": weight})
        self.learned.append({"original": original, "corrected": corrected, "weight": weight})
        return True
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas"""
        rate = (self.total_success / max(1, self.total_attempts) * 100)
        return {
            "enabled": self.enabled,
            "patterns": len(self.patterns),
            "attempts": self.total_attempts,
            "success": self.total_success,
            "success_rate": rate,
            "learned": len(self.learned)
        }
