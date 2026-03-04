### vasp-extract

Extracts energy and structure information from VASP relaxation/static calculations.

### Usage

    python vasp-extract.py <base_path>

- <base_path>: Path to the folder containing structure subfolders (with static/ or relaxation/ calculations).

### How it works

- The script looks for subfolders named static/ or relaxation/ inside <base_path>.
- Energy is extracted from the OUTCAR file in these folders.
- Structure information is extracted from the CONTCAR file (if present), otherwise POSCAR is used.

### Output

- CSV file with energy, composition, lattice parameters, ...
- Pickle file with structure objects (pymatgen).

#### Requirements

- Python 3
- pymatgen
