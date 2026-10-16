"""kredibel-synth (docs/18 §1).

kredibel-synth generate --scenario S2 --seed 1 --out out
kredibel-synth generate --all --seeds 1-5 --out out
kredibel-synth generate --scenario S1 --seed 1 --scan --out out
kredibel-synth fixtures --out out/fixtures
kredibel-synth demo --out out/demo
"""

import shutil
from pathlib import Path

import click

from .fixtures import build_fixtures
from .scenarios import SCENARIOS, Scenario, build
from .truth import dumps, readme, truth

P0_SCENARIOS = ["S1", "S2", "S3", "S4", "S5"]
DEMO_SCENARIOS = ["S1", "S2", "S3", "S4"]


def _seeds(text: str) -> list[int]:
    if "-" in text:
        lo, hi = text.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    return [int(part) for part in text.split(",")]


def scenario_dir(out: Path, sc: Scenario) -> Path:
    return out / sc.name / f"seed-{sc.seed}{'-scan' if sc.scanned else ''}"


def write_scenario(sc: Scenario, out: Path) -> Path:
    folder = scenario_dir(out, sc)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for name in sorted(sc.files):
        (folder / name).write_bytes(sc.files[name])
    (folder / "truth.json").write_bytes(dumps(truth(sc)))
    (folder / "upload-order.txt").write_text("\n".join(sc.upload_order) + "\n", encoding="utf-8")
    (folder / "README.md").write_bytes(readme(sc))
    return folder


@click.group()
def main() -> None:
    """Deterministic synthetic books for Kredibel (SYNTHETIC — FOR TESTING)."""


@main.command()
@click.option("--scenario", type=click.Choice(sorted(SCENARIOS)), help="One scenario.")
@click.option("--all", "all_", is_flag=True, help="Every P0 scenario (S1–S5).")
@click.option("--seed", type=int, help="One seed.")
@click.option("--seeds", help="A range (1-5) or a list (1,3).")
@click.option("--scan", is_flag=True, help="Image-only PDFs, 200 dpi, noise and skew.")
@click.option("--out", type=click.Path(path_type=Path), default=Path("out"), show_default=True)
def generate(
    scenario: str | None, all_: bool, seed: int | None, seeds: str | None, scan: bool, out: Path
) -> None:
    """Write scenarios to <out>/<scenario>/seed-<n>/."""
    names = P0_SCENARIOS if all_ else [scenario] if scenario else []
    numbers = _seeds(seeds) if seeds else [seed] if seed is not None else []
    if not names or not numbers:
        raise click.UsageError("Give --scenario or --all, and --seed or --seeds.")
    for name in names:
        for number in numbers:
            folder = write_scenario(build(name, number, scan=scan), out)
            click.echo(f"wrote {folder}")


@main.command()
@click.option(
    "--out", type=click.Path(path_type=Path), default=Path("out/fixtures"), show_default=True
)
@click.option("--seed", type=int, default=1, show_default=True)
def fixtures(out: Path, seed: int) -> None:
    """Write the fixtures of docs/18 §3.7, each with its own truth.json."""
    import json

    for fx in build_fixtures(seed):
        folder = out / fx.name
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        for name, data in sorted(fx.files.items()):
            (folder / name).write_bytes(data)
        (folder / "truth.json").write_text(
            json.dumps(fx.truth(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        click.echo(f"wrote {folder}")


@main.command()
@click.option("--out", type=click.Path(path_type=Path), default=Path("out/demo"), show_default=True)
@click.option(
    "--shift-months",
    type=int,
    default=0,
    show_default=True,
    help="Move every date by this many months (3: April to September 2026).",
)
@click.option(
    "--window",
    default=None,
    help="Keep only these months, after the shift: START:END as yyyy-mm (spec 024).",
)
@click.option("--pack", is_flag=True, help="Also merge the scenarios into one set in OUT/pack.")
def demo(out: Path, shift_months: int, window: str | None, pack: bool) -> None:
    """S1–S4, seed 1: the files of the demo workspace and the video (docs/18 §5)."""
    from .shift import set_shift
    from .window import keep_window

    set_shift(shift_months)
    for name in DEMO_SCENARIOS:
        folder = write_scenario(build(name, 1), out)
        if window:
            start, end = window.split(":")
            keep_window(folder, start, end)
        click.echo(f"wrote {folder}")
    if pack:
        from .pack import make_pack

        click.echo(f"wrote {make_pack(out, tuple(DEMO_SCENARIOS))}")


if __name__ == "__main__":
    main()
