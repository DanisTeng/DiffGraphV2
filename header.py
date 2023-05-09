from t1005_graph import *
from cpp_library import UserLibrary, CppLibrary
import os


class Header:
    """
    An agent for function interface.
    Each function name of option is guaranteed to be option.decorate(function_name).

    What is a header?
    Contain full information for cpp function head generation.
    Always capable for compatibility check.
    An optioned header

    may not need to consider lib dependency.
    may not need to consider namespace.
    """

    _option_head = "// Option:"
    _constant_output_format = "%.6f"

    def __init__(self, function_name: str,
                 supported_options: List[Option],
                 input_spec: List[str],
                 output_spec: List[str],
                 input_names: List[str],
                 output_names: List[str],
                 constant_derivative_channels: Dict[Tuple, float],
                 safe_check=True):
        self.function_name = function_name
        self.supported_options = supported_options
        self.input_spec = input_spec
        self.output_spec = output_spec
        self.input_names = input_names
        self.output_names = output_names

        if safe_check:
            self.safe_check()

        # the shared dict for all derivative orders.
        self.constant_derivative_channels = constant_derivative_channels

    @staticmethod
    def parse_sorted_output_channel_from_name(input_names, output_names, name_string: str) -> Tuple:
        """
        :param input_names: name of input variables
        :param output_names: name of output variables
        :param name_string: There are 3 supported types:
        1,{output_name}
        2,D_{output_name}_D_{input_name}
        3,D2_{output_name}_D_{input_name_1}_D_{input_name_2}
        :return: parsed tuple of int
        if multiple input channel, they will be ordered such that their
        channel indices have increasing order in the return value.
        """
        name_string = remove_front_spaces(remove_end_spaces(name_string))
        items = split_skip_empty(name_string, "D")
        n = len(items)
        # 1 for 0 order, 4 for 1st order, 6 for 2nd order
        warning = "invalid field name:" + name_string
        assert n in {1, 2, 3}, warning

        def input_index_from_name(name: str):
            assert is_valid_lower_case_cpp_name(name), warning
            assert name in input_names, warning
            return input_names.index(name)

        def output_index_from_name(name: str):
            assert is_valid_lower_case_cpp_name(name), warning
            assert name in output_names, warning
            return output_names.index(name)

        if n == 1:
            # {output_name}
            output_name = items[0]
            return output_index_from_name(output_name),
        elif n == 2:
            # D_{output_name}_D_{input_name}
            output_name = items[0][1:-1]
            input_name = items[1][1:]
            return output_index_from_name(output_name), input_index_from_name(input_name)
        elif n == 3:
            # D2_{output_name}_D_{input_name_1}_D_{input_name_2}
            output_name = items[0][2:-1]
            input_name_1 = items[1][1:-1]
            input_name_2 = items[2][1:]
            i1 = input_index_from_name(input_name_1)
            i2 = input_index_from_name(input_name_2)
            if i1 > i2:
                i1, i2 = i2, i1
            return output_index_from_name(output_name), i1, i2

    @staticmethod
    def find_missing_derivative_channels(in_dim: int, out_dim: int, option: Option,
                                         existing_derivative_channels: Set[Tuple]):
        """
        a step to determine constant_derivative_channels.
        :param out_dim: num of outputs
        :param in_dim: num of inputs
        :param existing_derivative_channels:
        :param option:
        :return:
        """
        full_channels = full_output_channels_with_derivatives(in_dim, out_dim,
                                                              option.enable_1st_order_derivative(),
                                                              option.enable_2nd_order_derivative())
        missing_channels = []
        for channel in full_channels:
            if len(channel) > 1 and channel not in existing_derivative_channels:
                missing_channels.append(channel)

        return missing_channels

    # TODO(huaiyuan):
    # 1, Study and Mock core & from core, you write the following way of header creation. DONE
    # 2, In wrapped_function, the header will print_python_code_to_create_header. DONE
    # 3, Deprecate from_header_core globally, print header core don't need to be coupled with
    # anyone. DONE
    # 4, Refactor CppFunction: no actual c++ file dependency. Just add a namespace. DONE
    # 5, Added UT to show how to create bare .h file. mock wrapped_function. DONE
    # 6, Full UT for the usage: Add pure sympy generation, add simple combination with user cpp and
    # generated sympy files. DONE
    # 7, Auto diff UT

    # This is the python -> header interface
    @staticmethod
    def create_header(function_name: str,
                      inputs: str,
                      outputs: str,
                      derivatives: str,
                      supported_options: List[str]) -> "Header":
        """
        WARNING: This function couples with print_python_code_to_create_header.
        Need to change both for any update.
        :param function_name: example: Add
        :param inputs: example: x,y
        :param outputs: example: z
        :param derivatives: example: D_z_D_x, D2_z_D_x_D_x
        :param supported_options: example: ["d0","d1","d2"]
        :return:
        """
        inputs = purify(inputs)
        outputs = purify(outputs)
        derivatives = purify(derivatives)

        # inputs.
        input_items = split_skip_empty(inputs, ",")
        input_items = [remove_end_spaces(remove_front_spaces(item)) for item in input_items]
        input_names = []
        input_spec = []
        for item in input_items:
            type_and_name = item.split(" ")
            assert len(type_and_name) == 2, "create_header: Invalid inputs"
            input_spec.append(type_and_name[0])
            input_names.append(type_and_name[1])

        # outputs.
        output_items = split_skip_empty(outputs, ",")
        output_items = [remove_end_spaces(remove_front_spaces(item)) for item in output_items]
        output_names = []
        output_spec = []
        for item in output_items:
            type_and_name = item.split(" ")
            assert len(type_and_name) == 2, "create_header: Invalid outputs"
            output_spec.append(type_and_name[0])
            output_names.append(type_and_name[1])

        # Constant derivative channels
        # User declared: non-zero channels, otherwise taken as zero
        derivative_items = split_skip_empty(derivatives, ",")
        derivative_items = [remove_end_spaces(remove_front_spaces(item)) for item in derivative_items]

        constant_output_channels = {}
        existing_channels = set()
        for item in derivative_items:
            equator = item.find("=")
            if equator == -1:
                # Normal output
                channel = Header.parse_sorted_output_channel_from_name(input_names, output_names, item)
                existing_channels.add(channel)
            else:
                # Constant output
                type_name_and_value = item.split("=")
                assert len(type_name_and_value) == 2, "create_header: Invalid constant derivative"
                v = float(type_name_and_value[1])
                name = type_name_and_value[0]
                channel = Header.parse_sorted_output_channel_from_name(input_names, output_names, name)
                existing_channels.add(channel)
                constant_output_channels[channel] = v

        missing_derivatives = Header.find_missing_derivative_channels(in_dim=len(input_names),
                                                                      out_dim=len(output_names),
                                                                      option=AllOptions.max_output_channel_option,
                                                                      existing_derivative_channels=existing_channels)
        for ch in missing_derivatives:
            constant_output_channels[ch] = 0.0

        return Header(function_name=function_name,
                      supported_options=AllOptions.build_option_list_from_names(supported_options),
                      input_spec=input_spec,
                      output_spec=output_spec,
                      input_names=input_names,
                      output_names=output_names,
                      constant_derivative_channels=constant_output_channels)

    # This is the header -> python interface
    def print_python_code_to_create_header(self, left_value_name: str) -> List[str]:
        """
        WARNING: This function couples with create_header.
        Update both when making change.
        :param left_value_name:
        :return: example:
        {left_value_name} = \
            Header.create_header(function_name="Add",
                                 inputs="UserType c,"
                                        "double x,"
                                        "double y",
                                 outputs="double z",
                                 derivatives="D_z_D_x, D_z_D_y, D2_z_D_x_D_y = 0.0",
                                 supported_options=[])
        """
        lines = list()
        lines.append("%s = \\" % left_value_name)

        func_call_left = "Header.create_header("
        front_spaces = Const1005.indent + " " * len(func_call_left)

        is_first_front_part = True

        def get_front_part():
            nonlocal is_first_front_part
            if is_first_front_part:
                is_first_front_part = False
                return Const1005.indent + func_call_left
            else:
                return front_spaces

        def append_field_and_multi_line_values(field: str, values: List[str]):
            nonlocal lines
            n = len(values)
            assert n > 0
            if n == 1:
                # One line for the field
                lines.append(get_front_part() + "%s=%s," % (field, values[0]))
            else:
                # Multiple lines for the field
                lines.append(get_front_part() + "%s=%s" % (field, values[0]))
                extra_front = " " * (len(field) + 1)
                for j in range(1, n - 1):
                    lines.append(get_front_part() + extra_front + values[j])
                lines.append(get_front_part() + extra_front + values[n - 1] + ",")

        append_field_and_multi_line_values("function_name", ["\"" + self.function_name + "\""])

        # inputs
        inputs_value = []
        for i in range(len(self.input_names)):
            inputs_value.append("\"%s %s,\"" % (self.input_spec[i], self.input_names[i]))
        if inputs_value:
            inputs_value[-1] = remove_end_comma_in_quotation(inputs_value[-1])
        else:
            inputs_value = ["\"\""]
        append_field_and_multi_line_values("inputs", inputs_value)

        # outputs
        outputs_value = []
        for i in range(len(self.output_names)):
            outputs_value.append("\"%s %s,\"" % (self.output_spec[i], self.output_names[i]))
        if outputs_value:
            outputs_value[-1] = remove_end_comma_in_quotation(outputs_value[-1])
        else:
            outputs_value = ["\"\""]
        append_field_and_multi_line_values("outputs", outputs_value)

        # derivatives
        derivatives_value = []
        for channel in self.output_channels(AllOptions.max_output_channel_option):
            if len(channel) == 1:
                # not derivative
                continue
            field_name = self.output_channel_name(channel)
            derivatives_value.append("\"%s,\"" % field_name)
        for channel, value in self.constant_derivative_channels.items():
            if value == 0:
                continue
            field_name = self.output_channel_name(channel)
            field_value = self._constant_output_format % value
            derivatives_value.append("\"%s = %s,\"" % (field_name, field_value))

        if derivatives_value:
            derivatives_value[-1] = remove_end_comma_in_quotation(derivatives_value[-1])
        else:
            derivatives_value = ["\"\""]
        append_field_and_multi_line_values("derivatives", derivatives_value)

        # supported options
        option_names = AllOptions.build_names_from_options_list(self.supported_options)
        append_field_and_multi_line_values("supported_options", [str(option_names)])

        # final ket.
        lines[-1] = lines[-1][:-1] + ")"

        return lines

    # This is the header -> .h file interface
    def dump_to_h_file(self, user_library: UserLibrary,
                       force_update=True,
                       namespace: List[str] = None,
                       dependencies: Set[CppLibrary] = None,
                       author_script: str = "None"):
        """
        :param user_library: cpp header file destination
        :param force_update:  Will override existing file if true
        :param namespace: ["math","util"] -> math::util
        :param dependencies: other library objects
        :param author_script: /my/folder/some_script.py
        :return:
        """
        path = user_library.lib_abs_path()
        name = user_library.lib_name()
        header_file = os.path.join(path, name + Const1005.cpp_header_file_extension)

        if not os.path.exists(path) and force_update:
            os.makedirs(path)
        if os.path.exists(header_file) and force_update:
            os.remove(header_file)

        assert os.path.exists(path), "<%s> not exist." % path
        assert not os.path.exists(header_file), "<%s> already exist." % header_file

        if namespace is None:
            namespace = []

        def write_lines(lines: List[str], indent=0):
            for l in lines:
                fp.write(str(Const1005.indent * indent) + l + "\n")

        def empty_line():
            fp.write("\n")

        namespace_string = "::".join(namespace)

        # Write to .h file.
        with open(header_file, "w") as fp:
            write_lines(user_library.head_comments_h(author_script))
            write_lines(["#pragma once"])
            empty_line()

            # includes
            builtin_includes = []
            includes = []
            for dep in dependencies:
                include_name = dep.include_name()
                if include_name[0] == "<":
                    builtin_includes.append("#include " + include_name)
                else:
                    includes.append("#include " + include_name)
            builtin_includes.sort()
            includes.sort()

            if builtin_includes:
                write_lines(builtin_includes)
                empty_line()
            write_lines(includes)
            empty_line()

            # namespace
            if namespace_string != "":
                write_lines(["namespace %s {" % namespace_string])

            # Tell user how to create this header using python
            python_comment = ["/*", "Python to create this header:"]
            python_comment += self.print_python_code_to_create_header(left_value_name="python_object")
            python_comment.append("*/")
            write_lines(python_comment, indent=1 if namespace_string != "" else 0)

            empty_line()

            # header core part
            write_lines(self.print_header_core(), indent=1 if namespace_string != "" else 0)

            # namespace
            if namespace_string != "":
                write_lines(["}  // namespace %s" % namespace_string])

            write_lines(user_library.tail_comments_h())
            empty_line()

    # The .h -> python interface is achieved by
    # printing the python code as comment in .h file

    def safe_check(self):
        """
        Check the validity of
        self.function_name
        self.input_spec
        self.output_spec
        self.input_names
        self.output_names
        :return:
        """
        assert is_valid_cpp_name(self.function_name), "Need valid function name."
        assert all([is_valid_cpp_name(item) for item in self.input_spec]), "Need valid input type."
        assert all([is_valid_lower_case_cpp_name(item) for item in self.input_names]), "Need valid input name."
        assert all([is_valid_cpp_name(item) for item in self.output_spec]), "Need valid output type."
        assert all([is_valid_lower_case_cpp_name(item) for item in self.output_names]), "Need valid output name."
        assert len(self.input_spec) == len(self.input_names)
        assert len(self.output_spec) == len(self.output_names)
        all_name_set = set(self.input_names)
        all_name_set.update(set(self.output_names))
        assert len(all_name_set) == len(self.input_names) + len(self.output_names), "Need no repeated names."

    def output_channels(self, option):
        """
        constant_derivative_channels must be valid
        list all output channels including zero order, skipping constant derivative ones.
        :param option:
        :return:
        """
        in_dim = len(self.input_spec)
        out_dim = len(self.output_spec)
        full_channels = full_output_channels_with_derivatives(in_dim, out_dim,
                                                              option.enable_1st_order_derivative(),
                                                              option.enable_2nd_order_derivative())
        channels = []
        for channel in full_channels:
            if channel not in self.constant_derivative_channels:
                channels.append(channel)

        return channels

    def find_missing_output_channels(self, option: Option, given_channels: Set[Tuple]):
        """
        a step to determine constant_derivative_channels.
        :param option:
        :param given_channels:
        :return:
        """
        in_dim = len(self.input_spec)
        out_dim = len(self.output_spec)
        full_channels = full_output_channels_with_derivatives(in_dim, out_dim,
                                                              option.enable_1st_order_derivative(),
                                                              option.enable_2nd_order_derivative())
        missing_channels = []
        for channel in full_channels:
            if channel not in given_channels:
                missing_channels.append(channel)

        return missing_channels

    def output_channel_name(self, channel: Tuple):
        assert len(channel) in {1, 2, 3}
        if len(channel) > 1:
            ch_names = [self.output_names[channel[0]]] + \
                       [self.input_names[i] for i in channel[1:]]
            return get_channel_name(tuple(ch_names))
        else:
            return self.output_names[channel[0]]

    def output_channel_type(self, channel: Tuple):
        assert len(channel) > 0
        return self.output_spec[channel[0]]

    def sorted_output_channel_from_name(self, name_string: str) -> Tuple:
        """
        Pre-condition:
        self.input_names, self.output_names are ready
        :param name_string: There are 3 supported types:
        1,{output_name}
        2,D_{output_name}_D_{input_name}
        3,D2_{output_name}_D_{input_name_1}_D_{input_name_2}
        :return: parsed tuple of int
        if multiple input channel, they will be ordered such that their
        channel indices have increasing order in the return value.
        """
        items = name_string.split("D")
        n = len(items)
        # 1 for 0 order, 4 for 1st order, 6 for 2nd order
        warning = "invalid field name:" + name_string
        assert n in {1, 4, 6}, warning

        def input_index_from_name(name: str):
            assert is_valid_lower_case_cpp_name(name), warning
            assert name in self.input_names, warning
            return self.input_names.index(name)

        def output_index_from_name(name: str):
            assert is_valid_lower_case_cpp_name(name), warning
            assert name in self.output_names, warning
            return self.output_names.index(name)

        if n == 1:
            # {output_name}
            output_name = items[0]
            return output_index_from_name(output_name),
        elif n == 4:
            # D_{output_name}_D_{input_name}
            output_name = items[0][1:-1]
            input_name = items[1][1:]
            return output_index_from_name(output_name), input_index_from_name(input_name)
        elif n == 6:
            # D2_{output_name}_D_{input_name_1}_D_{input_name_2}
            output_name = items[0][2:-1]
            input_name_1 = items[1][1:-1]
            input_name_2 = items[2][1:]
            i1 = input_index_from_name(input_name_1)
            i2 = input_index_from_name(input_name_2)
            if i1 > i2:
                i1, i2 = i2, i1
            return output_index_from_name(output_name), i1, i2

    def print_header_core(self):
        """
        to .h
        one line, one input/output
        /* xxx_name = 4.5*/ like this for constant derivative outputs
        you parse the xxx_name

        option must be headed.
        use raw option to fetch input spec. output specs.
        for constant derivative io, I bet you can make them inline in header.
        :return:
        """
        result = []

        for option in self.supported_options:
            # Print option lines
            option_lines = option.to_string().split('\n')
            result.append(self._option_head)
            for line in option_lines:
                result.append("//" + line)

            # Print function declaration
            final_function_name = option.decorate(self.function_name)
            fields = []
            # inputs
            in_dim = len(self.input_spec)
            for i in range(in_dim):
                fields.append(VarType1005.const_reference(self.input_spec[i]) + ' ' + self.input_names[i])
            # outputs
            for channel in self.output_channels(option):
                field_type = self.output_channel_type(channel)
                field_name = self.output_channel_name(channel)
                fields.append(field_type + "* " + field_name)
            # constant outputs
            for channel, value in self.constant_derivative_channels.items():
                if value == 0:
                    continue
                field_name = self.output_channel_name(channel)
                field_value = self._constant_output_format % value
                fields.append("/*%s = %s*/" % (field_name, field_value))
            result += self._function_with_fields_to_lines(final_function_name, fields)

            # Empty line
            result.append("")

        return result

    def print_implementation_head(self, option: Option):
        final_function_name = option.decorate(self.function_name)
        fields = []
        # inputs
        in_dim = len(self.input_spec)
        for i in range(in_dim):
            fields.append(VarType1005.const_reference(self.input_spec[i]) + ' ' + self.input_names[i])
        # outputs
        for channel in self.output_channels(option):
            field_type = self.output_channel_type(channel)
            field_name = self.output_channel_name(channel)
            fields.append(field_type + "* " + field_name)
        result = self._function_with_fields_to_lines(final_function_name, fields)

        if result[-1][-1] == ";":
            result[-1] = result[-1][:-1] + " {"
        return result

    @staticmethod
    def _function_with_fields_to_lines(function_final_name: str, fields: List[str]):
        """
        :param function_final_name: The final name of the function
        :param fields: each element shown in separate line, comma free, can be /*???*/.
        each field MUST avoid extra space in the front.
        :return:
        """
        result = []

        if not fields:
            return ['void ' + function_final_name + "();"]
        elif len(fields) == 1:
            return ['void %s(%s);' % (function_final_name, fields[0])]

        def is_comment_field(field: str):
            return field[:2] == "/*"

        last_non_comment_field = -1
        for i in range(len(fields)):
            if not is_comment_field(fields[i]):
                last_non_comment_field = i

        def may_add_comma(field_id: int):
            field = fields[field_id]
            if is_comment_field(field):
                # no comma for comment field
                return field
            elif field_id == last_non_comment_field:
                return field
            else:
                return field + ","

        # at least two fields
        head = 'void ' + function_final_name + "("
        result.append(head + may_add_comma(0))
        var_spaces = " " * len(head)

        for i in range(1, len(fields) - 1):
            result.append(var_spaces + may_add_comma(i))

        result.append(var_spaces + fields[-1] + ");")

        return result

    def print_call(self, full_context: FullContext, prefix="") -> CallResult:
        """
        GongJuRen
        :param prefix: The calling prefix, for e.g.
        SomeNameSpace::Foo(...)
        :param full_context:
        :return:
        """
        result = CallResult()

        # determine the interface
        interface_output_channels = self.output_channels(full_context.option)
        output_channels_required_by_graph = set(full_context.required_output_channels())
        output_field_names = []
        # type to name
        unused_variables: Dict[str, str] = {}
        for channel in interface_output_channels:
            if channel in output_channels_required_by_graph:
                output_field_names.append(full_context.output_channel_name(channel))
            else:
                var_type = self.output_channel_type(channel)
                if var_type not in unused_variables:
                    unused_variables[var_type] = Const1005.graph_unused_prefix + var_type
                output_field_names.append(unused_variables[var_type])

        result.lines = []
        result.lines.append("{")
        for var_type, var_name in unused_variables.items():
            result.lines.append(Const1005.indent + var_type + " " + var_name + ";")

        calling = Const1005.indent + prefix + full_context.option.decorate(self.function_name)

        calling += "("

        # TODO(huaiyuan):split into multiple lines if possible
        # fill input graph vars.
        for i in range(len(full_context.context.input_variables)):
            calling += full_context.context.input_variables[i].nick_name + ","

        for out_name in output_field_names:
            calling += "&" + out_name + ","

        if calling[-1] == ",":
            calling = calling[:-1]
        calling += ");"

        result.lines.append(calling)

        result.lines.append("}")

        # constant_derivative_outputs.
        result.constant_output_channels = {}
        for channel, value in self.constant_derivative_channels.items():
            # here, I guess it is correct
            if channel in output_channels_required_by_graph:
                result.constant_output_channels[channel] = value

        return result
