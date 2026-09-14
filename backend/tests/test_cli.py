from __future__ import annotations

import unittest

from bioai_pipeline.cli import build_parser


class CliTest(unittest.TestCase):
    def test_process_command_owns_only_its_parameters(self) -> None:
        args = build_parser().parse_args(
            ["process-stories", "--max-papers", "10", "--max-sol-stories", "1"]
        )
        self.assertEqual(args.command, "process-stories")
        self.assertEqual(args.max_papers, 10)
        self.assertEqual(args.max_sol_stories, 1)
        self.assertFalse(hasattr(args, "lookback_hours"))


if __name__ == "__main__":
    unittest.main()
