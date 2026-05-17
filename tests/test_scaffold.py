from scope_modeler.cli import main
from scope_modeler.models.scope import ScaffoldModel


def test_cli_help_runs(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "Local-first renovation scope extraction scaffold" in capsys.readouterr().out


def test_pydantic_v2_model_wiring():
    model = ScaffoldModel(name="donizo")

    assert model.model_dump() == {"name": "donizo"}
