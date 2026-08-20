#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DEEPSEEK MANAGER - LLM Integration
===================================
Gerencia chamadas ao DeepSeek Coder via OpenAI 0.28.0.

Author: Agent Smith Team
Version: 3.0.0
"""

import os
import time
from typing import Dict, Any, Optional, Tuple

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class DeepSeekManager:
    """Gerenciador do DeepSeek Coder"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.model = config.get("model", "deepseek-coder")
        self.api_base = config.get("api_base", "https://api.deepseek.com/v1")
        
        self.total_requests = 0
        self.total_time = 0.0
        
        if not OPENAI_AVAILABLE:
            self.enabled = False
            print("⚠️ OpenAI 0.28.0 não instalado")
        
        if not os.environ.get("DEEPSEEK_API_KEY"):
            self.enabled = False
            print("⚠️ DEEPSEEK_API_KEY não configurada")
        
        if self.enabled:
            openai.api_key = os.environ.get("DEEPSEEK_API_KEY")
            openai.api_base = self.api_base
    
    def correct(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Corrige usando DeepSeek Coder"""
        if not self.enabled:
            return text, {"corrected": False, "error": "DeepSeek desabilitado"}
        
        start = time.time()
        self.total_requests += 1
        
        try:
            prompt = f"""
            Você é um especialista em HMP. Corrija a sintaxe:
            
            Original: {text}
            
            Regras: CALL comando WITH parametro, SET variavel, GET variavel
            
            Responda APENAS com a linha corrigida.
            """
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Especialista em HMP"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            corrected = response.choices[0].message.content.strip()
            elapsed = time.time() - start
            self.total_time += elapsed
            
            if corrected != text:
                return corrected, {"corrected": True, "time": elapsed}
            else:
                return text, {"corrected": False, "time": elapsed}
                
        except Exception as e:
            elapsed = time.time() - start
            self.total_time += elapsed
            return text, {"corrected": False, "error": str(e)}
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas"""
        return {
            "enabled": self.enabled,
            "model": self.model,
            "requests": self.total_requests,
            "total_time": self.total_time,
            "avg_time": self.total_time / max(1, self.total_requests)
        }
