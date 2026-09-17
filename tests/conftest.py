"""
conftest.py — Fixtures compartilhadas para toda a suite de testes.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

# Adiciona a raiz do projeto ao path para que os scripts sejam importáveis
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixtures de dados ──────────────────────────────────────────────────────────
