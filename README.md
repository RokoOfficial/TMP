# TMP

**TMP** is an experimental Python prototype for a recurrent, adaptive task-routing architecture that combines **Transformer-style attention**, **Mixture of Experts (MoE)** selection, and **parallel execution**. It models an input-processing cycle in which execution feedback influences the attention state used by the next cycle.

> **Project status:** This repository is an experimental research prototype. The current embedding and attention components are heuristic implementations; they are not trained neural embedding, Transformer, or MoE models. The included validation records experimental behavior only and does not establish general convergence, stability, or performance guarantees. [1]

## Architecture

The project formalizes the following recurrent pipeline:

```text
X_t → M_t → A_t → G_t → S_t → E_t → R_t → A_(t+1)
```

```text
A_(t+1) = F(A_t, M_t, R_t)
```

| Symbol | Role in the prototype |
|---|---|
| `X_t` | Current input. |
| `M_t` | Heuristic semantic representation. |
| `A_t` | Current attention or relevance state. |
| `G_t` | Routing distribution derived from attention. |
| `S_t` | Top-K expert selection. |
| `E_t` | Execution of the selected experts. |
| `R_t` | Execution outcome and feedback. |
| `A_(t+1)` | Updated attention state for the next cycle. |

The architectural intent is to keep routing and execution separate: the TMP loop assigns relevance and selects specialists, while Motor11 executes the selected work. [1]

## Repository layout

| Path | Purpose |
|---|---|
| `MODULES/motor11.py` | MotorParallel V4.0.5 execution engine, including queues, scheduling, and parallel worker execution. |
| `VALIDATOR/DECEPTRON.py` | Compact single-input validation example for the TMP cycle. |
| `VALIDATOR/DECEPTRONv2.py` | Multi-input validation script that exercises seven task categories over recurrent cycles. |
| `components/embedding.py` | Heuristic semantic grouping component. |
| `components/transformer.py` | Pattern- and weight-based heuristic attention component. |
| `components/deepseek.py` | Optional DeepSeek Coder integration through the legacy `openai` client. |
| `DOC/TMP_EQUACAO_ANALISE_E_VALIDACAO.md` | Original Portuguese technical analysis and validation notes. |

## Prerequisites

The core source uses Python 3. The optional DeepSeek component additionally needs a compatible `openai` package and the `DEEPSEEK_API_KEY` environment variable.

> **Important:** This repository snapshot does not include `utils/helpers.py`, `data/embeddings.json`, or `data/patterns.json`, although `components/embedding.py` and `components/transformer.py` import or load them. The TMP validation examples require those support files to be restored or implemented before they can run successfully.

## Quick start

Clone the repository and enter its directory:

```bash
git clone https://github.com/RokoOfficial/TMP.git
cd TMP
```

The standalone Motor11 example can be run directly:

```bash
python MODULES/motor11.py
```

After the missing `utils/` and `data/` support files are available, execute the TMP validators from the repository root. Setting `PYTHONPATH` ensures that the root-level modules can be imported:

```bash
PYTHONPATH=. python VALIDATOR/DECEPTRON.py
PYTHONPATH=. python VALIDATOR/DECEPTRONv2.py
```

## Optional DeepSeek integration

`components/deepseek.py` is disabled by default. If you decide to use it, install the compatible client package and supply the API key through the environment rather than committing it to the repository:

```bash
export DEEPSEEK_API_KEY="your_api_key"
```

Do not store credentials in source files, documentation, or commits.

## License

This project is released under the [Apache License 2.0](LICENSE).

## References

[1]: [TMP architecture, formalization, and validation notes](DOC/TMP_EQUACAO_ANALISE_E_VALIDACAO.md)
