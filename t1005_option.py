from typing import Dict,Any,Set
from common import *
import json


class Option:
    def __init__(self,
                 enable_1st_order_derivative: bool = False,
                 enable_2nd_order_derivative: bool = False):
        self.attr: Dict[str, Any] = {}

        self.attr["enable_1st_order_derivative"] = enable_1st_order_derivative
        self.attr["enable_2nd_order_derivative"] = enable_2nd_order_derivative

    def enable_1st_order_derivative(self):
        return self.attr["enable_1st_order_derivative"]

    def enable_2nd_order_derivative(self):
        return self.attr["enable_2nd_order_derivative"]

    def __eq__(self, other: "Option"):
        return self.attr == other.attr

    def __hash__(self):
        return hash(self.to_string())

    def to_string(self):
        return json.dumps(self.attr, indent=2)

    def from_string(self, string: str, ensure_having_same_fields=False):
        """
        Will update only those compatible fields.
        :param ensure_having_same_fields: Will check loaded string contains exactly what the class want.
        :param string:
        :return:
        """
        # reset everything to default
        self.__init__()

        loaded_dict = json.loads(string)

        if ensure_having_same_fields:
            assert loaded_dict.keys() == self.attr.keys(), \
                "Loaded option's key fields are not exactly the same as current classes'."

        for k, v in loaded_dict.items():
            assert type(k) is str

            if k in self.attr:
                self.attr[k] = v

    def decorate(self, function_name: str):
        assert is_valid_cpp_name(function_name)
        mask = [self.enable_1st_order_derivative(), self.enable_2nd_order_derivative()]
        titles = ['First', 'Second']

        result = function_name
        if any(mask):
            result += 'With'
            for i in range(len(mask)):
                if mask[i]:
                    result += titles[i]
            result += 'OrderDerivatives'

        return result

    def from_decorated(self, function_name: str, decorated_name: str):
        # So strong, that is parses option from decorated function name.
        # parse from decorated cpp.
        pass


class AllOptions:
    option_menu: Dict[str, Option] = {
        "d0": Option(False, False),
        "d1": Option(True, False),
        "d2": Option(True, True),
    }

    option_menu_inv: Dict[Option, str] = {}
    for k,v in option_menu.items():
        option_menu_inv[v] = k

    full_option_names = set(option_menu.keys())
    full_option_set = set(option_menu.values())

    # The one with the largest
    # number of output channels
    max_output_channel_option = Option(True, True)




    @classmethod
    def build_option_list_from_names(cls, names: List[str]) -> List[Option]:
        return [cls.option_menu[n] for n in names]

    @classmethod
    def build_names_from_options_list(cls, options: List[Option]) -> List[str]:
        return [cls.option_menu_inv[op] for op in options]
