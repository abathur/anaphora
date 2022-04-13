{ pkgs ? import <nixpkgs> {} }:

pkgs.python3.pkgs.buildPythonPackage rec{
  version = "0.0.0";
  name = "anaphora-unreleased";
  src = fetchGit ./.;
  # src = fetchFromGitHub {
  #   owner = "abathur";
  #   repo = "anaphora";
  #   rev = "c0ef630a2b2bc283221b293ac057d57100182f02";
  #   sha256 = "0swn2p2fwifvvvi9b1xz2kjq5pwimxffwy9dsa99w1ks944gzs4n";
  # };
  buildInputs = [ ];
  propagatedBuildInputs = with pkgs.python3.pkgs; [
    colorama packaging coverage
  ];
  checkInputs = with pkgs.python3.pkgs; [
    flake8
    # pep257 # disable; not working in nix for some reason
  ];
  doCheck = true;
  installCheckPhase=''
    echo oooh nah nah
  '';

  checkPhase = ''
    type -p anaphora || true

    PYTHONPATH=$PWD:$PYTHONPATH $out/bin/anaphora tests.test -e ${version}
  '';
  meta = {
    homepage = "https://github.com/abathur/anaphora";
    license = pkgs.lib.licenses.mit;
    description = "A test thing.";
  };
}
