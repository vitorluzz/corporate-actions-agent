"""Command-line entrypoint: run the batch and write deliverables.

Examples:
    asset-agent run                  # offline stub if no GOOGLE_API_KEY, else Gemini
    asset-agent run --provider gemini
    asset-agent run --replay         # reproduce from the response cache (no LLM calls)
"""

from __future__ import annotations

import argparse
import sys

from app.agent.runner import run_batch
from app.config import get_settings
from app.output import write_outputs


def _cmd_run(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.provider:
        settings.llm_provider = args.provider
    if args.replay:
        settings.replay_only = True
    if args.out:
        settings.outputs_dir = args.out
    if args.n:
        settings.self_consistency_n = args.n

    print(
        f"provider={settings.effective_provider} model? "
        f"N={settings.self_consistency_n} replay={settings.replay_only}",
        file=sys.stderr,
    )
    results, summary = run_batch(settings)
    out = write_outputs(results, summary, settings.outputs_dir)

    print(
        f"\nProcessados {summary.total} documentos → {out}\n"
        f"  auto-aprovados: {summary.auto_approved} ({summary.auto_rate:.0%})\n"
        f"  revisão humana: {summary.review}\n"
        f"  rejeitados:     {summary.rejected}\n"
        f"  confiança média: {summary.avg_confidence:.0%}"
    )
    for r in results:
        print(f"  - {r.document.source_file:42} {r.routing.decision.value:13} {r.event_type.argmax.value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="asset-agent", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the batch over documents/ and write outputs/")
    run.add_argument("--provider", choices=["auto", "gemini", "stub"], default=None)
    run.add_argument("--replay", action="store_true", help="reproduce from cache (no LLM calls)")
    run.add_argument("--n", type=int, default=None, help="self-consistency samples per document")
    run.add_argument("--out", type=str, default=None, help="outputs directory")
    run.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
