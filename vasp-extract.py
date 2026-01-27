#!/usr/bin/env python3
"""
Extract energy + structure analysis from VASP calculations.

Outputs:
1. CSV file - All data (energy, composition, lattice parameters, etc.)
2. Pickle file - Structure objects only (lookup dictionary)

NO API required.

Usage: python extract_vasp_complete.py <base_path>

Example:
  python extract_vasp_complete.py /work/fb526710/complex_borides/no_Al
"""
import sys
import pickle
from pathlib import Path

def extract_energy(outcar_path):
    """Extract final energy from OUTCAR file."""
    try:
        with open(outcar_path, 'r') as f:
            for line in reversed(f.readlines()):
                if 'energy  without entropy' in line:
                    return float(line.split()[6])
    except:
        pass
    return None

def analyze_structure(poscar_path):
    """
    Analyze structure from POSCAR/CONTCAR using pymatgen.
    Returns: (Structure object, analysis dict)
    """
    try:
        from pymatgen.core import Structure
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        
        # Load structure
        struct = Structure.from_file(str(poscar_path))
        
        # Symmetry analysis (local computation, no API)
        sga = SpacegroupAnalyzer(struct, symprec=0.1)
        
        # Extract composition
        composition = {str(el): struct.composition[el] for el in struct.composition.elements}
        
        # Collect analysis data
        analysis = {
            'composition': composition,
           # 'space_group': sga.get_space_group_symbol(),
           # 'space_group_number': sga.get_space_group_number(),
            'crystal_system': sga.get_crystal_system(),
           # 'point_group': sga.get_point_group_symbol(),
            'lattice_a': struct.lattice.a,
            'lattice_b': struct.lattice.b,
            'lattice_c': struct.lattice.c,
            'lattice_alpha': struct.lattice.alpha,
            'lattice_beta': struct.lattice.beta,
            'lattice_gamma': struct.lattice.gamma,
            'volume': struct.lattice.volume,
            'density': struct.density,
            'num_sites': len(struct.sites)
        }
        
        return struct, analysis
        
    except ImportError:
        print("\nERROR: pymatgen not installed")
        print("Install with: pip install --user pymatgen")
        sys.exit(1)
    except Exception as e:
        return None, None

def main():
    
    # Parse Arguments:
    if len(sys.argv) < 2:
        print("Usage: python extract_vasp_complete.py <base_path>")
        print("\nExample:")
        print("  python extract_vasp_complete.py /work/fb*****/complex_borides/no_Al")
        sys.exit(1)
    
    base_path = Path(sys.argv[1]).resolve()
    output_csv = base_path / f"{base_path.name}_complete.csv"
    output_pickle = base_path / f"{base_path.name}_structures.pkl"
    
    if not base_path.exists():
        print(f"ERROR: Path does not exist: {base_path}")
        sys.exit(1)
    
    
    print("_" * 90)
    print("COMPLETE VASP ENERGY EXTRACTOR")
    print("_" * 90)
    print(f"Input path:      {base_path}")
    print(f"CSV output:      {output_csv}")
    print(f"Pickle output:   {output_pickle}")
    print(f"Strategy:        Prefer static > relaxation")
    print(f"Analysis:        Energy + Structure (no API)")
    print("-" * 90)
    
    
    # Find All Structure Folders:
    structures = {}
    
    for folder in base_path.iterdir():
        if not folder.is_dir():
            continue
        
        has_static = (folder / 'static').exists()
        has_relax = (folder / 'relaxation').exists()
        
        if has_static or has_relax:
            structures[folder.name] = {
                'static': folder / 'static' if has_static else None,
                'relax': folder / 'relaxation' if has_relax else None
            }
    
    if not structures:
        print("\nERROR: No structures found with static/ or relaxation/ folders")
        print(f"\nCheck your folder structure:")
        print(f"  ls -ld {base_path}/*/static {base_path}/*/relaxation")
        sys.exit(1)
    
    print(f"\nFound {len(structures)} structures\n")
    
    # ________________________
    results = []
    all_elements = set()
    
    for name in sorted(structures.keys()):
        data = structures[name]
        
        # Find energy and source folder (prefer static)
        energy = None
        calc_type = None
        source_folder = None
        
        # Try static first
        if data['static']:
            outcar = data['static'] / 'OUTCAR'
            if outcar.exists():
                energy = extract_energy(outcar)
                if energy is not None:
                    source_folder = data['static']
                    calc_type = 'static'
        
        # Fall back to relaxation
        if energy is None and data['relax']:
            outcar = data['relax'] / 'OUTCAR'
            if outcar.exists():
                energy = extract_energy(outcar)
                if energy is not None:
                    source_folder = data['relax']
                    calc_type = 'relaxation'
        
        if energy is None:
            print(f"✗ {name:<40} (no energy found)")
            continue
        
        # Analyze structure from same folder (prefer CONTCAR > POSCAR)
        struct_obj = None
        struct_info = None
        
        for filename in ['CONTCAR', 'POSCAR']:
            poscar = source_folder / filename
            if poscar.exists() and poscar.stat().st_size > 0:
                struct_obj, struct_info = analyze_structure(poscar)
                if struct_info:
                    break
        
        if not struct_info:
            print(f"✗ {name:<40} (structure analysis failed)")
            continue
        
        # Process composition
        comp = struct_info['composition']
        all_elements.update(comp.keys())
        
        num_atoms = sum(comp.values())
        energy_per_atom = energy / num_atoms if num_atoms > 0 else 0
        
        # Store all data
        result = {
            'structure_name': name,
            'structure_object': struct_obj,
            'composition': comp,
            'num_atoms': int(num_atoms),
            'total_energy_eV': energy,
            'energy_per_atom_eV': energy_per_atom,
           # 'space_group': struct_info['space_group'],
           # 'space_group_number': struct_info['space_group_number'],
            'crystal_system': struct_info['crystal_system'],
           # 'point_group': struct_info['point_group'],
            'lattice_a': struct_info['lattice_a'],
            'lattice_b': struct_info['lattice_b'],
            'lattice_c': struct_info['lattice_c'],
            'lattice_alpha': struct_info['lattice_alpha'],
            'lattice_beta': struct_info['lattice_beta'],
            'lattice_gamma': struct_info['lattice_gamma'],
            'volume': struct_info['volume'],
            'density': struct_info['density'],
	        'calc_type': calc_type
        }
        
        results.append(result)
        
        # Print progress
        comp_str = ' '.join([f"{el}{int(comp[el])}" for el in sorted(comp.keys())])
        symbol = '✓' if calc_type == 'static' else '⚠'
        print(f"{symbol} {name:<35} {energy:>12.6f} eV  {comp_str:<20}  "
              f"{result['space_group']:<12} [{calc_type.upper()}]")
    
    if not results:
        print("\nERROR: No data could be extracted")
        sys.exit(1)
    
    # save .csv file:

    sorted_elements = sorted(all_elements)
    
    with open(output_csv, 'w') as f:
        # Header
        header = (
    ['structure_name'] + 
        sorted_elements + 
        ['num_atoms', 'total_energy_eV', 'energy_per_atom_eV',
        'space_group', 'crystal_system', 'point_group',
        'lattice_a', 'lattice_b', 'lattice_c',
        'lattice_alpha', 'lattice_beta', 'lattice_gamma',
        'volume', 'density', 'calc_type']
    )
    f.write(','.join(header) + '\n')
        
        # Data rows
    for r in results:
            row = [r['structure_name']]
            row += [str(int(r['composition'].get(el, 0))) for el in sorted_elements]
            row += [
                str(r['num_atoms']),
                f"{r['total_energy_eV']:.8f}",
                f"{r['energy_per_atom_eV']:.8f}",
#                r['space_group'],
#                str(r['space_group_number']),
                r['crystal_system'],
#                r['point_group'],
                f"{r['lattice_a']:.6f}",
                f"{r['lattice_b']:.6f}",
                f"{r['lattice_c']:.6f}",
                f"{r['lattice_alpha']:.3f}",
                f"{r['lattice_beta']:.3f}",
                f"{r['lattice_gamma']:.3f}",
                f"{r['volume']:.6f}",
                f"{r['density']:.6f}",
	        str(r['calc_type'])
            ]
            f.write(','.join(row) + '\n')
    
    # save pickle file

    structure_dict = {r['structure_name']: r['structure_object'] for r in results}
    
    with open(output_pickle, 'wb') as f:
        pickle.dump(structure_dict, f)
    

    print(f"DONE! \n")
    print(f"Extracted:  {len(results)} structures")
    print(f"Elements:   {', '.join(sorted_elements)}")
    print(f"\n✓ CSV saved:    {output_csv}")
    print(f"  Contains:     Energy, composition, lattice parameters, symmetry")
    print(f"\n✓ Pickle saved: {output_pickle}")
    print(f"  Contains:     Structure objects (pymatgen)")
    print(f"\nDownload commands:")
    print(f"  scp fb******@login.hpc:{output_csv} .")
    print(f"  scp fb******@login.hpc:{output_pickle} .")
    print(f"{'_' * 90}")

if __name__ == '__main__':
    main()