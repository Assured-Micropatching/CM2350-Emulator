# Prerequesuites
1. Python3
2. [virtualenv](https://pypi.org/project/virtualenv/) is installed

# Using the Emulator
To use the emulator you can install with the `virtualenv` makefile target
```
make virtualenv
```

Or by manually creating a virtualenv and installing the python dependencies:
```
git clone https://github.com/Assured-Micropatching/CM2350-Emulator.git emulator
cd emulator
virtualenv --python=python3 ENV
. ENV/bin/activate
pip install -r requirements.txt
```

# Setting up your environment for emulator development
## With virtual environments
Assuming you want to use installed packages in the python-recommended way, you
will be using virtualenvs.

1. Clone the vivisect and cm2350 emulator git repos:
```
git clone https://github.com/atlas0fd00m/vivisect.git -b envi_ppc vivisect
git clone https://github.com/Assured-Micropatching/CM2350-Emulator.git emulator
```

2. Create a virtual environment and install the vivisect package and emulator
   dependencies in developer mode.  This will help ensure that changes made in
   to the emulator in the `vivisect/` directory are used immediately by other
   packages that import the `vivisect` python module.
```
virtualenv --python=python3 ENV
. ENV/bin/activate
cd vivisect
python setup.py develop
cd ../emulator
pip install ipython
```

3. After the vivisect package and emulator prerequisites have been installed,
   and you have activated the virtual environment you can start the emulator
   with the `EMU_ecu.py` script:
```
. ENV/bin/activate
emulator/ECU_emu.py
```

4. The virtualenv can be deactivated with the `deactivate` shell command that is
   defined when the virtualenv is activated:
```
deactivate
```

If you prefer to not have to activate and deactivate the virtualenv all the time
you can create an alias:
```
alias ampemu="bash -c 'source path/to/ENV/bin/activate && python path/to/emulator/ECU_emu.py'"
```
Or you can use an alternate python virtual environment management tool such as
[pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) for use with
[pyenv](https://github.com/pyenv/pyenv) which allows you to define a specific
python version or python virtualenv install to use for specific directories.

## Without virtual environments
You like to live dangerously, or can't be bothered (trust me I understand).

1. Clone the vivisect and cm2350 emulator git repos:
```
git clone https://github.com/atlas0fd00m/vivisect.git -b envi_ppc vivisect
git clone https://github.com/Assured-Micropatching/CM2350-Emulator.git emulator
```

2. Install the vivisect package and emulator dependencies in developer mode.
   This will help ensure that changes made in to the emulator in the `vivisect/`
   directory are used immediately by other packages that import the `vivisect`
   python module.
```
cd vivisect
python3 setup.py develop --user
cd ../emulator
pip install ipython
```

When installing python packages with `python3 setup.py develop --user` a
`$HOME/.local/lib/python3.9/site-packages/vivisect.egg-link` file is created with
path to directories that contain python packages that should be in the
`PYTHON_PATH`:
```
$ cat ~/.local/lib/python3.9/site-packages/vivisect.egg-link
/home/user/path/to/vivisect
```

You can remove the link to the "installed" emulator-specific vivisect directory
by editing that file to removing `/home/user/path/to/vivisect`.

## Using virtualenvs with pyenv
Install [pyenv](https://github.com/pyenv/pyenv) and
[pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv).  Those github
pages have the install instructions, but the generic "clone through git"
instructions are described here for Ubuntu:
1. Install the [pyenv dependencies](https://github.com/pyenv/pyenv/wiki#suggested-build-environment)
```
sudo apt-get update
sudo apt-get install git make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```
2. Install [pyenv](https://github.com/pyenv/pyenv):
```
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
cat <<'EOF' >> ~/.bashrc
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
EOF
```
3. Open a new shell and install [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv):
```
git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
```
4. Set your default python version.  On Linux it's usually fine to just use the
   system default:
```
pyenv global system
```
5. If you need a specific python version you can install it with pyenv.  In this
   step python version 3.9.10 is being installed, this isn't necessary it's
   just the version being used in this example.
```
pyenv install 3.9.10
pyenv global 3.9.10
```
6. On Linux there is a bug in the latest version of `setuptools` that results in
   a [python-build error](https://github.com/pyenv/pyenv/issues/2202).  If
   `pyenv install` fails you may need to explicitly install the latest
   `setuptools` from git until the version on pypi.org is fixed:
```
pip install --user git+https://github.com/pypa/setuptools@v60.5.4#egg=setuptools
```
7. Create a new virtualenv specific for CM2350 emulator and vivisect, and make
   it the default version to use for the TA3 emulator working directory:
```
pyenv virtualenv 3.9.10 amp_ta3_emulator
cd path/to
pyenv local amp_ta3_emulator
```
8. Clone the emulator and vivisect repos and install the required packages:
```
git clone https://github.com/atlas0fd00m/vivisect.git -b envi_ppc
path/to/vivisect
git clone https://github.com/Assured-Micropatching/CM2350-Emulator.git path/to/emulator
cd path/to/vivisect
python3 setup.py develop
pip install ipython
```
Now the `amp_ta3_emulator` virtualenv will be automatically activated whenever you are in the `path/to` directory or a subdirectory.
