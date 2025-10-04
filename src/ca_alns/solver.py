# src/ca_alns/solver.py
from __future__ import annotations

from typing import Any, Optional
import importlib

###############################################################################
# Esnek import yardımcıları
###############################################################################

def _try_import(path: str, name: str) -> Optional[Any]:
    """
    path.modül içinden 'name' sembolünü yüklemeyi dener.
    Bulamazsa None döner (farklı paket hiyerarşetleriyle uyum için).
    """
    try:
        mod = importlib.import_module(path)
    except Exception:
        return None
    return getattr(mod, name, None)


def try_import_screens():
    """
    SafetyFirstScreen / PenaltyOnlyScreen için tipik yolları sırayla dener.
    Geriye (SafetyFirstScreen, PenaltyOnlyScreen) döndürür (None olabilir).
    """
    candidates = [
        ("ca_alns.connectivity", "SafetyFirstScreen"),
        ("ca_alns.screening", "SafetyFirstScreen"),
        ("ca_alns.screens", "SafetyFirstScreen"),
        ("ca_alns.core", "SafetyFirstScreen"),
    ]
    safety = None
    for p, n in candidates:
        safety = _try_import(p, n)
        if safety is not None:
            break

    candidates = [
        ("ca_alns.connectivity", "PenaltyOnlyScreen"),
        ("ca_alns.screening", "PenaltyOnlyScreen"),
        ("ca_alns.screens", "PenaltyOnlyScreen"),
        ("ca_alns.core", "PenaltyOnlyScreen"),
    ]
    penalty = None
    for p, n in candidates:
        penalty = _try_import(p, n)
        if penalty is not None:
            break

    return safety, penalty


def try_import_default_ops():
    """
    default_alns_operators() için tipik yolları dener.
    """
    candidates = [
        ("ca_alns.operators", "default_alns_operators"),
        ("ca_alns.alns", "default_alns_operators"),
        ("ca_alns.core", "default_alns_operators"),
    ]
    for p, n in candidates:
        fn = _try_import(p, n)
        if fn is not None:
            return fn
    return None


def try_import_run_alns():
    """
    run_alns(...) için tipik yolları dener.
    """
    candidates = [
        ("ca_alns.alns", "run_alns"),
        ("ca_alns.core", "run_alns"),
        ("ca_alns.runner", "run_alns"),
    ]
    for p, n in candidates:
        fn = _try_import(p, n)
        if fn is not None:
            return fn
    return None


def try_import_run_evolutionary():
    """
    run_evolutionary(...) için tipik yolları dener.
    """
    candidates = [
        ("baselines.evolution", "run_evolutionary"),
        ("baselines.core", "run_evolutionary"),
        ("baselines", "run_evolutionary"),
        ("ca_alns.baselines", "run_evolutionary"),
    ]
    for p, n in candidates:
        fn = _try_import(p, n)
        if fn is not None:
            return fn
    return None


###############################################################################
# Yardımcı: Rally operatörünü aç/kapa (geriye dönük uyum)
###############################################################################

def _toggle_rally(ops: Any, enable: bool) -> None:
    """
    ops nesnesinde rally-point’i aç/kapatır.
    - enable_rally/disable_rally metodları varsa onları kullanır.
    - Yoksa use_rally_points özniteliğini set etmeyi dener.
    Sessiz hataya toleranslıdır (yoksa geçer).
    """
    try:
        if enable and hasattr(ops, "enable_rally"):
            ops.enable_rally()
            return
        if (not enable) and hasattr(ops, "disable_rally"):
            ops.disable_rally()
            return
    except Exception:
        pass

    # Fallback: bayrak
    try:
        if hasattr(ops, "use_rally_points"):
            setattr(ops, "use_rally_points", bool(enable))
    except Exception:
        pass


###############################################################################
# Ana API
###############################################################################

def solve(
    inst: Any,
    algo: str,
    E_max: int,
    T_max: Optional[float],
    rho: float,
    v_max: float,
    connectivity_mode: str = "safety",
    rally_enabled: bool = True,
) -> dict:
    """
    Makaledeki yama ile uyumlu giriş noktası.

    Parametreler
    -----------
    inst : herhangi
        Problem örneği (depot, targets, uavs vb. içerir).
    algo : {"ga","de","ca-alns","alns-std","alns-ls", ...}
        Algoritma seçimi. "ga"/"de" evrimsel rotaya yönlenir.
    E_max : int
        Değerlendirme bütçesi (eşit bütçe karşılaştırma için).
    T_max : float | None
        Duvar saati sınırı; None ise sınırsız.
    rho : float
        Sıkılaştırma payı (R-ρ) için.
    v_max : float
        Maksimum hız (kadans bağında ve/veya tarama tarafında).
    connectivity_mode : {"safety","penalty"}
        "safety": tightened margin + surrogate+BFS + cadence (SafetyFirstScreen)
        "penalty": yalnızca ceza temelli (PenaltyOnlyScreen)
    rally_enabled : bool
        Rally-point operatörünü aç/kapat.

    Dönüş
    -----
    dict
        Çalışan çözücünün döndürdüğü sonuç sözlüğü (JSON-uyumlu).
    """
    # Erişim fonksiyonlarını topla
    SafetyFirstScreen, PenaltyOnlyScreen = try_import_screens()
    default_alns_operators = try_import_default_ops()
    run_alns = try_import_run_alns()
    run_evolutionary = try_import_run_evolutionary()

    if default_alns_operators is None or run_alns is None:
        raise ImportError(
            "ALNS çalıştırma için gerekli fonksiyonlar bulunamadı: "
            "default_alns_operators veya run_alns çözümlenemedi. "
            "Lütfen modül yollarını kontrol edin."
        )

    if algo in ("ga", "de"):
        if run_evolutionary is None:
            raise ImportError(
                "Evrimsel rota (GA/DE) için run_evolutionary bulunamadı. "
                "Baselines modüllerinin import yollarını kontrol edin."
            )
        # Evrimsel taraf (screen/ops parametreleri kullanmayabilir)
        return run_evolutionary(inst, algo=algo, E_max=E_max, T_max=T_max)

    # Bağlanırlık ekranı seçimi
    if connectivity_mode == "safety":
        if SafetyFirstScreen is None:
            raise ImportError(
                "SafetyFirstScreen bulunamadı; connectivity_mode='safety' kullanılamıyor. "
                "Bağlı modülleri kontrol edin ya da 'penalty' deneyin."
            )
        screen = SafetyFirstScreen(rho=rho, v_max=v_max)
    else:
        # penalty-only
        if PenaltyOnlyScreen is None:
            # Son çare: boş/dummy screen
            class _DummyPenaltyScreen:
                def __init__(self, *a, **k): ...
            screen = _DummyPenaltyScreen()
        else:
            screen = PenaltyOnlyScreen()

    # Operatör seti ve rally toggling
    ops = default_alns_operators()
    _toggle_rally(ops, rally_enabled)

    # Çekirdek ALNS yürütme
    result = run_alns(inst, ops=ops, screen=screen, E_max=E_max, T_max=T_max)
    return result
