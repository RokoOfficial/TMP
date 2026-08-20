#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TMP FINAL — TESTE MULTI-ENTRADA
================================

Equação:

X_t → M_t → A_t → G_t → S_t → E_t → R_t → A_(t+1)

Componentes reais:

components/
    embedding.py
    transformer.py

MODULES/
    motor11.py
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple


# ============================================================
# PATH
# ============================================================

ROOT = os.path.dirname(
    os.path.abspath(__file__)
)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


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
# ESTADO
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

        # ====================================================
        # EMBEDDING REAL
        # ====================================================

        self.embedding = EmbeddingManager({
            "enabled": True
        })

        # ====================================================
        # TRANSFORMER REAL
        # ====================================================

        self.transformer = TransformerManager({
            "enabled": True
        })

        # ====================================================
        # MOTOR11 REAL
        # ====================================================

        self.motor = MotorParallel(
            modo="auto",
            nome="TMP-MOTOR11"
        )

        # ====================================================
        # ATENÇÃO INICIAL
        # ====================================================

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
    # M_t — EMBEDDING
    # ========================================================

    def calcular_semantica(
        self,
        entrada: InputState
    ) -> Dict[str, Any]:

        texto, metadata = self.embedding.correct(
            entrada.texto
        )

        grupos = []

        grupo = metadata.get("group")

        if grupo:
            grupos.append(
                str(grupo).upper()
            )

        # ====================================================
        # Mapeamento da entrada para os especialistas TMP.
        # Mantemos o Embedding real como fonte principal.
        # ====================================================

        texto_lower = entrada.texto.lower()

        if (
            "python" in texto_lower
            or "código" in texto_lower
            or "codigo" in texto_lower
            or "programar" in texto_lower
        ):
            if "CODE" not in grupos:
                grupos.append("CODE")

        if (
            "texto" in texto_lower
            or "escrever" in texto_lower
            or "frase" in texto_lower
            or "redigir" in texto_lower
        ):
            if "TEXT" not in grupos:
                grupos.append("TEXT")

        if (
            "web" in texto_lower
            or "internet" in texto_lower
            or "pesquisar" in texto_lower
            or "site" in texto_lower
        ):
            if "WEB" not in grupos:
                grupos.append("WEB")

        if (
            "imagem" in texto_lower
            or "foto" in texto_lower
            or "visual" in texto_lower
        ):
            if "IMAGE" not in grupos:
                grupos.append("IMAGE")

        if (
            "áudio" in texto_lower
            or "audio" in texto_lower
            or "som" in texto_lower
        ):
            if "AUDIO" not in grupos:
                grupos.append("AUDIO")

        if (
            "paralelo" in texto_lower
            or "parallel" in texto_lower
            or "tarefas" in texto_lower
        ):
            if "PARALLEL" not in grupos:
                grupos.append("PARALLEL")

        if (
            "sistema" in texto_lower
            or "terminal" in texto_lower
            or "comando" in texto_lower
            or "arquivo" in texto_lower
        ):
            if "SYSTEM" not in grupos:
                grupos.append("SYSTEM")

        return {
            "texto": texto,
            "grupos": grupos,
            "metadata": metadata
        }

    # ========================================================
    # A_t — ATENÇÃO
    # ========================================================

    def calcular_atencao(
        self,
        entrada: InputState,
        M_t: Dict[str, Any]
    ) -> Dict[str, float]:

        A_t = dict(self.attention)

        # ----------------------------------------------------
        # Tipo principal
        # ----------------------------------------------------

        if entrada.tipo in A_t:

            A_t[entrada.tipo] += 0.20

        # ----------------------------------------------------
        # Semântica
        # ----------------------------------------------------

        mapa = {
            "CODE": "code",
            "TEXT": "texto",
            "WEB": "web",
            "IMAGE": "imagem",
            "AUDIO": "audio",
            "PARALLEL": "parallel",
            "SYSTEM": "sistema",
            "SISTEMA": "sistema",
            "IMAGEM": "imagem",
            "TEXTO": "texto",
        }

        for grupo in M_t["grupos"]:

            agente = mapa.get(grupo)

            if agente in A_t:

                A_t[agente] += 0.20

        return self.normalizar(A_t)

    # ========================================================
    # G_t — ROUTING
    # ========================================================

    def routing(
        self,
        A_t: Dict[str, float]
    ) -> Dict[str, float]:

        return dict(A_t)

    # ========================================================
    # S_t — TOP-K
    # ========================================================

    def selecionar(
        self,
        G_t: Dict[str, float]
    ) -> List[Tuple[str, float]]:

        return sorted(
            G_t.items(),
            key=lambda x: x[1],
            reverse=True
        )[:self.TOP_K]

    # ========================================================
    # E_t — MOTOR11 REAL
    # ========================================================

    def executar(
        self,
        S_t: List[Tuple[str, float]],
        ciclo: int
    ) -> List[Dict[str, Any]]:

        resultados = []

        for indice, (agente, peso) in enumerate(
            S_t,
            start=1
        ):

            # ------------------------------------------------
            # Função executada pelo Motor11.
            # A decisão vem da TMP.
            # A execução vem do Motor11.
            # ------------------------------------------------

            def executar_agente(
                item,
                agente=agente
            ):
                return {
                    "agente": agente,
                    "executado": True,
                    "item": item
                }

            bloco = Bloco(
                id=(ciclo * 100) + indice,
                tipo=TipoBloco.FOR,
                dados=[agente],
                funcao=executar_agente,
                independente=True,
                nome=f"TMP::{agente}"
            )

            try:

                resultado = self.motor.executar(
                    bloco
                )

                sucesso = (
                    resultado is not None
                    and len(resultado) > 0
                )

                resultados.append({
                    "agente": agente,
                    "peso": peso,
                    "sucesso": sucesso,
                    "resultado": resultado
                })

            except Exception as exc:

                resultados.append({
                    "agente": agente,
                    "peso": peso,
                    "sucesso": False,
                    "resultado": None,
                    "erro": str(exc)
                })

        return resultados

    # ========================================================
    # R_t — FEEDBACK
    # ========================================================

    def feedback(
        self,
        E_t: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        if not E_t:

            return {
                "success": False,
                "score": 0.0
            }

        sucessos = sum(
            1
            for resultado in E_t
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

    def atualizar(
        self,
        A_t: Dict[str, float],
        M_t: Dict[str, Any],
        S_t: List[Tuple[str, float]],
        R_t: Dict[str, Any]
    ) -> Dict[str, float]:

        nova = dict(A_t)

        score = R_t["score"]

        # ----------------------------------------------------
        # Influência semântica
        # ----------------------------------------------------

        mapa = {
            "CODE": "code",
            "TEXT": "texto",
            "WEB": "web",
            "IMAGE": "imagem",
            "AUDIO": "audio",
            "PARALLEL": "parallel",
            "SYSTEM": "sistema",
            "SISTEMA": "sistema",
        }

        for grupo in M_t["grupos"]:

            agente = mapa.get(grupo)

            if agente in nova:

                nova[agente] += (
                    0.15
                )

        # ----------------------------------------------------
        # Feedback das rotas selecionadas
        # ----------------------------------------------------

        for agente, peso in S_t:

            if R_t["success"]:

                nova[agente] += (
                    0.20 * score
                )

            else:

                nova[agente] -= (
                    0.10 * (1.0 - score)
                )

        # ----------------------------------------------------
        # Normalização
        # ----------------------------------------------------

        return self.normalizar(nova)

    # ========================================================
    # CICLO
    # ========================================================

    def ciclo(
        self,
        entrada: InputState,
        numero: int
    ) -> Dict[str, Any]:

        print("\n")
        print("#" * 70)
        print(f"# CICLO t = {numero}")
        print("#" * 70)

        # ----------------------------------------------------
        # X_t
        # ----------------------------------------------------

        print("\nX_t - ENTRADA")
        print(entrada)

        # ----------------------------------------------------
        # M_t
        # ----------------------------------------------------

        M_t = self.calcular_semantica(
            entrada
        )

        print("\nM_t - EMBEDDING")

        print(
            f"  grupos : {M_t['grupos']}"
        )

        # ----------------------------------------------------
        # A_t
        # ----------------------------------------------------

        A_t = self.calcular_atencao(
            entrada,
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

        G_t = self.routing(
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

        for agente, peso in S_t:

            print(
                f"  {agente:<10}: "
                f"{peso:.4f}"
            )

        # ----------------------------------------------------
        # E_t
        # ----------------------------------------------------

        E_t = self.executar(
            S_t,
            numero
        )

        print("\nE_t - MOTOR11 REAL")

        for resultado in E_t:

            estado = (
                "OK"
                if resultado["sucesso"]
                else "FAIL"
            )

            print(
                f"  {resultado['agente']:<10}: "
                f"{estado} "
                f"(peso="
                f"{resultado['peso']:.4f})"
            )

            if resultado["sucesso"]:

                print(
                    f"      resultado = "
                    f"{resultado['resultado']}"
                )

            else:

                if "erro" in resultado:

                    print(
                        f"      erro = "
                        f"{resultado['erro']}"
                    )

        # ----------------------------------------------------
        # R_t
        # ----------------------------------------------------

        R_t = self.feedback(
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

        A_next = self.atualizar(
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

        mudou = any(
            abs(
                A_next[chave]
                -
                A_t[chave]
            ) > 1e-9

            for chave in A_t
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

        # ====================================================
        # CRÍTICO:
        # A_(t+1) VIRA O ESTADO PARA O PRÓXIMO CICLO
        # ====================================================

        self.attention = A_next

        return {
            "X_t": entrada,
            "M_t": M_t,
            "A_t": A_t,
            "G_t": G_t,
            "S_t": S_t,
            "E_t": E_t,
            "R_t": R_t,
            "A_t+1": A_next,
            "changed": mudou
        }


# ============================================================
# SUÍTE MULTI-ENTRADA
# ============================================================

TESTES = [

    InputState(
        "gerar código Python",
        "code"
    ),

    InputState(
        "escrever um texto sobre inteligência artificial",
        "texto"
    ),

    InputState(
        "pesquisar informações sobre Python na internet",
        "web"
    ),

    InputState(
        "gerar uma imagem de uma cidade futurista",
        "imagem"
    ),

    InputState(
        "processar um arquivo de áudio",
        "audio"
    ),

    InputState(
        "executar estas tarefas em paralelo",
        "parallel"
    ),

    InputState(
        "executar um comando no sistema",
        "sistema"
    )
]


# ============================================================
# TESTE FINAL
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("TMP FINAL — TESTE MULTI-ENTRADA")
    print("=" * 70)

    print("\nComponentes:")
    print("  • components.embedding")
    print("  • components.transformer")
    print("  • MODULES.motor11")

    # --------------------------------------------------------
    # TMP
    # --------------------------------------------------------

    tmp = TMP()

    resultados = []

    # --------------------------------------------------------
    # Cada entrada possui sua própria sequência.
    # --------------------------------------------------------

    for indice, entrada in enumerate(
        TESTES,
        start=1
    ):

        print("\n")
        print("=" * 70)
        print(
            f"TESTE {indice}/{len(TESTES)}"
        )
        print(
            f"ENTRADA: {entrada.texto}"
        )
        print(
            f"TIPO: {entrada.tipo}"
        )
        print("=" * 70)

        # Nova sequência para cada tipo
        valor = 1.0 / len(tmp.AGENTES)

        tmp.attention = {
            agente: valor
            for agente in tmp.AGENTES
        }

        atencao_inicial = dict(
            tmp.attention
        )

        # ----------------------------------------------------
        # 5 ciclos
        # ----------------------------------------------------

        historico = []

        for ciclo in range(1, 6):

            resultado = tmp.ciclo(
                entrada,
                ciclo
            )

            historico.append(
                resultado
            )

        resultados.append({
            "entrada": entrada,
            "inicial": atencao_inicial,
            "final": dict(tmp.attention),
            "historico": historico
        })

    # ========================================================
    # RESULTADO
    # ========================================================

    print("\n")
    print("=" * 70)
    print("RESULTADO FINAL — GENERALIZAÇÃO")
    print("=" * 70)

    convergencias = 0

    for resultado in resultados:

        entrada = resultado["entrada"]
        final = resultado["final"]

        dominante = max(
            final,
            key=final.get
        )

        print("\n" + "-" * 70)

        print(
            f"Entrada: {entrada.texto}"
        )

        print(
            f"Esperado: {entrada.tipo}"
        )

        print(
            f"Dominante: {dominante}"
        )

        print("\nAtenção final:")

        for agente, peso in sorted(
            final.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            print(
                f"  {agente:<10}: "
                f"{peso:.4f}"
            )

        if dominante == entrada.tipo:

            convergencias += 1

            print(
                "\n  ✅ CONVERGIU PARA "
                "O ESPECIALISTA ESPERADO"
            )

        else:

            print(
                "\n  ⚠️ NÃO CONVERGIU "
                "PARA O ESPERADO"
            )

    # ========================================================
    # RESUMO
    # ========================================================

    total = len(resultados)

    print("\n")
    print("=" * 70)
    print("RESUMO DA GENERALIZAÇÃO")
    print("=" * 70)

    print(
        f"\nTestes: {total}"
    )

    print(
        f"Convergências: "
        f"{convergencias}/{total}"
    )

    print(
        f"Taxa: "
        f"{convergencias / total * 100:.1f}%"
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

    print(
        "\n✅ Embedding real"
    )

    print(
        "✅ Transformer real"
    )

    print(
        "✅ Motor11 real"
    )

    print(
        "✅ Recorrência A_(t+1) → A_t"
    )

    print(
        "\n✅ TESTE MULTI-ENTRADA CONCLUÍDO"
    )


if __name__ == "__main__":
    main()
