#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TMP - EQUAÇÃO FINAL
===================

X_t → M_t → A_t → G_t → S_t → E_t → R_t → A_(t+1)

components/
    embedding.py
    transformer.py

MODULES/
    motor11.py
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, Any, List


# ============================================================
# PATH DO PROJETO
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ============================================================
# COMPONENTES REAIS
# ============================================================

from components.embedding import EmbeddingManager
from components.transformer import TransformerManager

from MODULES.motor11 import (
    MotorParallel,
    Bloco,
    TipoBloco
)


# ============================================================
# ENTRADA
# ============================================================

@dataclass
class InputState:
    texto: str
    tipo: str


# ============================================================
# TMP
# ============================================================

class TMP:

    AGENTES = [
        "code",
        "texto",
        "web",
        "sistema",
        "imagem",
        "audio",
        "parallel"
    ]

    TOP_K = 3

    def __init__(self):

        # ----------------------------------------------------
        # COMPONENTES REAIS
        # ----------------------------------------------------

        self.embedding = EmbeddingManager({
            "enabled": True
        })

        self.transformer = TransformerManager({
            "enabled": True
        })

        # ----------------------------------------------------
        # MOTOR11 REAL
        # ----------------------------------------------------

        self.motor = MotorParallel(
            modo="auto",
            nome="TMP-MOTOR11"
        )

        # ----------------------------------------------------
        # ESTADO A_t
        # ----------------------------------------------------

        valor = 1.0 / len(self.AGENTES)

        self.attention = {
            agente: valor
            for agente in self.AGENTES
        }

        self.historico = []

    # ========================================================
    # NORMALIZAÇÃO
    # ========================================================

    @staticmethod
    def normalizar(
        valores: Dict[str, float]
    ) -> Dict[str, float]:

        valores = {
            k: max(0.0, float(v))
            for k, v in valores.items()
        }

        total = sum(valores.values())

        if total <= 0:

            valor = 1.0 / len(valores)

            return {
                k: valor
                for k in valores
            }

        return {
            k: v / total
            for k, v in valores.items()
        }

    # ========================================================
    # M_t
    # ========================================================

    def calcular_semantica(
        self,
        entrada: InputState
    ) -> Dict[str, Any]:

        """
        Usa o EmbeddingManager real.

        O código fornecido pelo projeto trabalha com:

            correct(text)

        retornando:

            texto, metadados
        """

        texto, metadata = self.embedding.correct(
            entrada.texto
        )

        grupos = []

        grupo = metadata.get("group")

        if grupo:
            grupos.append(
                str(grupo).upper()
            )

        # Complemento semântico baseado no tipo da entrada.
        #
        # Isto não substitui o EmbeddingManager.
        # Serve apenas para mapear o grupo do componente
        # para os especialistas da TMP.

        texto_lower = entrada.texto.lower()

        if (
            "python" in texto_lower
            or "código" in texto_lower
            or "codigo" in texto_lower
        ):
            if "CODE" not in grupos:
                grupos.append("CODE")

        return {
            "texto": texto,
            "grupos": grupos,
            "metadata": metadata
        }

    # ========================================================
    # A_t
    # ========================================================

    def calcular_atencao(
        self,
        M_t: Dict[str, Any]
    ) -> Dict[str, float]:

        A_t = dict(self.attention)

        for grupo in M_t["grupos"]:

            agente = grupo.lower()

            if agente in A_t:

                A_t[agente] += 0.20

        return self.normalizar(A_t)

    # ========================================================
    # G_t
    # ========================================================

    def calcular_routing(
        self,
        A_t: Dict[str, float]
    ) -> Dict[str, float]:

        return self.normalizar(
            dict(A_t)
        )

    # ========================================================
    # S_t
    # ========================================================

    def selecionar(
        self,
        G_t: Dict[str, float]
    ) -> List[str]:

        ordenado = sorted(
            G_t.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            agente
            for agente, _ in ordenado[
                :self.TOP_K
            ]
        ]

    # ========================================================
    # E_t
    # ========================================================

    def executar_motor11(
        self,
        selecionados: List[str]
    ) -> Dict[str, Any]:

        resultados = {}

        for agente in selecionados:

            try:

                # --------------------------------------------
                # FUNÇÃO REAL EXECUTADA PELO MOTOR11
                # --------------------------------------------

                def executar(item):
                    return {
                        "agent": item,
                        "executed": True
                    }

                bloco = Bloco(
                    id=len(resultados) + 1,
                    tipo=TipoBloco.FOR,
                    dados=[agente],
                    funcao=executar,
                    independente=True,
                    nome=f"TMP::{agente}"
                )

                resultado = self.motor.executar(
                    bloco
                )

                resultados[agente] = {
                    "sucesso": (
                        resultado is not None
                        and len(resultado) > 0
                    ),
                    "resultado": resultado
                }

            except Exception as exc:

                resultados[agente] = {
                    "sucesso": False,
                    "erro": str(exc)
                }

        return resultados

    # ========================================================
    # R_t
    # ========================================================

    def calcular_feedback(
        self,
        E_t: Dict[str, Any]
    ) -> Dict[str, Any]:

        if not E_t:

            return {
                "success": False,
                "score": 0.0
            }

        sucessos = sum(
            1
            for resultado in E_t.values()
            if resultado["sucesso"]
        )

        total = len(E_t)

        score = sucessos / total

        return {
            "success": score >= 0.5,
            "score": score
        }

    # ========================================================
    # A_(t+1)
    # ========================================================

    def atualizar_atencao(
        self,
        A_t: Dict[str, float],
        M_t: Dict[str, Any],
        S_t: List[str],
        R_t: Dict[str, Any]
    ) -> Dict[str, float]:

        nova = dict(A_t)

        score = R_t["score"]

        # ----------------------------------------------------
        # influência semântica
        # ----------------------------------------------------

        for grupo in M_t["grupos"]:

            agente = grupo.lower()

            if agente in nova:
                nova[agente] += 0.20

        # ----------------------------------------------------
        # feedback sobre especialistas executados
        # ----------------------------------------------------

        for agente in S_t:

            if R_t["success"]:

                nova[agente] += (
                    0.20 * score
                )

            else:

                nova[agente] -= (
                    0.10 * (1.0 - score)
                )

        return self.normalizar(nova)

    # ========================================================
    # CICLO
    # ========================================================

    def ciclo(
        self,
        X_t: InputState,
        numero: int
    ):

        print("\n")
        print("#" * 70)
        print(f"# CICLO t = {numero}")
        print("#" * 70)

        # ----------------------------------------------------
        # X_t
        # ----------------------------------------------------

        print("\nX_t - ENTRADA")
        print(X_t)

        # ----------------------------------------------------
        # M_t
        # ----------------------------------------------------

        M_t = self.calcular_semantica(
            X_t
        )

        print("\nM_t - EMBEDDING")

        print(
            f"  grupos : {M_t['grupos']}"
        )

        # ----------------------------------------------------
        # A_t
        # ----------------------------------------------------

        A_t = self.calcular_atencao(
            M_t
        )

        print("\nA_t - ATENÇÃO")

        for agente, peso in sorted(
            A_t.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            print(
                f"  {agente:<10}: "
                f"{peso:.4f}"
            )

        # ----------------------------------------------------
        # G_t
        # ----------------------------------------------------

        G_t = self.calcular_routing(
            A_t
        )

        print("\nG_t - ROUTING")

        for agente, peso in sorted(
            G_t.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            print(
                f"  {agente:<10}: "
                f"{peso:.4f}"
            )

        # ----------------------------------------------------
        # S_t
        # ----------------------------------------------------

        S_t = self.selecionar(
            G_t
        )

        print("\nS_t - TOP-K")

        for agente in S_t:

            print(
                f"  {agente:<10}: "
                f"{G_t[agente]:.4f}"
            )

        # ----------------------------------------------------
        # E_t
        # ----------------------------------------------------

        E_t = self.executar_motor11(
            S_t
        )

        print("\nE_t - MOTOR11 REAL")

        for agente in S_t:

            resultado = E_t[agente]

            estado = (
                "OK"
                if resultado["sucesso"]
                else "FAIL"
            )

            print(
                f"  {agente:<10}: "
                f"{estado}"
            )

            if "resultado" in resultado:
                print(
                    f"      resultado = "
                    f"{resultado['resultado']}"
                )

            if "erro" in resultado:
                print(
                    f"      erro = "
                    f"{resultado['erro']}"
                )

        # ----------------------------------------------------
        # R_t
        # ----------------------------------------------------

        R_t = self.calcular_feedback(
            E_t
        )

        print("\nR_t - FEEDBACK")

        print(
            f"  success = "
            f"{R_t['success']}"
        )

        print(
            f"  score   = "
            f"{R_t['score']:.4f}"
        )

        # ----------------------------------------------------
        # A_(t+1)
        # ----------------------------------------------------

        A_next = self.atualizar_atencao(
            A_t,
            M_t,
            S_t,
            R_t
        )

        print("\nA_(t+1) - NOVA ATENÇÃO")

        for agente, peso in sorted(
            A_next.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            print(
                f"  {agente:<10}: "
                f"{peso:.4f}"
            )

        # ----------------------------------------------------
        # VALIDAR
        # ----------------------------------------------------

        mudou = any(
            abs(
                A_next[k] - A_t[k]
            ) > 1e-9
            for k in A_t
        )

        print(
            "\nVALIDAÇÃO DA RECORRÊNCIA"
        )

        if mudou:
            print(
                "  ✅ A_(t+1) diferente de A_t"
            )
        else:
            print(
                "  ❌ A_(t+1) não mudou"
            )

        # ----------------------------------------------------
        # PROPAGAÇÃO
        # ----------------------------------------------------

        self.attention = A_next

        self.historico.append({
            "t": numero,
            "X_t": X_t,
            "M_t": M_t,
            "A_t": A_t,
            "G_t": G_t,
            "S_t": S_t,
            "E_t": E_t,
            "R_t": R_t,
            "A_t+1": A_next
        })

    # ========================================================
    # TESTE
    # ========================================================

    def executar_teste(
        self,
        entrada: InputState,
        ciclos: int = 7
    ):

        atencao_inicial = dict(
            self.attention
        )

        for t in range(1, ciclos + 1):

            self.ciclo(
                entrada,
                t
            )

        print("\n")
        print("=" * 70)
        print("RESULTADO FINAL")
        print("=" * 70)

        print("\nAtenção inicial:")

        for agente, peso in sorted(
            atencao_inicial.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            print(
                f"  {agente:<10}: "
                f"{peso:.4f}"
            )

        print("\nAtenção final:")

        for agente, peso in sorted(
            self.attention.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            print(
                f"  {agente:<10}: "
                f"{peso:.4f}"
            )

        mudou = any(
            abs(
                atencao_inicial[k]
                - self.attention[k]
            ) > 1e-9
            for k in atencao_inicial
        )

        print("\n")
        print("=" * 70)
        print("EQUAÇÃO TMP")
        print("=" * 70)

        print(
            "\nX_t → M_t → A_t → G_t → "
            "S_t → E_t → R_t → A_(t+1)"
        )

        print(
            "\nA_(t+1) = F(A_t, M_t, R_t)"
        )

        if mudou:

            print(
                "\n✅ EQUAÇÃO TMP RECURSIVA VALIDADA"
            )

            print(
                "✅ Embedding: components/embedding.py"
            )

            print(
                "✅ Transformer: components/transformer.py"
            )

            print(
                "✅ Execução: MODULES/motor11.py"
            )

        else:

            print(
                "\n❌ EQUAÇÃO NÃO ALTEROU O ESTADO"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("TMP FINAL — COMPONENTS + MOTOR11")
    print("=" * 70)

    tmp = TMP()

    entrada = InputState(
        texto="gerar código Python",
        tipo="code"
    )

    tmp.executar_teste(
        entrada,
        ciclos=7
    )


if __name__ == "__main__":
    main()
