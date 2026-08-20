#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MOTOR PARALLEL V4.0.5 - VERSÃO FINAL ESTÁVEL
"""

import os
import sys
import time
import json
import heapq
import random
import threading
import queue as queue_lib
import subprocess
import multiprocessing
from dataclasses import dataclass, field
from typing import List, Any, Callable, Optional, Dict, Tuple, Union
from enum import Enum
from datetime import datetime
from collections import deque
import hashlib
import inspect

# ============================================
# 1. ENUMS
# ============================================

class TipoBloco(Enum):
    FOR = 'for'
    WHILE = 'while'
    IF = 'if'
    ELIF = 'elif'
    ELSE = 'else'
    TRY = 'try'
    BASH = 'bash'
    PYTHON = 'python'
    CUDA = 'cuda'

class EstrategiaTipo(Enum):
    SEQUENCIAL = 'sequencial'
    PARALELO_TOTAL = 'paralelo_total'
    PARALELO_PARCIAL = 'paralelo_parcial'
    BASH = 'bash'
    BASH_PARALELO = 'bash_paralelo'
    CUDA = 'cuda'
    CUDA_PARALELO = 'cuda_paralelo'
    MONITORADO = 'monitorado'

class StatusExecucao(Enum):
    PENDENTE = 'pendente'
    EXECUTANDO = 'executando'
    CONCLUIDO = 'concluido'
    FALHA = 'falha'
    CANCELADO = 'cancelado'
    TIMEOUT = 'timeout'

class TipoFila(Enum):
    FIFO = 'fifo'
    LIFO = 'lifo'
    PRIORIDADE = 'prioridade'
    DEADLINE = 'deadline'
    ROUND_ROBIN = 'round_robin'

# ============================================
# 2. EXCEÇÕES
# ============================================

class TaskTimeoutError(Exception):
    pass

class TaskCanceledError(Exception):
    pass

class TaskFailedError(Exception):
    pass

# ============================================
# 3. ESTRUTURAS
# ============================================

@dataclass
class Bloco:
    id: int
    tipo: TipoBloco
    dados: List[Any]
    funcao: Optional[Callable] = None
    independente: bool = True
    tamanho: int = 0
    complexidade: float = 0.0
    comando_bash: Optional[str] = None
    nome: str = ""
    timeout: float = 30.0
    prioridade: int = 5
    metadados: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.tamanho == 0 and self.dados:
            self.tamanho = len(self.dados)
        if not self.nome:
            self.nome = f"Bloco_{self.id}"

@dataclass
class ConfiguracaoFila:
    tipo: TipoFila = TipoFila.FIFO
    max_size: int = -1
    max_workers: int = 4
    timeout: float = 30.0
    retry_delay: float = 1.0
    max_retries: int = 3
    throttle_rate: int = 0
    batch_size: int = 1
    backoff_multiplier: float = 2.0

@dataclass
class Tarefa:
    id: int
    bloco: Bloco
    prioridade: int = 5
    deadline: Optional[float] = None
    tentativas: int = 0
    max_tentativas: int = 3
    status: StatusExecucao = StatusExecucao.PENDENTE
    resultado: Any = None
    erro: Optional[str] = None
    timestamp_criacao: float = field(default_factory=time.time)
    timestamp_inicio: float = 0.0
    timestamp_fim: float = 0.0
    fila_id: int = 0
    callback: Optional[Callable] = None

@dataclass
class Estrategia:
    tipo: EstrategiaTipo
    threads: int = 1
    chunk_size: int = 0
    usar_bash: bool = False
    usar_cuda: bool = False
    comando: Optional[str] = None
    motivo: str = ""

# ============================================
# 4. DETECTORES
# ============================================

class DetectorCUDA:
    @staticmethod
    def disponivel() -> bool:
        return False
    
    @staticmethod
    def recomendar(bloco: Bloco, recursos: Dict) -> Dict:
        return {'usar_cuda': False, 'motivo': 'CUDA não disponível'}

class DetectorBash:
    @staticmethod
    def detectar(bloco: Bloco, recursos: Dict) -> Dict:
        if bloco.tipo == TipoBloco.BASH and bloco.comando_bash:
            return {'usar_bash': True, 'tipo_bash': 'paralelo' if bloco.tamanho > 50 else 'sequencial', 'motivo': 'Bloco bash explícito'}
        return {'usar_bash': False, 'tipo_bash': None, 'motivo': 'Padrão: Python'}

# ============================================
# 5. MONITOR
# ============================================

class MonitorRecursos:
    def __init__(self):
        self.cores = multiprocessing.cpu_count()
    
    def monitorar(self) -> Dict:
        return {
            'cores': self.cores,
            'cpu_percent': 20,
            'cpu_livre': 80,
            'memoria_gb': 2.0,
            'carga_1min': 0.5
        }

# ============================================
# 6. MOTOR DE DECISÃO
# ============================================

class MotorDecisao:
    def __init__(self, modo='auto'):
        self.modo = modo
        self.monitor = MonitorRecursos()
        self._stats = {'python': 0, 'bash': 0, 'cuda': 0}
    
    def decidir(self, bloco: Bloco) -> Estrategia:
        recursos = self.monitor.monitorar()
        cores = recursos['cores']
        
        if bloco.tipo == TipoBloco.FOR and bloco.independente and bloco.funcao:
            if bloco.tamanho > 50:
                self._stats['python'] += 1
                threads = min(cores, max(1, bloco.tamanho // 50 + 1), 8)
                return Estrategia(
                    EstrategiaTipo.PARALELO_TOTAL,
                    threads=threads,
                    chunk_size=max(1, bloco.tamanho // threads),
                    motivo=f"Paralelo total: {bloco.tamanho} itens"
                )
            elif bloco.tamanho > 10:
                self._stats['python'] += 1
                threads = max(1, cores // 2)
                return Estrategia(
                    EstrategiaTipo.PARALELO_PARCIAL,
                    threads=threads,
                    chunk_size=max(1, bloco.tamanho // threads),
                    motivo=f"Paralelo parcial: {bloco.tamanho} itens"
                )
        
        self._stats['python'] += 1
        return Estrategia(
            EstrategiaTipo.SEQUENCIAL,
            threads=1,
            chunk_size=0,
            motivo="Sequencial"
        )

# ============================================
# 7. EXECUTOR
# ============================================

class Executor:
    def __init__(self, motor):
        self.motor = motor
        self._metricas = []
        self._tempo_total = 0
        self._resultados_cache = {}  # Cache de resultados por tarefa
    
    def _executar_estrategia(self, bloco: Bloco, estrategia: Estrategia, tarefa_id: int = None) -> List[Any]:
        from concurrent.futures import ThreadPoolExecutor
        
        if not bloco.funcao:
            return bloco.dados if bloco.dados else []
        
        if not bloco.dados:
            return []
        
        try:
            if estrategia.tipo == EstrategiaTipo.SEQUENCIAL:
                resultado = [bloco.funcao(item) for item in bloco.dados]
            elif estrategia.tipo in [EstrategiaTipo.PARALELO_TOTAL, EstrategiaTipo.PARALELO_PARCIAL]:
                with ThreadPoolExecutor(max_workers=estrategia.threads) as executor:
                    resultado = list(executor.map(bloco.funcao, bloco.dados))
            else:
                resultado = [bloco.funcao(item) for item in bloco.dados]
            
            # Cache do resultado
            if tarefa_id is not None:
                self._resultados_cache[tarefa_id] = resultado
            
            return resultado
                
        except Exception as e:
            print(f"⚠️ Erro ao executar bloco {bloco.id}: {e}")
            return []

# ============================================
# 8. FILAS
# ============================================

class FilaBase:
    def __init__(self, nome: str, config: ConfiguracaoFila, fila_id: int):
        self.nome = nome
        self.config = config
        self.fila_id = fila_id
        self._tarefas = []
        self._tarefas_concluidas = {}  # Cache de tarefas concluídas
        self._lock = threading.Lock()
        self._executor = None
        self._workers = []
        self._rodando = False
        self._stats = {
            'total_adicionadas': 0,
            'total_concluidas': 0,
            'total_falhas': 0,
            'total_canceladas': 0,
            'total_timeouts': 0,
            'total_retries': 0
        }
    
    def set_executor(self, executor):
        self._executor = executor
    
    def adicionar(self, tarefa: Tarefa):
        raise NotImplementedError
    
    def obter_proxima(self) -> Optional[Tarefa]:
        raise NotImplementedError
    
    def cancelar(self, tarefa_id: int) -> bool:
        with self._lock:
            for i, t in enumerate(self._tarefas):
                if t.id == tarefa_id and t.status in [StatusExecucao.PENDENTE]:
                    t.status = StatusExecucao.CANCELADO
                    self._tarefas.pop(i)
                    self._stats['total_canceladas'] += 1
                    return True
        return False
    
    def obter_resultado(self, tarefa_id: int) -> Any:
        """Obtém resultado de uma tarefa concluída"""
        with self._lock:
            if tarefa_id in self._tarefas_concluidas:
                return self._tarefas_concluidas[tarefa_id]
        return None
    
    def iniciar(self):
        if self._rodando or not self._executor:
            return
        self._rodando = True
        for i in range(self.config.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(f"worker_{self.fila_id}_{i}",),
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
    
    def _worker_loop(self, worker_id: str):
        while self._rodando:
            try:
                tarefa = self.obter_proxima()
                if tarefa is None:
                    time.sleep(0.01)
                    continue
                
                if tarefa.deadline and time.time() > tarefa.deadline:
                    tarefa.status = StatusExecucao.TIMEOUT
                    self._stats['total_timeouts'] += 1
                    continue
                
                tarefa.status = StatusExecucao.EXECUTANDO
                tarefa.timestamp_inicio = time.time()
                
                try:
                    estrategia = self._executor.motor.motor_decisao.decidir(tarefa.bloco)
                    resultado = self._executor._executar_estrategia(tarefa.bloco, estrategia, tarefa.id)
                    tarefa.resultado = resultado if resultado is not None else []
                    tarefa.status = StatusExecucao.CONCLUIDO
                    self._stats['total_concluidas'] += 1
                    
                    # Armazena no cache de concluídas
                    with self._lock:
                        self._tarefas_concluidas[tarefa.id] = tarefa.resultado
                    
                    if tarefa.callback:
                        try:
                            tarefa.callback(tarefa)
                        except Exception as e:
                            print(f"⚠️ Callback: {e}")
                            
                except Exception as e:
                    tarefa.erro = str(e)
                    tarefa.tentativas += 1
                    self._stats['total_retries'] += 1
                    
                    if tarefa.tentativas < tarefa.max_tentativas:
                        tarefa.status = StatusExecucao.PENDENTE
                        time.sleep(self.config.retry_delay)
                        self.adicionar(tarefa)
                    else:
                        tarefa.status = StatusExecucao.FALHA
                        self._stats['total_falhas'] += 1
                
                tarefa.timestamp_fim = time.time()
                
            except Exception as e:
                print(f"❌ Erro worker: {e}")
                time.sleep(1)
    
    def get_status(self) -> Dict:
        with self._lock:
            return {
                'nome': self.nome,
                'fila_id': self.fila_id,
                'tipo': self.config.tipo.value,
                'tamanho': len(self._tarefas),
                'workers_ativos': len([w for w in self._workers if w.is_alive()]),
                'max_workers': self.config.max_workers,
                'concluidas': self._stats['total_concluidas'],
                'stats': self._stats.copy()
            }

class FilaFIFO(FilaBase):
    def __init__(self, nome, config, fila_id):
        super().__init__(nome, config, fila_id)
        self._fila = deque()
    
    def adicionar(self, tarefa: Tarefa):
        with self._lock:
            self._fila.append(tarefa)
            self._stats['total_adicionadas'] += 1
    
    def obter_proxima(self) -> Optional[Tarefa]:
        with self._lock:
            if self._fila:
                return self._fila.popleft()
        return None

class FilaPrioridade(FilaBase):
    def __init__(self, nome, config, fila_id):
        super().__init__(nome, config, fila_id)
        self._heap = []
        self._contador = 0
    
    def adicionar(self, tarefa: Tarefa):
        with self._lock:
            heapq.heappush(self._heap, (tarefa.prioridade, self._contador, tarefa))
            self._contador += 1
            self._stats['total_adicionadas'] += 1
    
    def obter_proxima(self) -> Optional[Tarefa]:
        with self._lock:
            if self._heap:
                _, _, tarefa = heapq.heappop(self._heap)
                return tarefa
        return None

class FilaDeadline(FilaBase):
    def __init__(self, nome, config, fila_id):
        super().__init__(nome, config, fila_id)
        self._heap = []
        self._contador = 0
    
    def adicionar(self, tarefa: Tarefa):
        with self._lock:
            if tarefa.deadline is None:
                tarefa.deadline = time.time() + self.config.timeout
            heapq.heappush(self._heap, (tarefa.deadline, self._contador, tarefa))
            self._contador += 1
            self._stats['total_adicionadas'] += 1
    
    def obter_proxima(self) -> Optional[Tarefa]:
        with self._lock:
            if self._heap:
                deadline, _, tarefa = heapq.heappop(self._heap)
                if time.time() > deadline:
                    tarefa.status = StatusExecucao.TIMEOUT
                    self._stats['total_timeouts'] += 1
                    return None
                return tarefa
        return None

# ============================================
# 9. GERENCIADOR DE FILAS
# ============================================

class GerenciadorFilas:
    def __init__(self):
        self._filas: Dict[int, FilaBase] = {}
        self._proximo_fila_id = 0
        self._proximo_tarefa_id = 0
        self._lock = threading.Lock()
        self._executor = None
    
    def set_executor(self, executor):
        self._executor = executor
        for fila in self._filas.values():
            fila.set_executor(executor)
    
    def criar_fila(self, nome: str, config: ConfiguracaoFila) -> int:
        with self._lock:
            fila_id = self._proximo_fila_id
            self._proximo_fila_id += 1
            
            if config.tipo == TipoFila.PRIORIDADE:
                fila = FilaPrioridade(nome, config, fila_id)
            elif config.tipo == TipoFila.DEADLINE:
                fila = FilaDeadline(nome, config, fila_id)
            else:
                fila = FilaFIFO(nome, config, fila_id)
            
            if self._executor:
                fila.set_executor(self._executor)
            
            self._filas[fila_id] = fila
            return fila_id
    
    def adicionar_tarefa(self, fila_id: int, bloco: Bloco, 
                         prioridade: int = 5, deadline: Optional[float] = None,
                         callback: Optional[Callable] = None) -> int:
        if fila_id not in self._filas:
            raise ValueError(f"Fila {fila_id} não existe")
        
        with self._lock:
            tarefa_id = self._proximo_tarefa_id
            self._proximo_tarefa_id += 1
        
        tarefa = Tarefa(
            id=tarefa_id,
            bloco=bloco,
            prioridade=prioridade,
            deadline=deadline,
            max_tentativas=self._filas[fila_id].config.max_retries,
            fila_id=fila_id,
            callback=callback
        )
        
        self._filas[fila_id].adicionar(tarefa)
        self._filas[fila_id].iniciar()
        return tarefa_id
    
    def obter_resultado(self, tarefa_id: int) -> Any:
        """Obtém resultado de uma tarefa de qualquer fila"""
        for fila in self._filas.values():
            resultado = fila.obter_resultado(tarefa_id)
            if resultado is not None:
                return resultado
        return None
    
    def get_status(self) -> Dict:
        status = {'total_filas': len(self._filas), 'filas': {}}
        for fila_id, fila in self._filas.items():
            status['filas'][fila_id] = fila.get_status()
        return status

# ============================================
# 10. MOTOR PARALLEL
# ============================================

class MotorParallel:
    def __init__(self, modo='auto', nome='MotorParallel'):
        self.nome = nome
        self.modo = modo
        self._versao = '4.0.5'
        self._inicializado = datetime.now()
        self._tarefas_ativas = {}
        self._lock = threading.Lock()
        
        self.motor_decisao = MotorDecisao(modo)
        self.executor = Executor(self)
        self.gerenciador_filas = GerenciadorFilas()
        self.gerenciador_filas.set_executor(self.executor)
        
        print(f"\n{'='*70}")
        print(f"🚀 {self.nome} - Versão {self._versao}")
        print(f"📅 Inicializado em: {self._inicializado.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⚙️ Modo: {modo.upper()}")
        print(f"🧠 Cores: {multiprocessing.cpu_count()}")
        print(f"{'='*70}\n")
    
    def criar_fila(self, nome: str, config: Optional[ConfiguracaoFila] = None) -> int:
        if config is None:
            config = ConfiguracaoFila()
        config.max_workers = min(config.max_workers, multiprocessing.cpu_count())
        fila_id = self.gerenciador_filas.criar_fila(nome, config)
        self.gerenciador_filas.set_executor(self.executor)
        return fila_id
    
    def submit(self, bloco: Bloco, fila_id: Optional[int] = None, 
               prioridade: int = 5, deadline: Optional[float] = None,
               callback: Optional[Callable] = None) -> int:
        if fila_id is None:
            if 0 not in self.gerenciador_filas._filas:
                fila_id = self.criar_fila('default')
            else:
                fila_id = 0
        
        tarefa_id = self.gerenciador_filas.adicionar_tarefa(
            fila_id, bloco, prioridade, deadline, callback
        )
        
        with self._lock:
            self._tarefas_ativas[tarefa_id] = {
                'id': tarefa_id,
                'fila_id': fila_id,
                'status': StatusExecucao.PENDENTE,
                'timestamp': time.time()
            }
        
        return tarefa_id
    
    def aguardar(self, tarefa_id: int, timeout: Optional[float] = None) -> Any:
        inicio = time.time()
        while True:
            if timeout and time.time() - inicio > timeout:
                raise TaskTimeoutError(f"Tarefa {tarefa_id} timeout")
            
            # Tenta obter resultado do cache
            resultado = self.gerenciador_filas.obter_resultado(tarefa_id)
            if resultado is not None:
                return resultado
            
            # Verifica status nas filas
            for fila in self.gerenciador_filas._filas.values():
                with fila._lock:
                    for tarefa in fila._tarefas:
                        if tarefa.id == tarefa_id:
                            if tarefa.status == StatusExecucao.FALHA:
                                raise TaskFailedError(f"Tarefa {tarefa_id} falhou: {tarefa.erro}")
                            elif tarefa.status == StatusExecucao.CANCELADO:
                                raise TaskCanceledError(f"Tarefa {tarefa_id} cancelada")
                            elif tarefa.status == StatusExecucao.TIMEOUT:
                                raise TaskTimeoutError(f"Tarefa {tarefa_id} timeout")
            
            time.sleep(0.05)
    
    def status_filas(self) -> Dict:
        return self.gerenciador_filas.get_status()
    
    def executar(self, bloco: Bloco) -> List[Any]:
        estrategia = self.motor_decisao.decidir(bloco)
        return self.executor._executar_estrategia(bloco, estrategia)
    
    def gerar_relatorio(self) -> Dict:
        print("\n" + "=" * 70)
        print("📊 RELATÓRIO DE EXECUÇÃO - MOTOR PARALLEL V4")
        print("=" * 70)
        
        print("\n📈 RESUMO:")
        print(f"   Filas: {len(self.gerenciador_filas._filas)}")
        print(f"   Tarefas ativas: {len(self._tarefas_ativas)}")
        
        print("\n📋 FILAS:")
        status = self.status_filas()
        for fila_id, fila_info in status['filas'].items():
            print(f"\n   Fila {fila_info['nome']} (ID: {fila_id}):")
            print(f"      Tipo: {fila_info['tipo']}")
            print(f"      Tamanho: {fila_info['tamanho']}")
            print(f"      Workers: {fila_info['workers_ativos']}/{fila_info['max_workers']}")
            print(f"      Concluídas: {fila_info.get('concluidas', 0)}")
            print(f"      Stats: {fila_info['stats']}")
        
        print("\n📊 DECISÕES:")
        stats = self.motor_decisao._stats
        print(f"   Python: {stats['python']}")
        print(f"   Bash: {stats['bash']}")
        print(f"   CUDA: {stats['cuda']}")
        
        return {'status': 'ok'}
    
    def get_info(self) -> Dict:
        return {
            'nome': self.nome,
            'versao': self._versao,
            'modo': self.modo,
            'cores': multiprocessing.cpu_count(),
            'filas': len(self.gerenciador_filas._filas),
            'stats_decisoes': self.motor_decisao._stats
        }

# ============================================
# 11. EXEMPLO
# ============================================

def exemplo_filas():
    print("\n" + "=" * 70)
    print("📚 EXEMPLO: MOTOR PARALLEL COM FILAS")
    print("=" * 70)
    
    motor = MotorParallel(modo='auto', nome='MotorFilas')
    
    fila_alta = motor.criar_fila('alta_prioridade', ConfiguracaoFila(
        tipo=TipoFila.PRIORIDADE,
        max_workers=4
    ))
    
    fila_batch = motor.criar_fila('batch', ConfiguracaoFila(
        tipo=TipoFila.FIFO,
        max_workers=2
    ))
    
    fila_urgente = motor.criar_fila('urgente', ConfiguracaoFila(
        tipo=TipoFila.DEADLINE,
        max_workers=8,
        timeout=2.0
    ))
    
    print(f"\n✅ Filas criadas:")
    print(f"   • alta_prioridade (ID: {fila_alta})")
    print(f"   • batch (ID: {fila_batch})")
    print(f"   • urgente (ID: {fila_urgente})")
    
    dados = list(range(50))
    
    bloco1 = Bloco(
        id=1,
        tipo=TipoBloco.FOR,
        dados=dados[:20],
        funcao=lambda x: x * 2,
        nome="Multiplica por 2"
    )
    
    bloco2 = Bloco(
        id=2,
        tipo=TipoBloco.FOR,
        dados=dados,
        funcao=lambda x: x ** 2,
        nome="Quadrado"
    )
    
    bloco3 = Bloco(
        id=3,
        tipo=TipoBloco.FOR,
        dados=dados[:10],
        funcao=lambda x: x + 10,
        nome="Soma 10"
    )
    
    print("\n📤 Submetendo tarefas...")
    
    tarefa1 = motor.submit(bloco1, fila_id=fila_alta, prioridade=0)
    print(f"   ✅ Tarefa 1 (prioridade 0) na fila alta")
    
    tarefa2 = motor.submit(bloco2, fila_id=fila_batch, prioridade=5)
    print(f"   ✅ Tarefa 2 (prioridade 5) na fila batch")
    
    tarefa3 = motor.submit(bloco3, fila_id=fila_urgente, deadline=time.time() + 5.0)
    print(f"   ✅ Tarefa 3 (deadline 5s) na fila urgente")
    
    print("\n⏳ Aguardando conclusão...")
    
    try:
        r1 = motor.aguardar(tarefa1, timeout=10.0)
        print(f"   ✅ Tarefa 1: {len(r1)} resultados")
        print(f"      Amostra: {r1[:5]}")
    except Exception as e:
        print(f"   ❌ Tarefa 1: {e}")
    
    try:
        r2 = motor.aguardar(tarefa2, timeout=10.0)
        print(f"   ✅ Tarefa 2: {len(r2)} resultados")
        print(f"      Amostra: {r2[:5]}")
    except Exception as e:
        print(f"   ❌ Tarefa 2: {e}")
    
    try:
        r3 = motor.aguardar(tarefa3, timeout=6.0)
        print(f"   ✅ Tarefa 3: {len(r3)} resultados")
        print(f"      Amostra: {r3[:5]}")
    except Exception as e:
        print(f"   ❌ Tarefa 3: {e}")
    
    motor.gerar_relatorio()
    return motor

# ============================================
# 12. MAIN
# ============================================

def main():
    print("\n" + "=" * 70)
    print("🧠 MOTOR PARALLEL V4.0.5 - VERSÃO FINAL ESTÁVEL")
    print("🚀 COM FILAS INTELIGENTES")
    print("=" * 70)
    
    motor = exemplo_filas()
    
    info = motor.get_info()
    print("\n" + "=" * 70)
    print("📊 INFORMAÇÕES FINAIS")
    print("=" * 70)
    for chave, valor in info.items():
        print(f"   {chave.replace('_', ' ').title()}: {valor}")
    print("=" * 70)
    print("\n✅ Demonstração concluída!")

if __name__ == "__main__":
    main()
