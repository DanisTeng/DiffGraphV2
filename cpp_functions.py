from t1005_graph import *
from typing import List
from cpp_library import UserLibrary
from header import Header
import os


class CppFunction(FunctionBase):
    """
    A function that is assumed to be present inside the given user library.
    The python user need to provide a Header object to define a CppFunction.

    This class WON'T load c++ files to check the existence of the declared function,
    it ASSUMES that.
    TODO(huaiyuan): support more than one function in a library
    """
    def __init__(self,  header: Header,
                 user_library: UserLibrary,
                 namespace: str):
        assert is_valid_namespace(namespace)

        self.calling_prefix = namespace + "::"
        self.header = header

        super(CppFunction, self).__init__(self.header.input_spec.copy(),
                                          self.header.output_spec.copy(),
                                          {user_library, },
                                          self.header.supported_options.copy())

    def optional_header(self) -> "Header":
        return self.header

    def print_call(self, full_context: FullContext) -> CallResult:
        return self.header.print_call(full_context, prefix=self.calling_prefix)

