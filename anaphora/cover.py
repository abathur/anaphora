"""Wrapper for interfacing with coverage.py."""

from coverage.report import Reporter
from coverage.results import Numbers

# LATERDO: figure out why I had this # from coverage.misc import NotPython


class Dict(Reporter):

    """A reporter for writing the summary report."""

    def __init__(self, cover_ob, config):
        super().__init__(cover_ob, config)
        self.branches = cover_ob.data.has_arcs()

    def statistics(self, morfs):
        """Return a dictionary of coverage statistics."""
        self.find_code_units(morfs)
        # names = [cu.name for cu in self.code_units]
        total = Numbers()
        output = {}

        # print(self.code_units)
        for code_unit in self.code_units:
            analysis = self.coverage._analyze(
                code_unit
            )  # pylint: disable=protected-access
            nums = analysis.numbers
            output[code_unit.name] = {
                "statements": nums.n_statements,
                "missing": nums.n_missing,
                "branches": nums.n_branches,
                "missing_branches": nums.n_missing_branches,
                "coverage": nums.pc_covered,
                "miss": analysis.missing_formatted(),
            }
            total += nums
        output["total"] = {
            "statements": total.n_statements,
            "missing": total.n_missing,
            "branches": total.n_branches,
            "missing_branches": total.n_missing_branches,
            "coverage": total.pc_covered,
        }

        return output
