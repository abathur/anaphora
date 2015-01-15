import coverage

import sys

from coverage.report import Reporter
from coverage.results import Numbers
from coverage.misc import NotPython

class Dict(Reporter):
    """A reporter for writing the summary report."""

    def __init__(self, coverage, config):
        super().__init__(coverage, config)
        self.branches = coverage.data.has_arcs()

    def statistics(self, morfs):
    	self.find_code_units(morfs)
    	#names = [cu.name for cu in self.code_units]
    	total = Numbers()
    	output = {}

    	#print(self.code_units)
    	for cu in self.code_units:
    		analysis = self.coverage._analyze(cu)
    		nums = analysis.numbers
    		output[cu.name] = {"statements": nums.n_statements, "missing": nums.n_missing, "branches": nums.n_branches, "missing_branches": nums.n_missing_branches, "coverage": nums.pc_covered, "miss": analysis.missing_formatted()}
    		total += nums
    	output["total"] = {"statements": total.n_statements, "missing": total.n_missing, "branches": total.n_branches, "missing_branches": total.n_missing_branches, "coverage": total.pc_covered}

    	return output

