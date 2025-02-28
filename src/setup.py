from setuptools import find_packages, setup


setup(
    name="kedro_graphql",
    packages=find_packages(exclude=["tests"]),
    extras_require={
        "docs": [
            "docutils<0.18.0",
            "sphinx~=3.4.3",
            "sphinx_rtd_theme==0.5.1",
            "nbsphinx==0.8.1",
            "nbstripout~=0.4",
            "sphinx-autodoc-typehints==1.11.1",
            "sphinx_copybutton==0.3.1",
            "ipykernel>=5.3, <7.0",
            "Jinja2<3.1.0",
            "myst-parser~=0.17.2",
        ]
    },
)
