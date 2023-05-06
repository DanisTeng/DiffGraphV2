from wrapped_function import *
from t1005_graph import *
from cpp_functions import CppFunction

from wrapped_function import *
import sympy_function

_my_visual_studio_project_root = ""
UserLibrary.set_global_project_root(_my_visual_studio_project_root)

def test_case_1():
    g = Graph()
    x, y = g.state_inputs(['x', 'y'], 'double')
    c = g.config_inputs(['c'], 'UserType')
    radius = x ** 2 + y ** 3

    radius.set_name('r')

    create_rad = wrap_graph(g, [c, x, y], [radius], "Radius")

    create_rad.dump_to_lib(UserLibrary("generated", "radius"))




def test_case_2():
    g = Graph()
    x, y = g.state_inputs(['x', 'y'], 'double')
    c = g.config_inputs(['c'], 'UserType')

    radius_func = CppFunction(UserLibrary("generated", "radius"))

    radius = radius_func(c, x, y)

    radius.set_name('r')
    radius_inv = 1.0/radius
    create_rad = wrap_graph(g, [c, x, y], [radius_inv], "RadiusInv")

    create_rad.dump_to_lib(UserLibrary("generated", "radius_inv"))



test_case_1()
    # TODO(): test validity in C++ project. operators. Bp process for gradients. (single output)

