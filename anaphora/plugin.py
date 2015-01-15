import coverage

class Plugin(coverage.CoveragePlugin):

	# def trace_judge(self, disposition):
	# 	print("TRACE_JUDGE %s" % disposition.origina)
	# 	disposition.trace = True

	def source_file_name(self, filename):
		print(filename)
		print("HAIL SATAN")
		return filename

	def code_unit_class(self, filename):
		print(filename)
		print("HAIL SANTANA")
		return coverage.codeunit.PythonCodeUnit
