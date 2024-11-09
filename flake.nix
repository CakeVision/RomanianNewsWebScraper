# flake.nix
{
  description = "Python development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        # Python packages to add to development environment
        pythonPackages = ps: with ps; [
          # Development tools
          ipython
          jupyter
          pytest
          black
          flake8
          mypy

          # Data Science core
          numpy
          scipy
          scikit-learn
          pandas
          matplotlib
          seaborn
          statsmodels
          #factor-analyzer
          
          # Additional data tools
          xlrd
          openpyxl

#FIXME: Check why these packages dont work
          #efficient-apriori
        # scikit-plot
         # linearmodels
          
          # Spatial analysis
          gdal # From conda-forge normally, but using nixpkgs version
          shapely
          pyproj
          geopandas
          fiona
          bokeh
          
          # Additional packages as needed...
        ];

        # Create a Python with our chosen packages
        python = pkgs.python311.withPackages pythonPackages;

      in {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python environment
            python
            
            # Development tools
            poetry
            pyright  # Python LSP
            ruff  # Fast Python linter
            

            #tooling for python libs
            gdal
            proj
            geos
            libxml2
            libxslt

            # Build tools
            gcc
            gnumake
            pkg-config
            
          ];

          shellHook = ''
            echo "Python Development Environment"
            echo "Python: $(python --version)"
            echo "Poetry: $(poetry --version)"
          #  
          #  poetry init 
          #  poetry add mca mpl_finance   
          #  poetry install
          #  poetry lock --no-update
            
            # Add any additional environment setup here
            export PYTHONPATH="$PWD:$PYTHONPATH"
          '';
        };

        # For building Python applications
        packages.default = pkgs.python3Packages.buildPythonApplication {
          pname = "my-python-app";  # Change this
          version = "0.1.0";
          format = "pyproject";  # or "setuptools" if using setup.py

          src = ./.;  # Source directory

          nativeBuildInputs = with pkgs.python3Packages; [
            poetry-core
          ];

          propagatedBuildInputs = pythonPackages pkgs.python3Packages;
        };
      });
}
