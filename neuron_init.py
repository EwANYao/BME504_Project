"""
mrglike_myelinated_fiber.py

A runnable "MRG-style" myelinated axon model for NEURON (Python).
- Builds repeating node/paranode/juxtaparanode/internode structure.
- Uses Hodgkin-Huxley style mechanisms at nodes (as an approximation to full MRG),
  with adjusted conductances to better mimic high nodal excitability.
- Provides functions to attach a time-varying current waveform (Vector.play -> IClamp.i)
  and perform a binary-search threshold estimation (scale factor on waveform peak).

Notes:
- This is an MRG-inspired implementation for simulation and comparison.
- For publication-grade quantitative agreement with McIntyre et al. 2002,
  replace channel kinetics & densities with the original parameter set (ModelDB).
"""

import numpy as np
from neuron import h, gui
import matplotlib.pyplot as plt

h.load_file("stdrun.hoc")
h.celsius = 37.0
DT = 0.025  # ms simulation time step

# -------------------------
# Biophysical helper params
# -------------------------
DEFAULT_RA = 70.0   # ohm*cm
CM_NODE = 1.0       # uF/cm2
CM_INTERNODE = 0.02 # reduced to simulate myelin
E_LEAK = -80.0

# Nodal ionic densities (approximate, scaled HH-like)
# These are intentionally larger than classic squid-HH to mimic nodal excitability.
G_NA_BAR = 0.18   # S/cm2  (approx high sodium)
G_K_BAR  = 0.036  # S/cm2
G_LEAK_NODE = 0.0003

# Paranode and juxtaparanode passive properties
G_PAS_INTERN = 1e-5

# Geometry rules
def internode_length_from_diam(diam_um):
    # empirical: internode length ~ 100 * diameter (µm)
    return max(50.0, 100.0 * diam_um)

def node_length_um():
    return 1.0

def paranode_length_um(diam_um):
    # small paranode region
    return max(1.0, 3.0 * diam_um**0.5)

def juxta_length_um(diam_um):
    return max(5.0, 10.0 * (diam_um**0.5))

# -------------------------
# Build MRG-like fiber
# -------------------------
def make_MRG_fiber(diam_um=5.0, n_nodes=21):
    """
    Build a myelinated fiber with repeating sections:
    node_i - paranode_i - juxta_i - internode_i - ... - node_{i+1}
    Returns dict with lists: nodes, paranos, juxtas, interns
    Stimulate at central node index mid_idx = len(nodes)//2
    """
    nodes = []
    paranos = []
    juxtas = []
    interns = []

    # convert geometry; NEURON uses µm for L and diam
    for i in range(n_nodes):
        # Node
        nd = h.Section(name=f'node_{i}')
        nd.L = node_length_um()
        nd.diam = diam_um
        nd.Ra = DEFAULT_RA
        nd.nseg = 1
        nd.cm = CM_NODE
        nd.insert('hh')  # use hh as node mechanism (approximate)
        # scale hh conductances to approximate nodal densities
        try:
            nd.gnabar_hh = G_NA_BAR
            nd.gkbar_hh = G_K_BAR
            nd.gl_hh = G_LEAK_NODE
            nd.el_hh = E_LEAK
        except Exception:
            # some NEURON hh variants don't expose same names; fallback: set via mechanism
            pass
        nodes.append(nd)

        if i < n_nodes - 1:
            # Paranode
            pn = h.Section(name=f'paranode_{i}')
            pn.L = paranode_length_um(diam_um)
            pn.diam = diam_um
            pn.Ra = DEFAULT_RA
            pn.nseg = 1
            pn.cm = CM_INTERNODE  # reduced cm
            pn.insert('pas')
            pn.g_pas = G_PAS_INTERN
            pn.e_pas = E_LEAK
            paranos.append(pn)

            # Juxtaparanode
            jx = h.Section(name=f'juxta_{i}')
            jx.L = juxta_length_um(diam_um)
            jx.diam = diam_um
            jx.Ra = DEFAULT_RA
            jx.nseg = 1
            jx.cm = CM_INTERNODE
            jx.insert('pas')
            jx.g_pas = G_PAS_INTERN
            jx.e_pas = E_LEAK
            juxtas.append(jx)

            # Internode (myelinated)
            intern = h.Section(name=f'intern_{i}')
            intern.L = internode_length_from_diam(diam_um)
            intern.diam = diam_um
            intern.Ra = DEFAULT_RA
            intern.nseg = 1
            intern.cm = CM_INTERNODE
            intern.insert('pas')
            intern.g_pas = G_PAS_INTERN
            intern.e_pas = E_LEAK
            interns.append(intern)

    # connect sections in sequence:
    # node0(1) -- paranode0(0)
    # paranode0(1) -- juxta0(0)
    # juxta0(1) -- intern0(0)
    # intern0(1) -- node1(0)
    for i in range(len(nodes)-1):
        paranos[i].connect(nodes[i](1.0))
        juxtas[i].connect(paranos[i](1.0))
        interns[i].connect(juxtas[i](1.0))
        nodes[i+1].connect(interns[i](1.0))

    fiber = {
        'nodes': nodes,
        'paranos': paranos,
        'juxtas': juxtas,
        'interns': interns,
        'mid_idx': len(nodes)//2
    }
    return fiber

# -------------------------
# Stimulation utilities
# -------------------------
def attach_vector_stim(node_section, tvec_ms, ivec_nA):
    """
    Attach a time-varying current waveform to node_section(0.5) by playing Vector -> IClamp.i
    tvec_ms: 1D array-like of times in ms
    ivec_nA: 1D array-like of currents in nA (NEURON's point current units)
    Returns (stim, vt, vi) to keep references alive.
    """
    stim = h.IClamp(node_section(0.5))
    stim.delay = 0
    stim.dur = 1e9  # long because we'll override with Vector.play
    vt = h.Vector(list(tvec_ms))
    vi = h.Vector(list(ivec_nA))
    vi.play(stim._ref_i, vt, 1)  # play current (nA) into IClamp.i
    return stim, vt, vi

def record_section_v(section):
    vt = h.Vector()
    vv = h.Vector()
    vt.record(h._ref_t)
    vv.record(section(0.5)._ref_v)
    return vt, vv

def run_sim(tstop_ms):
    h.tstop = tstop_ms
    h.dt = DT
    h.finitialize(E_LEAK)
    h.run()

# -------------------------
# Threshold search
# -------------------------
def find_threshold(fiber, tvec_ms, base_waveform_nA, scale_lo=0.0, scale_hi=1000.0,
                   tol=1e-2, max_iters=20, record_node_index=None):
    """
    Binary-search threshold scale factor 's' such that s * base_waveform evokes a propagated AP.
    - fiber: dict from make_MRG_fiber
    - tvec_ms, base_waveform_nA: arrays (same length)
    - returns threshold scale factor (multiplicative on waveform)
    """
    nodes = fiber['nodes']
    mid = fiber['mid_idx']
    rec_idx = record_node_index if record_node_index is not None else (len(nodes)-1)  # record at distal node
    rec_t, rec_v = record_section_v(nodes[rec_idx])

    def test_scale(s):
        # Remove previous stimuli by creating a new stim each test (Vectors are local)
        stim, vt, vi = attach_vector_stim(nodes[mid], tvec_ms, (base_waveform_nA * s).tolist())
        run_sim(tvec_ms[-1] + 5.0)
        Vm = np.array(rec_v)
        # detect AP: simple threshold crossing (e.g., > 0 mV or > -20 mV)
        return Vm.max() > 0.0

    # Ensure hi evokes and lo does not
    if not test_scale(scale_hi):
        print("Warning: high scale did NOT evoke AP. Increase scale_hi.")
        return None
    if test_scale(scale_lo):
        return scale_lo

    lo, hi = scale_lo, scale_hi
    for it in range(max_iters):
        mid_s = 0.5*(lo+hi)
        ev = test_scale(mid_s)
        if ev:
            hi = mid_s
        else:
            lo = mid_s
        if (hi - lo) < tol:
            break
    return hi

# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    # Build fiber
    diameters = [2.0, 5.0, 8.0]  # µm
    results = {}
    for d in diameters:
        print(f"Building fiber diameter {d} µm ...")
        f = make_MRG_fiber(diam_um=d, n_nodes=31)
        # Construct a test waveform (nA units) - replace this with ETI-derived current waveform
        tvec = np.arange(0.0, 5.0, DT)  # ms
        base = np.zeros_like(tvec)
        # a 0.2 ms rectangular current at t=0.2 ms of amplitude 1 nA (use CC vs CV waveforms in practice)
        t_on = 0.2
        pw = 0.2
        base[(tvec >= t_on) & (tvec < t_on + pw)] = 1.0
        print("Searching threshold (scale factor on 1 nA base waveform)...")
        thr_scale = find_threshold(f, tvec, base, scale_lo=0.0, scale_hi=2000.0, tol=1e-1)
        results[d] = thr_scale
        print(f"Diameter {d} um -> threshold scale {thr_scale} (peak nA = {thr_scale*1.0} nA)")
    print("Results:", results)
