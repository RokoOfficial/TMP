#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EMBEDDING MANAGER - Semântico
==============================
Gerencia embeddings semânticos para correção rápida.

Author: Agent Smith Team
Version: 3.0.0
"""

import re
import json
from typing import Dict, Any, Optional, Tuple
from functools import lru_cache
from utils.helpers import load_json


class EmbeddingManager:
    """Gerenciador de embeddings semânticos"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        
        # Carrega dados
        self.groups = load_json("data/embeddings.json")
        
        self.cache_hits = 0
        self.total_queries = 0
    
    @lru_cache(maxsize=128)
    def _cached_lookup(self, word: str) -> Optional[str]:
        """Busca em cache"""
        for group, words in self.groups.items():
            if word.upper() in [w.upper() for w in words]:
                return group
        return None
    
    def correct(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Corrige usando embedding semântico"""
        match = re.match(r'@(\w+)', text)
        if not match:
            return text, {"corrected": False}
        
        self.total_queries += 1
        word = match.group(1).upper()
        group = self._cached_lookup(word)
        
        if not group:
            return text, {"corrected": False}
        
        self.cache_hits += 1
        rest = text[match.end():].strip()
        
        corrections = {
            "LOG": f'CALL log.info WITH message={rest}',
            "RUN": f'CALL system.exec WITH command={rest}',
            "CALC": f'CALL math.sum WITH a={rest} AS resultado',
            "SET": f'SET {rest}',
            "GET": f'GET {rest}'
        }
        
        if group in corrections:
            return corrections[group], {"corrected": True, "group": group}
        
        return text, {"corrected": False}
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas"""
        return {
            "enabled": self.enabled,
            "groups": len(self.groups),
            "words": sum(len(v) for v in self.groups.values()),
            "queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_rate": (self.cache_hits / max(1, self.total_queries) * 100)
        }
