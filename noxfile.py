"""Nox sessions."""

from __future__ import annotations

import argparse
import os
import sys

import nox

nox.options.sessions = ["lint", "pylint", "tests"]

PYTHON_ALL_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12"]

if os.environ.get("CI", None):
    nox.options.error_on_missing_interpreters = True


@nox.session(reuse_venv=True)
def lint(session: nox.Session) -> None:
    """Lint the Python part of the codebase using pre-commit.

    Simply execute `nox -rs lint` to run all configured hooks.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session(reuse_venv=True)
def pylint(session: nox.Session) -> None:
    """Run PyLint.

    Simply execute `nox -rs pylint` to run PyLint.
    """
    session.install("scikit-build-core[pyproject]", "setuptools_scm", "pybind11")
    session.install("--no-build-isolation", "-ve.[dev]", "pylint")
    session.run("pylint", "mqt.qcec", *session.posargs)


@nox.session(reuse_venv=True, python=PYTHON_ALL_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run the test suite.

    Simply execute `nox -rs tests` to run all tests.
    """
    posargs = list(session.posargs)
    env = {"PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    install_arg = "-ve.[coverage]" if "--cov" in posargs else "-ve.[test]"

    # add -T ClangCl on Windows to avoid MSVC running out of heap space
    if sys.platform == "win32":
        env["CMAKE_ARGS"] = "-T ClangCl"

    if "--cov" in posargs:
        posargs.append("--cov-config=pyproject.toml")

    session.install("scikit-build-core[pyproject]", "setuptools_scm", "pybind11", env=env)
    session.install("--no-build-isolation", install_arg, env=env)
    session.run("pip", "show", "qiskit-terra")
    session.run("pytest", *posargs, env=env)


@nox.session(reuse_venv=True)
def min_qiskit_version(session: nox.Session) -> None:
    """Installs the minimum supported version of Qiskit, runs the test suite and collects the coverage."""
    session.install("qiskit-terra~=0.20.0")
    session.install("scikit-build-core[pyproject]", "setuptools_scm", "pybind11")
    session.install("--no-build-isolation", "-ve.[coverage]")
    session.run("pip", "show", "qiskit-terra")
    session.run("pytest", "--cov", *session.posargs)


@nox.session(reuse_venv=True)
def docs(session: nox.Session) -> None:
    """Build the docs. Pass "--serve" to serve. Pass "-b linkcheck" to check links."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="Serve after building")
    parser.add_argument("-b", dest="builder", default="html", help="Build target (default: html)")
    args, posargs = parser.parse_known_args(session.posargs)

    if args.builder != "html" and args.serve:
        session.error("Must not specify non-HTML builder with --serve")

    build_requirements = ["scikit-build-core[pyproject]", "setuptools_scm", "pybind11"]
    extra_installs = ["sphinx-autobuild"] if args.serve else []
    session.install(*build_requirements, *extra_installs)
    session.install("--no-build-isolation", "-ve.[docs]")
    session.chdir("docs")

    if args.builder == "linkcheck":
        session.run("sphinx-build", "-b", "linkcheck", "source", "_build/linkcheck", *posargs)
        return

    shared_args = (
        "-n",  # nitpicky mode
        "-T",  # full tracebacks
        f"-b={args.builder}",
        "source",
        f"_build/{args.builder}",
        *posargs,
    )

    if args.serve:
        session.run("sphinx-autobuild", *shared_args)
    else:
        session.run("sphinx-build", "--keep-going", *shared_args)
